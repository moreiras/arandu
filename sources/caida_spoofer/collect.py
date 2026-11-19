# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""CAIDA Spoofer: sessões de teste de validação de endereço de origem do Brasil, agregadas por ASN.

Fonte:       https://api.spoofer.caida.org/sessions?country=bra&timestamp[after]=AAAA-MM-DDTHH:MM:SS&itemsPerPage=500 (Hydra/JSON aberto, sem chave)
Estado:      data/spoofer/sessoes.json.gz   {ate, sessoes: [...]}   sessões já **sem o endereço do cliente** (`core.spoofer.sanear`); incremental, guarda ~400 dias
Normalizado: data/normalized/{date}/summary/caida_spoofer.json.gz   agregados por ASN na janela de 12 meses (core/spoofer.py)
Bruto:       nenhum: a resposta da API traz o /24 do cliente, que não pode ser gravado (nem no bruto).
Licença:     Public AUA do CAIDA: citar "The CAIDA UCSD Spoofer ..." e comunicar a publicação ao CAIDA (data-info@caida.org). O projeto está sem financiamento (página do projeto, 2026-11-02).

A primeira execução baixa os 12 meses (~66 páginas de 500, ~40 min); as seguintes só o que veio depois da última sessão guardada.

Uso:
    python -m sources.caida_spoofer.collect --date 2026-11-02
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import httpx

from core import spoofer
from core.common import configure_logging, data_dir, normalized_path, now_iso, today_str
from core.jsonio import carregar_json_gz, gravar_json_gz
from core.site import USER_AGENT

BASE_URL = "https://api.spoofer.caida.org"
HEADERS = {"User-Agent": USER_AGENT}
POR_PAGINA = 500
ESPERA_S = 1.0
RETENCAO_DIAS = 400
MINIMO_SESSOES = 5000                                   # 12 meses do Brasil: hoje ~32 mil; bem menos que isso é coleta truncada
CITACAO = "The CAIDA UCSD Spoofer Project, https://www.caida.org/projects/spoofer/ (testes de validação de endereço de origem enviados por voluntários)"


def estado_path(base: Path) -> Path:
    return base / "spoofer" / "sessoes.json.gz"


def baixar(client: httpx.Client, depois_de: str, espera: float = ESPERA_S, tentativas: int = 3) -> list[dict]:
    """Todas as sessões do Brasil depois de `depois_de` (ISO), já sem o endereço do cliente. A API devolve em ordem crescente de tempo."""
    url: Optional[str] = f"/sessions?country=bra&timestamp%5Bafter%5D={quote(depois_de)}&itemsPerPage={POR_PAGINA}&page=1"
    out: list[dict] = []
    while url:
        for t in range(1, tentativas + 1):
            try:
                r = client.get(url)
                r.raise_for_status()
                d = r.json()
                break
            except (httpx.HTTPError, ValueError):
                if t == tentativas:
                    raise
                time.sleep(5 * t)
        out += [spoofer.sanear(x) for x in d["hydra:member"]]
        url = (d.get("hydra:view") or {}).get("hydra:next")
        if url:
            time.sleep(espera)
    return out


def run(date_str: str, base: Path, log, client: Optional[httpx.Client] = None, espera: float = ESPERA_S) -> dict:
    fim = dt.date.fromisoformat(date_str)
    proprio = client is None
    client = client or httpx.Client(base_url=BASE_URL, timeout=httpx.Timeout(60, read=240), follow_redirects=True, headers=HEADERS)
    try:
        estado = carregar_json_gz(estado_path(base)) or {"ate": None, "sessoes": []}
        desde = estado["ate"] or (dt.datetime.combine(fim, dt.time.min) - dt.timedelta(days=spoofer.JANELA_DIAS + 1)).isoformat()
        novas = baixar(client, desde, espera)
    finally:
        if proprio:
            client.close()
    por_id = {s["session"]: s for s in estado["sessoes"]}
    por_id.update({s["session"]: s for s in novas})
    corte = (dt.datetime.combine(fim, dt.time.min, tzinfo=dt.timezone.utc) - dt.timedelta(days=RETENCAO_DIAS)).isoformat()
    sessoes = sorted((s for s in por_id.values() if s["timestamp"] >= corte), key=lambda s: s["timestamp"])
    if len(sessoes) < MINIMO_SESSOES:
        raise RuntimeError(f"caida_spoofer: só {len(sessoes)} sessões guardadas (esperado ≥ {MINIMO_SESSOES}); coleta truncada?")
    destino_estado = estado_path(base)
    destino_estado.parent.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino_estado, {"ate": sessoes[-1]["timestamp"], "atualizado_em": now_iso(), "sessoes": sessoes})
    asns, resumo = spoofer.agregar(sessoes, fim)
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino / "caida_spoofer.json.gz", {
        "snapshot_date": date_str, "fetched_at": now_iso(), "fonte": "CAIDA Spoofer (api.spoofer.caida.org)", "citacao": CITACAO, "novas_sessoes": len(novas),
        "resumo": resumo, "asns": asns})
    log.info("caida_spoofer written", novas=len(novas), **{k: v for k, v in resumo.items() if k != "janela"})
    return {"novas_sessoes": len(novas), **{k: v for k, v in resumo.items() if k != "janela"}}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="CAIDA Spoofer: agregados por ASN (sem endereço do cliente)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre incremental")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        print(run(a.date, data_dir(), log))
    except Exception:
        log.exception("falha na coleta de caida_spoofer")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
