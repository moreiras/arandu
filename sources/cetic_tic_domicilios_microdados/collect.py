# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cetic.br: TIC Domicílios, microdados → estimativas por UF com erro-padrão.

Fonte:       https://cetic.br/pt/pesquisa/domicilios/microdados/ (CSV da base de domicílios da edição vigente, desidentificado, CC BY 4.0; sem API)
Bruto:       data/raw/{date}/summary/<arquivo da edição>.csv.gz (a base inteira, comprimida; é de domicílios sem identificação, e não é publicada)
Normalizado: data/normalized/{date}/summary/cetic_tic_domicilios_uf.json.gz   {grupos: {BR, região, UF: {n, domicilios, indicadores: {...}}}, metodo, ...}
O cálculo (200 pesos de réplica, margem = 1,96 × erro-padrão, supressão por amostra mínima) está em core/cetic_microdados.py.

Uso:
    python -m sources.cetic_tic_domicilios_microdados.collect --date 2026-11-01
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import sys
import time
from pathlib import Path
from typing import Callable, Optional

import httpx

from core import cetic, cetic_microdados as md
from core.common import configure_logging, data_dir, normalized_path, now_iso, raw_path, today_str, write_json_gz

PESQUISA, PREFIXO = "domicilios", "tic_domicilios"
SUFIXO = r"domicilios_base_de_microdados_v[\d.]+\.csv"
MINIMO_LINHAS = 10000                                  # a base tem ~27 mil domicílios; bem menos que isso é download truncado


def run(date_str: str, base: Path, log, client: Optional[httpx.Client] = None, dormir: Callable[[float], None] = time.sleep) -> dict:
    proprio = client is None
    client = client or httpx.Client(timeout=300, follow_redirects=True, headers=cetic.HEADERS)
    try:
        pagina = cetic.PAGINA.format(pesquisa=PESQUISA)
        url, ano, nome = cetic.descobrir(cetic._get(client, pagina, dormir).text, PREFIXO, SUFIXO)
        dormir(cetic.PAUSA_S)
        conteudo = cetic._get(client, url, dormir).content
    finally:
        if proprio:
            client.close()
    grupos, lidas = md.estimar(conteudo)
    if lidas < MINIMO_LINHAS:
        raise RuntimeError(f"cetic microdados: só {lidas} domicílios (esperado ≥ {MINIMO_LINHAS}); download truncado?")
    if len([g for g in grupos.values() if g["tipo"] == "uf"]) != 27:
        raise RuntimeError("cetic microdados: a base não traz as 27 UFs")
    bruto = raw_path(base, date_str, "summary")
    bruto.mkdir(parents=True, exist_ok=True)
    with open(bruto / (nome + ".gz"), "wb") as arq, gzip.GzipFile(fileobj=arq, mode="wb", compresslevel=6, mtime=0) as f:
        f.write(conteudo)
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    write_json_gz(destino / "cetic_tic_domicilios_uf.json.gz", {
        "snapshot_date": date_str, "generated_at": now_iso(), "natureza": "estimativa_arandurape", "pesquisa": "TIC Domicílios", "edicao": ano,
        "fonte": f"Estimativa do Arandurapé a partir dos microdados da TIC Domicílios {ano} (Cetic.br|NIC.br)", "licenca": cetic.LICENCA,
        "pagina": pagina, "url": url, "arquivo": nome, "sha256": hashlib.sha256(conteudo).hexdigest(), "domicilios_entrevistados": lidas,
        "metodo": {"replicas": md.REPLICAS, "variancia": "média dos quadrados dos desvios das réplicas em torno da estimativa pontual", "margem": "1,96 × erro-padrão (95%)",
                   "supressao_n_minimo": md.N_MINIMO, "precisao_baixa_cv": md.CV_BAIXO},
        "indicadores": {i: {"rotulo": r, "definicao": d} for i, (_, _, r, d) in md.INDICADORES.items()},
        "grupos": grupos})
    log.info("cetic microdados written", edicao=ano, domicilios=lidas, grupos=len(grupos))
    return {"edicao": ano, "domicilios": lidas, "grupos": len(grupos)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="TIC Domicílios: estimativas por UF a partir dos microdados (Cetic.br)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre refeita")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        print(run(a.date, data_dir(), log))
    except Exception:
        log.exception("falha na coleta de cetic_tic_domicilios_microdados")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
