# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""abuse.ch: contagens **agregadas por ASN** de servidores de comando e controle de botnets do Feodo Tracker (CC0).

Só o Feodo Tracker (`https://feodotracker.abuse.ch/downloads/ipblocklist.json`, sem cadastro, `robots.txt` livre). O URLhaus exige `Auth-Key` (cadastro): o arquivo
`csv_recent` responde 410 e a API pede a chave; sem cadastro não se coleta. Nenhum IP, porta ou hostname é gravado: só contagens por ASN.
Em 2026-11-06 o Feodo está quase vazio (a própria página diz "datasets currently empty"): 5 entradas no mundo, nenhuma no Brasil. Zero é resultado válido.

Normalizado: data/normalized/{date}/summary/abusech.json.gz
             {snapshot_date, fetched_at, fonte, licenca, feodo: {total, online, asns: {asn: {c2_total, c2_online, malware: {familia: n}}}}, urlhaus: {estado, motivo}}

Uso:
    python -m sources.abusech.collect --date 2026-11-05
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import httpx

from core.common import configure_logging, data_dir, normalized_path, now_iso, today_str, write_json_gz
from core.site import USER_AGENT

URL_FEODO = "https://feodotracker.abuse.ch/downloads/ipblocklist.json"
HEADERS = {"User-Agent": USER_AGENT}


def agregar(entradas: list[dict]) -> dict:
    """Contagens por ASN a partir da lista do Feodo; o IP, a porta e o hostname são descartados aqui."""
    por: dict[str, dict] = {}
    for e in entradas:
        a = e.get("as_number")
        if a is None:
            continue
        d = por.setdefault(str(int(a)), {"c2_total": 0, "c2_online": 0, "malware": Counter()})
        d["c2_total"] += 1
        d["c2_online"] += 1 if e.get("status") == "online" else 0
        if e.get("malware"):
            d["malware"][e["malware"]] += 1
    return {"total": len(entradas), "online": sum(1 for e in entradas if e.get("status") == "online"),
            "asns": {a: {**d, "malware": dict(sorted(d["malware"].items()))} for a, d in sorted(por.items(), key=lambda kv: int(kv[0]))}}


def run(date_str: str, base: Path, log) -> dict:
    with httpx.Client(timeout=60, follow_redirects=True, headers=HEADERS) as client:
        r = client.get(URL_FEODO)
        r.raise_for_status()
        dados = r.json()
    if not isinstance(dados, list):
        raise RuntimeError("abusech: a lista do Feodo Tracker não veio como array JSON")
    feodo = agregar(dados)
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    write_json_gz(destino / "abusech.json.gz", {
        "snapshot_date": date_str, "fetched_at": now_iso(), "fonte": URL_FEODO, "licenca": "CC0 (Feodo Tracker, abuse.ch)", "feodo": feodo,
        "urlhaus": {"estado": "indisponivel", "motivo": "exige Auth-Key (cadastro); não coletado (I-008)"}})
    log.info("abusech written", feodo_total=feodo["total"], asns=len(feodo["asns"]))
    return {"total": feodo["total"], "asns": len(feodo["asns"])}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="abuse.ch: Feodo Tracker agregado por ASN")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre refeita")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        run(a.date, data_dir(), log)
    except Exception:
        log.exception("falha na coleta de abusech")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
