# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""CAIDA AS Rank: rank, grau e cone de cada ASN do Brasil, pela API REST pública do CAIDA.

Fonte:       https://api.asrank.caida.org/v2/restful/asns/?first=N&offset=M (listagem paginada de todos os ~123 mil ASNs; filtramos o país BR)
Normalizado: data/normalized/{date}/summary/caida_asrank.json.gz
             {snapshot_date, fetched_at, total_global, copyright, asns: {asn: {rank, fonte_rir, clique, org_id, cone: {asns, prefixos, enderecos},
              grau: {total, cliente, par, provedor}}}}
Licença:     dados públicos do CAIDA: citar "The CAIDA UCSD AS Rank" (https://asrank.caida.org). O AS Rank é inferência do CAIDA sobre a tabela de rotas.

Uso:
    python -m sources.caida_asrank.collect --date 2026-10-31
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx

from core.common import configure_logging, data_dir, normalized_path, now_iso, today_str, write_json_gz
from core.site import USER_AGENT

URL = "https://api.asrank.caida.org/v2/restful/asns/"
HEADERS = {"User-Agent": USER_AGENT}
PAGINA = 10000
ESPERA_S = 1.0
MINIMO_GLOBAL = 100_000                                   # a base tem ~123 mil ASNs: bem menos que isso é listagem truncada
MINIMO_BR = 1_000
CITACAO = "The CAIDA UCSD AS Rank, https://asrank.caida.org (inferência do CAIDA sobre a tabela de rotas pública)"


def extrair_br(pagina: dict, pais: str = "BR") -> list[dict]:
    """ASNs do país numa página da API (`data.asns.edges[].node`), já no formato normalizado."""
    out = []
    for e in pagina["data"]["asns"]["edges"]:
        n = e["node"]
        if (n.get("country") or {}).get("iso") != pais:
            continue
        cone, grau = n.get("cone") or {}, n.get("asnDegree") or {}
        out.append({"asn": int(n["asn"]), "rank": n.get("rank"), "fonte_rir": n.get("source"), "clique": bool(n.get("cliqueMember")),
                    "org_id": (n.get("organization") or {}).get("orgId"),
                    "cone": {"asns": cone.get("numberAsns"), "prefixos": cone.get("numberPrefixes"), "enderecos": cone.get("numberAddresses")},
                    "grau": {"total": grau.get("total"), "cliente": grau.get("customer"), "par": grau.get("peer"), "provedor": grau.get("provider")}})
    return out


def baixar_pagina(client: httpx.Client, offset: int, tentativas: int = 3) -> dict:
    for t in range(1, tentativas + 1):
        try:
            r = client.get(URL, params={"first": PAGINA, "offset": offset})
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError):
            if t == tentativas:
                raise
            time.sleep(ESPERA_S * 5 * t)
    raise AssertionError("inalcançável")


def run(date_str: str, base: Path, log, espera_s: float = ESPERA_S) -> dict:
    asns: list[dict] = []
    offset = 0
    total = 0
    with httpx.Client(timeout=180, follow_redirects=True, headers=HEADERS) as client:
        while True:
            pg = baixar_pagina(client, offset)
            info = pg["data"]["asns"]
            total = info["totalCount"]
            asns += extrair_br(pg)
            if not info["pageInfo"]["hasNextPage"] or not info["edges"]:
                break
            offset += PAGINA
            time.sleep(espera_s)
    if total < MINIMO_GLOBAL or len(asns) < MINIMO_BR:
        raise RuntimeError(f"caida_asrank: {total} ASNs na base e {len(asns)} do Brasil (esperado ≥ {MINIMO_GLOBAL} e ≥ {MINIMO_BR})")
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    por = {str(a.pop("asn")): a for a in sorted(asns, key=lambda x: x["asn"])}
    write_json_gz(destino / "caida_asrank.json.gz", {"snapshot_date": date_str, "fetched_at": now_iso(), "total_global": total, "copyright": CITACAO,
                                                     "total": len(por), "asns": por})
    log.info("caida_asrank written", asns_br=len(por), total_global=total)
    return {"asns_br": len(por), "total_global": total}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="CAIDA AS Rank (ASNs do Brasil)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre refeita")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        run(a.date, data_dir(), log)
    except Exception:
        log.exception("falha na coleta de caida_asrank")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
