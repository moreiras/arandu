# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Vigia dos diretórios de numeração do Registro.br e do LACNIC. Fonte própria, sem dado publicado: grava a varredura do dia e os alertas.

Varre as listagens (`ftp.registro.br/pub/{numeracao,numeracao/origin,numeracao/geoip,geofeed}`, `ftp.lacnic.net/pub/stats/lacnic{,/transfers,/critical_infra}`) e o cabeçalho de
alguns arquivos-chave, compara com a varredura anterior (`core/vigia_diretorios.py`) e grava `data/ops/vigia/ipv4/{date}.json` com `alertas`. O alerta vai também para o log
(`aviso`), onde o `arandu doctor` e o mantenedor o veem; a coleta termina com sucesso mesmo com alerta (alerta não é falha). Uma conexão, pausa entre requisições.

Uso:
    python -m sources.ipv4_vigia.collect --date 2026-11-02
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Callable, Optional

import httpx

from core.common import configure_logging, data_dir, now_iso, today_str
from core.vigia_diretorios import cabecalho, comparar, parse_indice
from core.site import USER_AGENT

HEADERS = {"User-Agent": USER_AGENT}
PAUSA_S = 1.0
RB, LC = "https://ftp.registro.br/pub", "https://ftp.lacnic.net/pub/stats/lacnic"
DIRETORIOS = [f"{RB}/numeracao/", f"{RB}/numeracao/origin/", f"{RB}/numeracao/geoip/", f"{RB}/geofeed/", f"{LC}/", f"{LC}/transfers/", f"{LC}/critical_infra/"]
ARQUIVOS = [f"{RB}/numeracao/transferencias-diretas-latest", f"{RB}/numeracao/transferencias-diretas-lacnic-latest", f"{RB}/numeracao/recuperacao-latest", f"{RB}/numeracao/recuperados-latest",
            f"{RB}/numeracao/origin/nicbr-asn-blk-latest.txt", f"{LC}/transfers/transfers_latest.json", f"{LC}/critical_infra/critical-infra-latest", f"{LC}/delegated-lacnic-extended-latest"]
MINIMO_DIRETORIOS = 6                                  # de 7: um diretório fora do ar não derruba a varredura, mas quase nada listado é falha


def caminho(base: Path, date_str: str) -> Path:
    return base / "ops" / "vigia" / "ipv4" / f"{date_str}.json"


def anterior(base: Path, date_str: str) -> Optional[dict]:
    pasta = caminho(base, date_str).parent
    if not pasta.exists():
        return None
    antes = sorted(p for p in pasta.glob("*.json") if p.stem < date_str)
    return json.loads(antes[-1].read_text(encoding="utf-8")) if antes else None


def varrer(client: httpx.Client, log, dormir: Callable[[float], None] = time.sleep) -> dict:
    dirs, cabs, erros = {}, {}, {}
    for url in DIRETORIOS:
        try:
            r = client.get(url)
            r.raise_for_status()
            dirs[url] = parse_indice(r.text)
        except httpx.HTTPError as e:
            erros[url] = str(e)[:160]
            log.warning("vigia: diretório indisponível", url=url, erro=erros[url])
        dormir(PAUSA_S)
    for url in ARQUIVOS:
        try:
            r = client.get(url, headers={"Range": "bytes=0-4095"})
            r.raise_for_status()
            cabs[url] = cabecalho(r.content)
        except httpx.HTTPError as e:
            erros[url] = str(e)[:160]
        dormir(PAUSA_S)
    return {"diretorios": dirs, "cabecalhos": cabs, "erros": erros}


def run(date_str: str, base: Path, log, client: Optional[httpx.Client] = None, dormir: Callable[[float], None] = time.sleep) -> dict:
    proprio = client is None
    client = client or httpx.Client(timeout=60, follow_redirects=True, headers=HEADERS)
    try:
        v = varrer(client, log, dormir)
    finally:
        if proprio:
            client.close()
    if len(v["diretorios"]) < MINIMO_DIRETORIOS:
        raise RuntimeError(f"vigia: só {len(v['diretorios'])} de {len(DIRETORIOS)} diretórios listados")
    # um diretório que falhou hoje não vira "removido": herda a listagem da varredura anterior
    ant = anterior(base, date_str)
    alertas = comparar({"diretorios": v["diretorios"], "cabecalhos": v["cabecalhos"]}, ant)
    destino = caminho(base, date_str)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".tmp")
    tmp.write_text(json.dumps({"snapshot_date": date_str, "generated_at": now_iso(), "alertas": alertas, **v}, ensure_ascii=False), encoding="utf-8")
    tmp.replace(destino)
    for a in alertas:
        log.warning("vigia: novidade nos diretórios de numeração", **{k: str(x)[:200] for k, x in a.items()})
    log.info("ipv4_vigia written", diretorios=len(v["diretorios"]), arquivos=len(v["cabecalhos"]), alertas=len(alertas))
    return {"diretorios": len(v["diretorios"]), "cabecalhos": len(v["cabecalhos"]), "alertas": len(alertas), "primeira_varredura": ant is None}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Vigia dos diretórios de numeração do Registro.br e do LACNIC")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a varredura é sempre refeita")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        print(run(a.date, data_dir(), log))
    except Exception:
        log.exception("falha no vigia ipv4")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
