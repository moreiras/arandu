# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Publicação das outorgas da Anatel: `publicar_outorgas(servico, …)` serve SCM, SMP, STFC e SeAC.

Saídas por serviço: published/{date}/<sigla>.json.gz e maps/<sigla>s.geojson (formato inalterado).
"""
from __future__ import annotations

import gzip
import json
import re
from pathlib import Path
from typing import Optional

from core import compose
from core.common import build_path, normalized_path, now_iso, published_path
from core.jsonio import carregar_json_gz
from core.outorgas import Servico


_load_json_gz = carregar_json_gz


def aplicar_sici_registro(rec: dict, agg: dict | None, mes_ref: str) -> bool:
    """Escalares do SICI numa outorga SCM: distingue licenciado de efetivamente em operação. True se há acessos declarados."""
    if not agg:
        rec["sici_ativo"] = False
        return False
    rec["sici_ativo"] = True
    rec["sici_mes_referencia"] = mes_ref
    rec["sici_acessos"] = agg["acessos"]
    rec["sici_pf"] = agg["pf"]
    rec["sici_pj"] = agg["pj"]
    rec["sici_municipios"] = agg.get("municipios", 0)
    rec["sici_capacidade_mbps"] = agg.get("capacidade_mbps", 0.0)
    rec["sici_tecnologia"] = agg.get("tecnologia_predominante", "")
    rec["sici_empresa"] = agg.get("empresa", "")
    return True


def aplicar_sici_feature(props: dict, agg: dict | None, mes_ref: str) -> None:
    """O GeoJSON do mapa de SCMs também ganha os acessos, para dimensionar as bolhas."""
    props["sici_ativo"] = bool(agg)
    props["sici_mes_referencia"] = mes_ref if agg else ""
    props["sici_acessos"] = agg["acessos"] if agg else 0
    props["sici_pf"] = agg["pf"] if agg else 0
    props["sici_pj"] = agg["pj"] if agg else 0
    props["sici_municipios"] = agg.get("municipios", 0) if agg else 0
    props["sici_capacidade_mbps"] = agg.get("capacidade_mbps", 0.0) if agg else 0.0
    props["sici_tecnologia"] = agg.get("tecnologia_predominante", "") if agg else ""


# Campos do agregado do SICI que o SCM usa (o fragmento guarda só isto, não o detalhe municipal)
CAMPOS_SICI_SCM = ("acessos", "pf", "pj", "municipios", "capacidade_mbps", "tecnologia_predominante", "empresa")


def caminho_fragmento_sici(base: Path, date_str: str) -> Path:
    return build_path(base, date_str, "fragments", "scm", "sici.json.gz")


def gravar_fragmento_sici(base: Path, date_str: str, cnpjs: dict, mes_ref: str) -> int:
    """Fragmento do SICI para o SCM (ARANDU_COMPOSE=on): {mes_referencia, cnpjs:{cnpj: escalares}}. Devolve nº de CNPJs."""
    import json as _json
    destino = caminho_fragmento_sici(base, date_str)
    destino.parent.mkdir(parents=True, exist_ok=True)
    corpo = {"mes_referencia": mes_ref,
             "cnpjs": {c: {k: a[k] for k in CAMPOS_SICI_SCM if k in a} for c, a in sorted(cnpjs.items())}}
    tmp = destino.with_name(destino.name + ".tmp")
    with tmp.open("wb") as bruto, gzip.GzipFile(filename="", mode="wb", fileobj=bruto, compresslevel=6, mtime=0) as f:
        f.write(_json.dumps(corpo, ensure_ascii=False).encode("utf-8"))
    tmp.replace(destino)
    return len(corpo["cnpjs"])


def _ler_fragmento_sici(base: Path, date_str: str) -> Optional[dict]:
    return _load_json_gz(caminho_fragmento_sici(base, date_str))


def publicar_outorgas(servico: Servico, base: Path, date_str: str, log) -> dict:
    """
    Publica as outorgas de um serviço (SCM, SMP, STFC ou SeAC) com cruzamento CNPJ↔ASN e mapa GeoJSON.

    Lê anatel_<sigla>_geo.json.gz (`scm_geo`…) e geo_orgs.json.gz (enrich/cnpj_geo).
    Saídas:
      published/{date}/<sigla>.json.gz         — índice completo das outorgas
      published/{date}/maps/<sigla>s.geojson   — pontos para o mapa
    A geo do AS substitui a da outorga quando tem maior confiança, para haver uma coordenada única entre os layers de sede-de-AS
    e de outorga. Os quatro serviços usam a mesma lógica.
    """
    sigla, chave = servico.sigla, servico.chave
    norm_dir = normalized_path(base, date_str, "summary")
    geo_path = norm_dir / f"anatel_{sigla}_geo.json.gz"
    if not geo_path.exists():
        log.info(f"anatel_{sigla}_geo not found, skipping {sigla.upper()} build")
        return {}

    dados = _load_json_gz(geo_path)
    if not dados:
        return {}

    # Constrói CNPJ (14 dígitos) → [asn, ...] e CNPJ → melhor geo do AS (geo_orgs.json.gz).
    # A geo do AS é usada para substituir a geo da outorga quando o AS tem maior confiança,
    # garantindo coordenada única entre os dois layers do mapa.
    _CONF_RANK = {"exact_address": 4, "cep_centroid": 3, "cnpj_cache": 3,
                      "city_centroid": 2, "org_coords": 2}
    cnpj_to_asns: dict[str, list[int]] = {}
    cnpj_to_asn_geo: dict[str, dict] = {}  # CNPJ → {lat, lon, geo_confidence}
    geo_orgs_path = norm_dir / "geo_orgs.json.gz"
    if geo_orgs_path.exists():
        geo_orgs = _load_json_gz(geo_orgs_path)
        if geo_orgs:
            for asn_str, org in geo_orgs.get("orgs", {}).items():
                raw_cnpj = org.get("cnpj") or ""
                cnpj = re.sub(r"\D", "", raw_cnpj)
                if len(cnpj) == 14:
                    cnpj_to_asns.setdefault(cnpj, []).append(int(asn_str))
                    if org.get("lat") is not None:
                        conf = _CONF_RANK.get(org.get("geo_confidence", ""), 1)
                        existing = cnpj_to_asn_geo.get(cnpj)
                        if existing is None or conf > _CONF_RANK.get(
                                existing.get("geo_confidence", ""), 1):
                            cnpj_to_asn_geo[cnpj] = {
                                "lat": org["lat"], "lon": org["lon"],
                                "geo_confidence": org.get("geo_confidence", ""),
                            }
    log.info(f"cnpj_to_asns built ({sigla})", unique_cnpjs=len(cnpj_to_asns))

    records = dados.get(chave, [])
    matched = 0
    for rec in records:
        asns = cnpj_to_asns.get(rec.get("cnpj", ""), [])
        rec["asns"] = asns
        if asns:
            matched += 1

    # SCM com ARANDU_COMPOSE=on: o SICI vem do fragmento e entra aqui, antes da única escrita (antes era uma segunda escrita)
    frag_sici = _ler_fragmento_sici(base, date_str) if sigla == "scm" and compose.ativo() else None
    if frag_sici is not None:
        sici_cnpjs, mes_ref_sici = frag_sici.get("cnpjs", {}), frag_sici.get("mes_referencia", "")
        for rec in records:
            aplicar_sici_registro(rec, sici_cnpjs.get(rec.get("cnpj", "")), mes_ref_sici)

    # Reconstrói by_cnpj com cross-ref de ASN
    by_cnpj: dict[str, list[dict]] = {}
    for rec in records:
        cnpj = rec.get("cnpj", "")
        if cnpj:
            by_cnpj.setdefault(cnpj, []).append(rec)

    output = {
        "snapshot_date":  date_str,
        "generated_at":   now_iso(),
        "total":          len(records),
        "unique_cnpjs":   len(by_cnpj),
        "matched_asns":   matched,
        chave:            records,
        "by_cnpj":        by_cnpj,
        "cnpj_to_asns":   cnpj_to_asns,
    }

    pub_dir = published_path(base, date_str)
    pub_dir.mkdir(parents=True, exist_ok=True)

    pub_path = pub_dir / f"{sigla}.json.gz"
    with gzip.open(pub_path, "wt", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)
    log.info(f"{sigla}.json.gz written",
             path=str(pub_path), total=len(records), matched_asns=matched)

    # Mapa GeoJSON — usa coordenadas do AS quando este tem maior confiança que a outorga,
    # garantindo coordenada única entre os layers de sede-de-AS e outorga.
    features = []
    asn_override = 0
    for rec in records:
        lat = rec.get("lat")
        lon = rec.get("lon")
        if lat is None or lon is None:
            continue
        cnpj = rec.get("cnpj", "")
        asns = rec.get("asns", [])
        geo_confidence = rec.get("geo_confidence", "")
        asn_geo = cnpj_to_asn_geo.get(cnpj) if asns else None
        if asn_geo and (_CONF_RANK.get(asn_geo["geo_confidence"], 1)
                        > _CONF_RANK.get(geo_confidence, 1)):
            lat, lon = asn_geo["lat"], asn_geo["lon"]
            geo_confidence = asn_geo["geo_confidence"]
            asn_override += 1
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "cnpj":         cnpj,
                "razao_social": rec.get("razao_social", ""),
                "nome_fantasia": rec.get("nome_fantasia", ""),
                "municipio":    rec.get("municipio", ""),
                "uf":           rec.get("uf", ""),
                "situacao":     rec.get("situacao", ""),
                "asns":         asns,
                "has_asn":      len(asns) > 0,
                "geo_confidence": geo_confidence,
            },
        })
    log.info(f"{chave}.geojson: asn coordinate override", asn_override=asn_override)

    # Deduplica por (CNPJ, coordenada): a base Anatel pode conter registros idênticos
    # para o mesmo CNPJ + endereço. Mantém apenas o primeiro de cada par.
    seen_cnpj_coord: set[tuple] = set()
    unique_features = []
    for feat in features:
        key = (feat["properties"]["cnpj"],
               tuple(feat["geometry"]["coordinates"]))
        if key not in seen_cnpj_coord:
            seen_cnpj_coord.add(key)
            unique_features.append(feat)
    dupes = len(features) - len(unique_features)
    if dupes:
        log.info(f"{chave}.geojson: duplicates removed", removed=dupes)
    features = unique_features

    if frag_sici is not None:
        for feat in features:
            aplicar_sici_feature(feat["properties"], sici_cnpjs.get(feat["properties"].get("cnpj", "")), mes_ref_sici)

    if features:
        maps_dir = pub_dir / "maps"
        maps_dir.mkdir(parents=True, exist_ok=True)
        geojson = {
            "type": "FeatureCollection",
            "snapshot_date": date_str,
            "features": features,
        }
        (maps_dir / f"{chave}.geojson").write_text(
            json.dumps(geojson, ensure_ascii=False), encoding="utf-8"
        )
        log.info(f"{chave}.geojson written", features=len(features))

    return {
        f"{sigla}_total":        len(records),
        f"{sigla}_matched_asns": matched,
        f"{sigla}_geo_features": len(features),
    }
