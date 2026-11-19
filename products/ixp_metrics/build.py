# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Métricas de IXP     → published/{date}/ixps/{ixp}.json
Documentos de ASN   → published/{date}/asns/{asn}.json

Entradas:
  normalized/{date}/{ixp}/routes-{afi}.json.gz          — rotas+relações (`bgp_ixp`)
  normalized/{date}/{ixp}/origin-prefixes-{afi}.json.gz — {asn→prefixos} (`bgp_ixp`)
  normalized/{date}/{ixp}/prefix-set-{afi}.json.gz      — [prefixos] (`bgp_ixp`)
  normalized/{date}/summary/routes-{afi}.json.gz        — tabela global via RouteViews (`fulltable_routeviews`)
  normalized/{date}/summary/origin-prefixes-{afi}.json.gz
  normalized/{date}/summary/prefix-set-{afi}.json.gz
  normalized/{date}/summary/registro_br.json.gz         — prefixos IP declarados no NICBR/ASN-BLK (`registro_br`)
  normalized/{date}/summary/lacnic_delegated.json.gz    — ASNs alocados ao BR pelo LACNIC (`lacnic_delegated`)
  normalized/{date}/summary/aspath-adj-{afi}.json.gz    — grafo de adjacências RouteViews (`fulltable_routeviews`)
  normalized/{date}/summary/peeringdb_ixps.json.gz      — membros externos de IXPs (`peeringdb_ixps`; opcional)
  normalized/{date}/summary/peeringdb_networks.json.gz  — metadados de redes BR (`peeringdb_networks`; opcional)
  normalized/{date}/summary/apnic_pop.json.gz           — estimativas APNIC Labs (`apnic_pop`; opcional)
  normalized/{date}/summary/asn_names.json.gz           — nomes de ASNs globais (`asn_names`; opcional)

Saídas:
  published/{date}/ixps/{ixp}.json
  published/{date}/ixps/_aggregate.json
  published/{date}/asns/{asn}.json

Semântica das métricas de cobertura de ASNs BR (campo br_asns_origin_pct):
  - Numerador:   ASNs BR que aparecem como originadores (último ASN do AS_PATH) no IXP
  - Denominador: br_asns_in_ft = ASNs BR que originam prefixos na full table global
  → Mede a fração de ASNs BR "visíveis na internet" que também aparecem no IXP.
  → Exclui ASNs sem rota global (alocados mas inativos), evitando denominador inflado.

Semântica das métricas de cobertura de espaço de endereços (campo br_prefix_coverage_pct):
  - Numerador:   endereços IPv4/IPv6 do espaço `registro_br` (Registro.br) cobertos pelo IXP
  - Denominador: total de endereços IPv4/IPv6 declarados no `registro_br`
  → Cobertura inclui supernets e subnets: um /24 no IXP cobre o /24 do `registro_br` mesmo
    que o `registro_br` declare um /22 que o contém.

Uso:
  python -m products.ixp_metrics.build --date 2026-06-06
  python -m products.ixp_metrics.build --date 2026-06-06 --ixp cas laj
  python -m products.ixp_metrics.build --date 2026-06-06 --no-p3
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from core.common import configure_logging, data_dir, load_ixps, today_str

from products.ixp_metrics.entradas import _load_apnic_pop, _load_asn_names_bulk, _load_aspath_adj, _load_geo_orgs, _load_geo_prefixes, _load_gz_json, _load_lacnic_br_asns, _load_registro_br, _load_origin_prefixes, _load_peeringdb_ixps, _load_peeringdb_networks, _load_prefix_set, _load_rels  # noqa: F401
from products.ixp_metrics.espaco import _compute_aggregate_afi, _compute_ixp_afi, _covered_space, _parse_nets, _pct, _pct_space, _total_space  # noqa: F401
from products.ixp_metrics.indice_asn import _build_asn_index  # noqa: F401
from products.ixp_metrics.documentos_asn import gerar_documentos_asn  # noqa: F401
from products.ixp_metrics.metricas_ixp import gerar_metricas_ixp  # noqa: F401


def run(
    date_str: str,
    base: Path,
    ixp_codes: list[str] | None = None,
    sem_metricas_ixp: bool = False,
    sem_documentos_asn: bool = False,
    log=None,
) -> dict:
    """Orquestra as métricas de IXP e os documentos de ASN para uma data.

    Ordem de execução:
      1. Carrega `registro_br` (nicbr_map) e `lacnic_delegated` (lacnic_br_asns) como insumos de ambas as etapas
      2. gerar_metricas_ixp() — gera ixps/*.json
      3. Carrega `asn_names` (bulk_names) — usado apenas pelos documentos de ASN
      4. _build_asn_index() → gerar_documentos_asn() — gera asns/*.json

    Args:
        date_str:  Data do snapshot (YYYY-MM-DD)
        base:      Diretório raiz dos dados
        ixp_codes: Lista de códigos; None = todos os 40 IXPs
        sem_metricas_ixp:   Se True, pula as métricas de IXP (útil para refazer só os documentos de ASN)
        sem_documentos_asn: Se True, pula os documentos de ASN (útil para checar só os IXPs rapidamente)
        log:       Logger estruturado

    Returns:
        {"p2": {"ok": int, "total": int}, "p3": {"ok": int, "errors": int}}
        Chaves com valor {} para etapas puladas.
    """
    nicbr_map = _load_registro_br(base, date_str)
    if not nicbr_map:
        log.warning("registro_br data missing — IP prefix data for BR ASNs will be empty")

    lacnic_br_asns = _load_lacnic_br_asns(base, date_str)
    if lacnic_br_asns:
        log.info("lacnic delegated loaded", br_asns=len(lacnic_br_asns))
    else:
        log.warning("lacnic_delegated data missing — falling back to nicbr_map for is_br")
        lacnic_br_asns = None

    all_ixps = load_ixps()
    if ixp_codes:
        all_ixps = [ix for ix in all_ixps if ix["code"] in ixp_codes]

    log.info(
        "starting metrics",
        date=date_str,
        ixps=len(all_ixps),
        br_asns=len(lacnic_br_asns) if lacnic_br_asns else len(nicbr_map),
    )

    metricas_ixp: dict = {}
    if not sem_metricas_ixp:
        res_metricas = gerar_metricas_ixp(date_str, base, all_ixps, nicbr_map, log, lacnic_br_asns=lacnic_br_asns)
        ok_metricas = sum(1 for r in res_metricas if r["status"] == "ok")
        metricas_ixp = {"ok": ok_metricas, "total": len(res_metricas)}

    bulk_names = _load_asn_names_bulk(base, date_str)
    if bulk_names:
        log.info("asn bulk names loaded", count=len(bulk_names))
    else:
        log.warning("asn_names bulk names not found — non-BR ASNs may lack names (run sources.asn_names.collect)")

    documentos_asn: dict = {}
    if not sem_documentos_asn:
        log.info("building asn index")
        asn_index = _build_asn_index(date_str, base, all_ixps, log)
        log.info("asn index built", asns=len(asn_index))
        documentos_asn = gerar_documentos_asn(
            date_str, base, asn_index, nicbr_map, log,
            lacnic_br_asns=lacnic_br_asns,
            bulk_names=bulk_names,
        )

    return {
        "metricas_ixp": metricas_ixp,
        "documentos_asn": documentos_asn,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI do `metricas_ixp_asn`. Por padrão executa ambas as etapas; use --no-p2/--no-p3 para parciais."""
    parser = argparse.ArgumentParser(
        description="`metricas_ixp_asn` — métricas por IXP e por ASN"
    )
    parser.add_argument("--date", default=today_str())
    parser.add_argument("--ixp", nargs="+", metavar="CODE")
    parser.add_argument(
        "--sem-documentos-asn", "--no-p3", dest="sem_documentos_asn", action="store_true",
        help="gera apenas as métricas de IXP, sem os documentos de ASN (--no-p3: alias)"
    )
    parser.add_argument(
        "--sem-metricas-ixp", "--no-p2", dest="sem_metricas_ixp", action="store_true",
        help="gera apenas os documentos de ASN, reaproveitando as métricas de IXP já gravadas (--no-p2: alias)"
    )
    args = parser.parse_args(argv)

    log = configure_logging()
    base = data_dir()

    result = run(
        date_str=args.date,
        base=base,
        ixp_codes=args.ixp,
        sem_metricas_ixp=args.sem_metricas_ixp,
        sem_documentos_asn=args.sem_documentos_asn,
        log=log,
    )
    log.info("metrics complete", **result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
