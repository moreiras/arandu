# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Carregadores de entradas do `metricas_ixp_asn`: relações e prefixos por IXP, Registro.br, LACNIC, AS_PATH, PeeringDB, APNIC e geo."""
from __future__ import annotations

import gzip
import json
from pathlib import Path
from core.common import normalized_path


def _load_gz_json(path: Path, default):
    """Carrega JSON gzip; retorna default se arquivo ausente ou corrompido."""
    if not path.exists():
        return default
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _load_rels(base: Path, date_str: str, source: str, afi: str) -> dict:
    """Carrega relationships+stats do arquivo normalizado (sem as rotas)."""
    path = normalized_path(base, date_str, source) / f"routes-{afi}.json.gz"
    data = _load_gz_json(path, {})
    data.pop("routes", None)
    return data


def _load_origin_prefixes(base: Path, date_str: str, source: str, afi: str) -> dict[str, list[str]]:
    """Carrega {str(asn): [prefix, ...]} do índice compacto de origens."""
    path = normalized_path(base, date_str, source) / f"origin-prefixes-{afi}.json.gz"
    return _load_gz_json(path, {})


def _load_prefix_set(base: Path, date_str: str, source: str, afi: str) -> set[str]:
    """Carrega conjunto de prefixos únicos de uma fonte."""
    path = normalized_path(base, date_str, source) / f"prefix-set-{afi}.json.gz"
    return set(_load_gz_json(path, []))


def _load_registro_br(base: Path, date_str: str) -> dict[int, dict]:
    """
    Carrega dados do Registro.br (`registro_br` — nicbr-asn-blk).
    Retorna {asn: {"name": ..., "cnpj": ..., "prefixes_v4": [...], "prefixes_v6": [...]}}.
    Usado exclusivamente para dados de prefixos IP (rir_prefixes).
    Para determinar is_br use _load_lacnic_br_asns().
    """
    path = normalized_path(base, date_str, "summary") / "registro_br.json.gz"
    data = _load_gz_json(path, {})
    if not data:
        return {}
    return {
        entry["asn"]: {
            "name": entry.get("name", ""),
            "cnpj": entry.get("cnpj", ""),
            "prefixes_v4": entry.get("prefixes_v4", []),
            "prefixes_v6": entry.get("prefixes_v6", []),
        }
        for entry in data.get("asns", [])
    }


def _load_lacnic_br_asns(base: Path, date_str: str) -> set[int]:
    """
    Carrega ASNs alocados pelo LACNIC ao Brasil (`lacnic_delegated` — delegated-lacnic-extended).
    Fonte autoritativa para is_br: inclui apenas ASNs registrados por entidades BR,
    excluindo ASNs estrangeiros que porventura detenham blocos IP brasileiros.
    Retorna set vazio se o arquivo ainda não existir (fallback: usa nicbr_map keys).
    """
    path = normalized_path(base, date_str, "summary") / "lacnic_delegated.json.gz"
    data = _load_gz_json(path, {})
    if not data:
        return set()
    return set(data.get("br_asns", []))


def _load_aspath_adj(base: Path, date_str: str, afi: str) -> dict[str, dict]:
    """
    Carrega grafo de adjacências do RouteViews.
    Retorna {str(asn): {"up": [...], "down": [...]}} ou {} se não disponível.
    """
    path = normalized_path(base, date_str, "summary") / f"aspath-adj-{afi}.json.gz"
    return _load_gz_json(path, {})


def _load_peeringdb_ixps(base: Path, date_str: str) -> dict:
    """
    Carrega peeringdb_ixps.json.gz (`peeringdb_ixps`).
    Retorna {'per_asn': {str(asn): {'external': [...], 'ixbr': [...]}}, ...}
    ou {} se não disponível.
    """
    path = normalized_path(base, date_str, "summary") / "peeringdb_ixps.json.gz"
    return _load_gz_json(path, {})


def _load_peeringdb_networks(base: Path, date_str: str) -> dict:
    """
    Carrega peeringdb_networks.json.gz (`peeringdb_networks`).
    Retorna {'networks': {str(asn): {...}}} ou {} se não disponível.
    """
    path = normalized_path(base, date_str, "summary") / "peeringdb_networks.json.gz"
    data = _load_gz_json(path, {})
    if path.exists() and not (data.get("networks") if isinstance(data, dict) else None):
        # arquivo presente mas vazio ≠ arquivo ausente: todo ASN sairia com pdb_registered=False
        import logging

        logging.getLogger(__name__).warning(
            "peeringdb_networks.json.gz existe mas não tem redes — pdb_registered=False para todos os ASNs "
            "(coleta peeringdb_networks suspeita: o coletor do PeeringDB devia ter falhado)")
    return data


def _load_apnic_pop(base: Path, date_str: str) -> dict[int, dict]:
    """
    Carrega apnic_pop.json.gz (`apnic_pop` — estimativas APNIC Labs).
    Retorna {asn_int: {users, users_pct_cc, v6_users, v6_pct_as}} ou {} se ausente.
    """
    path = normalized_path(base, date_str, "summary") / "apnic_pop.json.gz"
    raw = _load_gz_json(path, {})
    asns_raw = raw.get("asns", {})
    return {int(k): v for k, v in asns_raw.items()}


def _load_geo_orgs(base: Path, date_str: str) -> dict[str, dict]:
    """
    Carrega geo_orgs.json.gz (enrich/cnpj_geo).
    Retorna {str(asn): {lat, lon, city, uf, geo_confidence, geo_source, ...}} ou {} se ausente.
    """
    path = normalized_path(base, date_str, "summary") / "geo_orgs.json.gz"
    data = _load_gz_json(path, {})
    return data.get("orgs", {}) if data else {}


def _load_geo_prefixes(base: Path, date_str: str) -> dict[str, dict]:
    """
    Carrega geo_prefixes.json.gz (`prefix_geo` — prefixos BR declarados no Registro.br).
    Retorna {prefix: {lat, lon, city, uf, country, geo_confidence, geo_source}} ou {} se ausente.
    """
    path = normalized_path(base, date_str, "summary") / "geo_prefixes.json.gz"
    data = _load_gz_json(path, {})
    return data.get("prefixes", {}) if data else {}


def _load_asn_names_bulk(base: Path, date_str: str) -> dict[int, str]:
    """
    Carrega nomes de ASNs do bulk collector (`asn_names` — asn.txt/RIPE NCC).
    Cobre ~100k ASNs globais; usado como fallback após Registro.br e PeeringDB.
    Retorna {asn_int: nome_str} ou {} se o arquivo não existir.
    """
    path = normalized_path(base, date_str, "summary") / "asn_names.json.gz"
    data = _load_gz_json(path, {})
    if not data:
        return {}
    return {int(k): v for k, v in data.items() if k.isdigit()}
