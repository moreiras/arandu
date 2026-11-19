# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Snapshot builder: executa os passos do build de `products.passos` em sequência, num só processo, e fecha com `publish.manifesto`.
O caminho principal é o `arandu` (um passo do catálogo por produto); este módulo atende o replay e as operações
pontuais sobre snapshots já publicados (`--detail-only`, `--asn-health-only`).

Entradas (published/{date}/):
  ixps/{ixp}.json          — gerados por `metricas_ixp_asn`
  asns/{asn}.json          — gerados por `metricas_ixp_asn`

Entradas (raw/ e normalized/):
  raw/{date}/{ixp}/bgp-*.txt
  raw/{date}/summary/bgp-*-fulltable-*.txt
  normalized/{date}/summary/registro_br.json.gz
  normalized/{date}/summary/prefix-set-v4.json.gz

Saídas (published/{date}/):
  ixps/index.json           — lista compacta de IXPs (para API /ixps)
  asns/index.json           — lista compacta de ASNs (para API /asns)
  hilbert_v4.json           — mapas de densidade /16 para 4 camadas Hilbert
  hilbert_v6.json           — mapas de presença /32 IPv6 para 6 blocos RIR
  summary.json              — totais e estatísticas globais
  manifest.json             — metadados do pipeline + checksums SHA-256 de todos os demais

O manifesto é sempre o último arquivo escrito. Snapshots são imutáveis após publicação.

Uso:
  python -m publish.snapshot_builder --date 2026-06-01
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import ipaddress
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
from pathlib import Path

from core import compose
from products import passos
from publish import manifesto
from core.integridade import calcular_checksums, sha256_arquivo
from core.jsonio import carregar_json, carregar_json_gz, gravar_json_gz
from core.outorgas import SERVICOS
from products.cdns.build import publicar_cdn_presence
from products.grupos_societarios.build import publicar_grupos_societarios
from products.asn_docs.build import (executar_indice as executar_asn_indice, executar_ixp_paths, executar_nomes,
                                     publicar_asn_index as build_asn_index, publicar_asn_names as build_asn_names,  # noqa: F401
                                     publicar_ixp_paths as build_ixp_paths_for_asns)
from products.ixp_docs.build import (executar_externos, executar_indice as executar_ixp_indice, publicar_external_ixps,  # noqa: F401
                                     publicar_ixp_index as build_ixp_index)
from products.mapas_prefixos.build import (executar_hilbert, executar_mapas,
                                           _compute_v6_sparse, _density_from_slash24_intersection, _prefix_to_16_density,  # noqa: F401
                                           _slash24_bitset, _slash24_set, _v6_prefix_to_cells, build_geojson_maps,  # noqa: F401
                                           build_global_prefixes_map, build_hilbert_v4, build_hilbert_v6, compute_density)
from products.mapas_infraestrutura.build import publicar_infra_maps
from products.outorgas.build import publicar_outorgas
from products.asn_saude.build import publicar_asn_saude
from products.sici.build import publicar_sici, publicar_sici_movel
from products.snapshot.build import (executar_resumo,
                                      _IPV6_48, _load_global_metrics, _load_registro_br_stats, montar_manifesto as build_manifest,  # noqa: F401
                                      publicar_summary as build_summary)
from publish import coleta_checks
from core.common import (
    raw_bgp_ixp,
    raw_existente,
    app_version,
    configure_logging,
    data_dir,
    load_ixps,
    load_peeringdb_ixps_config,
    normalized_path,
    now_iso,
    published_path,
    raw_path,
    today_str,
)

PIPELINE_VERSION = app_version()  # arquivo VERSION (fonte única)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256_file(path: Path) -> str:
    return sha256_arquivo(path)


_load_json = carregar_json          # nomes históricos deste módulo (leitura tolerante: core/jsonio.py)
_load_json_gz = carregar_json_gz
_write_json_gz_pub = gravar_json_gz


def _ixp_raw_status(base: Path, date_str: str, code: str) -> str:
    """ok | partial | missing — baseado na presença de arquivos raw."""
    rd = raw_path(base, date_str, code)
    v4 = raw_bgp_ixp(rd, "v4", code, date_str).exists()
    v6 = raw_bgp_ixp(rd, "v6", code, date_str).exists()
    if v4 and v6:
        return "ok"
    if v4 or v6:
        return "partial"
    return "missing"


def compute_checksums(pub_dir: Path, skip: frozenset[str] = frozenset()) -> dict[str, str]:
    """SHA-256 de todos os arquivos em pub_dir, exceto os listados em skip (checksums parciais do `snapshot_completo`; os finais vêm do `refresh_manifest`)."""
    return calcular_checksums(pub_dir, skip)


def build_asn_health_for_asns(base: Path, date_str: str, log, force: bool = False) -> int:
    """Saúde do ASN (ver `products.asn_saude.build.publicar_asn_saude`); o `Store` da API é injetado daqui."""
    from api.store import Store

    return publicar_asn_saude(base, date_str, log, Store, force)


# ---------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------

def build_external_ixps(base: Path, date_str: str, br_asns: set[int], log) -> int:
    """IXPs externos (ver `products.ixp_docs.build`). O carregador da config é injetado daqui para os testes poderem trocá-lo."""
    return publicar_external_ixps(base, date_str, br_asns, log, load_peeringdb_ixps_config)


def build_cdn_presence(base: Path, date_str: str, log) -> int:
    """Presença de CDNs nos IXPs (ver `products.cdns.build`)."""
    return publicar_cdn_presence(base, date_str, log)


def _resumo_outorgas(resultados: dict, siglas: tuple) -> dict:
    """{sigla}_total e {sigla}_matched_asns de cada serviço, no formato do manifesto."""
    return {k: resultados.get(sigla, {}).get(k, 0) for sigla in siglas for k in (f"{sigla}_total", f"{sigla}_matched_asns")}


# ---------------------------------------------------------------------------
# Outorgas da Anatel (SCM, SMP, STFC, SeAC)
# ---------------------------------------------------------------------------
# Uma implementação (products/outorgas/build.py) para os quatro serviços; os nomes abaixo continuam existindo porque
# o run() e o CLI deste módulo, a documentação e os testes os chamam.

def build_scm_data(base: Path, date_str: str, log) -> dict:
    """SCM. Ver `products.outorgas.build.publicar_outorgas`."""
    return publicar_outorgas(SERVICOS["scm"], base, date_str, log)


def build_smp_data(base: Path, date_str: str, log) -> dict:
    """SMP (o enriquecimento de rede virtual é feito na coleta)."""
    return publicar_outorgas(SERVICOS["smp"], base, date_str, log)


def build_stfc_data(base: Path, date_str: str, log) -> dict:
    """STFC."""
    return publicar_outorgas(SERVICOS["stfc"], base, date_str, log)


def build_seac_data(base: Path, date_str: str, log) -> dict:
    """SeAC."""
    return publicar_outorgas(SERVICOS["seac"], base, date_str, log)


# ---------------------------------------------------------------------------
# Infraestrutura física de fundo (ITU + TeleGeography)
# ---------------------------------------------------------------------------

def build_infra_maps(base: Path, date_str: str, log) -> dict:
    """Camadas de fundo de infraestrutura física (ver `products.mapas_infraestrutura.build`)."""
    return publicar_infra_maps(base, date_str, log)


# ---------------------------------------------------------------------------
# SICI fixo e móvel e grupos societários (em products/sici e products/grupos_societarios)
# ---------------------------------------------------------------------------

def build_sici_data(base: Path, date_str: str, log, republicar_scm: bool = False) -> dict:
    """Acessos SICI fixos (ver `products.sici.build.publicar_sici`)."""
    return publicar_sici(base, date_str, log, republicar_scm)


# ---------------------------------------------------------------------------
# Acessos móveis SICI (Anatel)
# ---------------------------------------------------------------------------

def build_sici_movel_data(base: Path, date_str: str, log) -> dict:
    """Acessos SICI móveis (ver `products.sici.build.publicar_sici_movel`)."""
    return publicar_sici_movel(base, date_str, log)


def build_grupos_societarios_data(base: Path, date_str: str, log) -> dict:
    """Grupos societários (ver `products.grupos_societarios.build`)."""
    return publicar_grupos_societarios(base, date_str, log)


def run(date_str: str, base: Path, log) -> dict:
    """Caminho legado (um processo): executa os passos do build na ORDEM de `products.passos` e escreve o manifesto no fim.

    No arandu, cada passo é uma etapa do catálogo (`catalog/steps/<passo>.yaml`) e o manifesto é a última etapa; aqui os carregadores de
    configuração são os deste módulo, que os testes e o replay substituem."""
    all_ixps = load_ixps()
    pub_dir = published_path(base, date_str)
    ctx = passos.Contexto(base, date_str, log, ixps=lambda: load_ixps(), config_peeringdb=lambda: load_peeringdb_ixps_config())
    ordem = list(passos.ORDEM)
    if not compose.ativo():          # ARANDU_COMPOSE=off (fluxo sem fragmentos): o SCM é publicado antes e o SICI o reescreve
        i, j = ordem.index("sici"), ordem.index("outorgas_scm")
        ordem[i], ordem[j] = ordem[j], ordem[i]
    r = {pid: passos.executar(pid, ctx) for pid in ordem}

    summary = json.loads((pub_dir / "summary.json").read_text(encoding="utf-8"))
    asn_index = json.loads((pub_dir / "asns" / "index.json").read_text(encoding="utf-8"))
    ixp_index = json.loads((pub_dir / "ixps" / "index.json").read_text(encoding="utf-8"))
    outorgas_result = {"scm": r["outorgas_scm"], **r["outorgas_demais"]}
    sici_result, infra_result = r["sici"], r["mapas_infraestrutura"]
    sici_movel_result, grupos_societarios_result = r["sici_movel"], r["grupos_societarios"]
    geo_counts = r["mapas_geo"]
    ASN_INDEX = r["asn_indice"]
    ext_ixps_count, cdn_count = r["ixp_externos"]["external_ixps"], r["cdns"]["cdn_count"]
    ixp_paths_enriched, asn_names_count = r["asn_ixp_paths"]["ixp_paths_enriched"], r["asn_nomes"]["asn_names"]

    # PeeringDB contacts: NÃO copiado para published/ (AUP PeeringDB).
    # A Store lê direto de normalized/{date}/summary/peeringdb_contacts.json.gz.
    pdb_contacts_count = 0

    manifesto_final = manifesto.fechar(base, date_str, log, all_ixps)
    checksums = manifesto_final.get("checksums", {})

    return {
        "ixps_indexed": len(ixp_index),
        "asns_indexed": ASN_INDEX["asns_indexed"],
        "asn_names": asn_names_count,
        "ixp_paths_enriched": ixp_paths_enriched,
        "external_ixps": ext_ixps_count,
        "cdn_count": cdn_count,
        "geo_asns": geo_counts["geo_asns"],
        "geo_prefixes": geo_counts["geo_prefixes"],
        "geo_global_prefixes": geo_counts["geo_global_prefixes"],
        **_resumo_outorgas(outorgas_result, ("scm",)),
        "sici_cnpjs": sici_result.get("sici_cnpjs", 0),
        "sici_acessos": sici_result.get("sici_acessos", 0),
        "sici_mes_referencia": sici_result.get("sici_mes_referencia", ""),
        **_resumo_outorgas(outorgas_result, tuple(x for x in SERVICOS if x != "scm")),
        "itu_links": infra_result.get("itu_links", 0),
        "submarine_cables": infra_result.get("submarine_cables", 0),
        "submarine_landing_points": infra_result.get("submarine_landing_points", 0),
        "power_transmission_lines": infra_result.get("power_transmission_lines", 0),
        "ibge_rodovias": infra_result.get("ibge_rodovias", 0),
        "sici_movel_cnpjs": sici_movel_result.get("sici_movel_cnpjs", 0),
        "sici_movel_acessos": sici_movel_result.get("sici_movel_acessos", 0),
        "sici_movel_mes_referencia": sici_movel_result.get("sici_movel_mes_referencia", ""),
        "grupos_societarios_total": grupos_societarios_result.get("grupos_societarios_total", 0),
        "grupos_societarios_cnpjs": grupos_societarios_result.get("grupos_societarios_cnpjs", 0),
        "pdb_contacts": pdb_contacts_count,
        "files_checksummed": len(checksums),
    }


def _indice_ja_tem_rpki(base: Path, date_str: str, index_path: Path) -> bool:
    """O índice foi gravado DEPOIS da coleta do RPKI (ou não há RPKI): reescrevê-lo daria o mesmo arquivo."""
    rpki = published_path(base, date_str, "rpki") / "vrp_list.json.gz"
    if not index_path.exists():
        return False
    return (not rpki.exists()) or index_path.stat().st_mtime >= rpki.stat().st_mtime


def run_asn_health_only(base: Path, date_str: str, log, force: bool = False) -> int:
    """`saude_asn`: pré-calcula alerts + RPKI por ASN e reconstrói `asns/index.json`.

    Usada pelo CLI (`--asn-health-only`), pelo replay (scripts/replay.py) e pelos testes de produto,
    para que os três executem exatamente a mesma sequência."""
    n = build_asn_health_for_asns(base, date_str, log, force=force)
    log.info("asn health backfill complete", date=date_str, enriched=n)
    # Reconstruir índice para que has_rpki/has_aspa reflitam os dados RPKI coletados
    # após o `snapshot_completo` original. O build_asn_index relê os VRPs/ASPAs do diretório rpki/.
    asn_index_path = published_path(base, date_str, "asns") / "index.json"
    if compose.fluxo_novo(base, date_str) and _indice_ja_tem_rpki(base, date_str, asn_index_path):
        log.info("asn index already built after the RPKI collection, not rewritten", date=date_str)   # RPKI antes do `snapshot_completo`: 1 escrita
    else:
        asn_index, *_ = build_asn_index(base, date_str, log)
        asn_index_path.write_text(json.dumps(asn_index, ensure_ascii=False), encoding="utf-8")
        log.info("asn index rebuilt", date=date_str, asns=len(asn_index))
    coleta_checks.refresh_manifest(base, date_str, log, checksums=True)     # agora com VRPs (RPKI já coletado) e checksums de TUDO
    return n


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="`snapshot_completo` — Snapshot builder: índices, summary e manifesto"
    )
    parser.add_argument("--date", default=today_str(), help="Data do snapshot (YYYY-MM-DD)")
    parser.add_argument(
        "--asn-health-only",
        action="store_true",
        help="Roda apenas o pré-cálculo de alerts + RPKI nos arquivos ASN existentes "
             "(backfill de um snapshot já publicado, sem reconstruir o resto).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Com --asn-health-only, força reenriquecimento mesmo se o ASN já tem "
             "alerts/RPKI computados (necessário após mudar a lógica de enrich_asn_document).",
    )
    parser.add_argument(
        "--geo-maps-only",
        action="store_true",
        help="Regenera apenas maps/asns.geojson e maps/prefixes.geojson (sem reconstruir "
             "índices, Hilbert, SCM, etc.). Útil para reaplicar correções de geocodificação "
             "a um snapshot já publicado.",
    )
    parser.add_argument(
        "--sici-only",
        action="store_true",
        help="Regenera apenas sici.json.gz, sici_municipios.json.gz e a injeção de "
             "acessos nos documentos de ASN/SCM. Requer que a coleta anatel_sici já tenha rodado.",
    )
    for sigla, svc in SERVICOS.items():                 # --scm-only, --smp-only, --stfc-only, --seac-only… (registro único)
        parser.add_argument(
            f"--{sigla}-only",
            action="store_true",
            help=f"Regenera apenas {sigla}.json.gz e maps/{svc.mapa}. Requer que a geocodificação ({sigla}_geo) já tenha rodado.",
        )
    parser.add_argument(
        "--infra-only",
        action="store_true",
        help="Regenera apenas maps/itu_transmission.geojson, maps/submarine_cables.geojson, "
             "maps/submarine_landing_points.geojson, maps/power_transmission_lines.geojson e "
             "maps/ibge_rodovias.geojson. Requer que itu_transmission, telegeography_cables, aneel_sigel_transmission e ibge_bc250_rodovias já tenham rodado.",
    )
    parser.add_argument(
        "--sici-movel-only",
        action="store_true",
        help="Regenera apenas sici_movel.json.gz e sici_movel_municipios.json.gz. "
             "Requer que a coleta anatel_sici_movel já tenha rodado.",
    )
    parser.add_argument(
        "--detail-only",
        action="store_true",
        help="Gera apenas snapshot_detail.json (detalhe de /snapshots/{date}) de um snapshot já publicado: "
             "backfill aditivo, não altera nenhum arquivo existente.",
    )
    parser.add_argument(
        "--grupos-societarios-only",
        action="store_true",
        help="Regenera apenas grupos_societarios.json.gz. Requer que receita_socios e socios_grupos já tenham rodado.",
    )
    args = parser.parse_args(argv)

    log = configure_logging()
    base = data_dir()

    if args.geo_maps_only:
        geo_counts = build_geojson_maps(base, args.date, log)
        log.info("geo maps rebuilt", date=args.date, **geo_counts)
        return 0

    if args.sici_only:
        sici_result = build_sici_data(base, args.date, log, republicar_scm=True)
        log.info("sici rebuilt", date=args.date, **sici_result)
        return 0

    for sigla, svc in SERVICOS.items():
        if getattr(args, f"{sigla}_only"):
            resultado = publicar_outorgas(svc, base, args.date, log)
            log.info(f"{sigla} rebuilt", date=args.date, **resultado)
            return 0

    if args.infra_only:
        infra_result = build_infra_maps(base, args.date, log)
        log.info("infra maps rebuilt", date=args.date, **infra_result)
        return 0

    if args.sici_movel_only:
        sici_movel_result = build_sici_movel_data(base, args.date, log)
        log.info("sici movel rebuilt", date=args.date, **sici_movel_result)
        return 0

    if args.detail_only:
        from api import snapshot_detail

        path = snapshot_detail.build_sidecar(base, args.date, log)
        log.info("snapshot detail backfill", date=args.date, path=str(path) if path else None)
        return 0 if path else 1

    if args.grupos_societarios_only:
        grupos_result = build_grupos_societarios_data(base, args.date, log)
        log.info("grupos societarios rebuilt", date=args.date, **grupos_result)
        return 0

    if args.asn_health_only:
        run_asn_health_only(base, args.date, log, force=args.force)
        return 0

    result = run(date_str=args.date, base=base, log=log)
    log.info("snapshot complete", **result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
