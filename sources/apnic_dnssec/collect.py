# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""APNIC Labs, validação de DNSSEC por ASN no Brasil.

Fonte:       https://stats.labs.apnic.net/dnssec/BR (tabela por ASN embutida na página; ver sources/apnic_labs/tabela.py)
Raw:         data/raw/{date}/summary/apnic-dnssec-BR-{as_of}.html.gz
Normalizado: data/normalized/{date}/summary/apnic_dnssec.json.gz   {snapshot_date, as_of, janela_dias, copyright, asns: {asn: {validates_pct, parcial_pct, amostras}}}
Licença:     o JSON do APNIC traz "(c) APNIC Pty/Ltd. re-use with attribution permitted": citar APNIC Labs como fonte.

Uso:
    python -m sources.apnic_dnssec.collect --date 2026-10-31
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

from core.common import configure_logging, data_dir, gravar_texto_gz, normalized_path, now_iso, raw_path, today_str, write_json_gz
from sources.apnic_labs import tabela
from core.site import USER_AGENT

URL = "https://stats.labs.apnic.net/dnssec/BR"
HEADERS = {"User-Agent": USER_AGENT}
JANELA_DIAS = 1
MINIMO_ASNS = 1000                                  # ASNs do Brasil com medição: bem menos que isso é página truncada
COPYRIGHT = "(c) APNIC Pty/Ltd. re-use with attribution permitted"


def normalizar(html: str, date_str: str) -> dict:
    t = tabela.parse_tabela(html, "dnssec")
    as_of = tabela.ultima_data_da_serie(html)
    if as_of is None or len(t["asns"]) < MINIMO_ASNS:
        raise RuntimeError(f"apnic_dnssec: {len(t['asns'])} ASNs com medição (esperado ≥ {MINIMO_ASNS}) e data {as_of}")
    asns = {str(a): {"validates_pct": v["valores"][0], "parcial_pct": v["valores"][1], "amostras": v["amostras"]} for a, v in sorted(t["asns"].items())}
    return {"snapshot_date": date_str, "generated_at": now_iso(), "as_of": as_of, "janela_dias": JANELA_DIAS, "copyright": COPYRIGHT,
            "fonte": URL, "asns_sem_medicao": t["sem_valor"], "total": len(asns), "asns": asns}


def run(date_str: str, base: Path, log) -> dict:
    with httpx.Client(timeout=180, follow_redirects=True, headers=HEADERS) as client:
        r = client.get(URL)
        r.raise_for_status()
    html = r.text
    saida = normalizar(html, date_str)
    raw_dir = raw_path(base, date_str, "summary")
    raw_dir.mkdir(parents=True, exist_ok=True)
    gravar_texto_gz(raw_dir / f"apnic-dnssec-BR-{saida['as_of']}.html.gz", html)
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    write_json_gz(destino / "apnic_dnssec.json.gz", saida)
    log.info("apnic_dnssec written", asns=saida["total"], sem_medicao=saida["asns_sem_medicao"], as_of=saida["as_of"])
    return saida


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="APNIC Labs, validação de DNSSEC por ASN (Brasil)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre refeita")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        run(a.date, data_dir(), log)
    except Exception:
        log.exception("falha na coleta de apnic_dnssec")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
