# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`cnpj_geo` — Geolocalização de organizações via CNPJ

Fonte: BrasilAPI (CNPJ → dados cadastrais + endereço) + Nominatim OSM (endereço → lat/lon)
Cache: data/normalized/geo_cache/cnpj.json.gz  (persiste entre snapshots)

Entradas coletadas da BrasilAPI além do endereço:
  identificação : razao_social, nome_fantasia, identificador_matriz_filial,
                  descricao_identificador_matriz_filial
  atividade     : cnae_fiscal, cnae_fiscal_descricao, cnaes_secundarios
  situação      : situacao_cadastral, descricao_situacao_cadastral,
                  motivo_situacao_cadastral, descricao_motivo_situacao_cadastral
  natureza/porte: natureza_juridica, codigo_natureza_juridica, porte, codigo_porte
  outros        : data_inicio_atividade, email, ddd_telefone_1, ddd_telefone_2

Entrada:  normalized/{date}/summary/orgs.json.gz
Saída:    normalized/{date}/summary/geo_orgs.json.gz

Estratégias de geocodificação (ordem decrescente de confiança):
  1. logradouro + número + município + UF  →  geo_confidence: exact_address
  2. CEP                                   →  geo_confidence: cep_centroid
  3. município + UF                        →  geo_confidence: city_centroid
  4. sem resultado                         →  geo_confidence: unknown

User-Agent para Nominatim: variável NOMINATIM_USER_AGENT ou padrão do projeto.
Taxa: 1 req/s (política do Nominatim).

Uso:
    python -m sources.cnpj_geo.enrich --date 2026-06-12
    python -m sources.cnpj_geo.enrich --date 2026-06-12 --force   # ignora cache
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import httpx

from core.common import (
    configure_logging,
    data_dir,
    normalized_path,
    now_iso,
    read_json_gz,
    today_str,
    write_json_gz,
)
from core.site import USER_AGENT

BRASILAPI_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_DELAY = 1.1  # segundos entre requisições (política: máx 1 req/s)

# Incrementar quando os campos coletados mudarem — invalida entradas antigas do cache.
CACHE_VERSION = "2"


def _user_agent() -> str:
    return os.environ.get("NOMINATIM_USER_AGENT") or USER_AGENT


def _fetch_brasilapi(cnpj: str, client: httpx.Client) -> dict | None:
    try:
        r = client.get(BRASILAPI_URL.format(cnpj=cnpj), timeout=15)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        d = r.json()
        # Resposta de erro da API (CNPJ inválido etc.)
        if "message" in d and "cnpj" not in d:
            return None
        return d
    except Exception:
        return None


def _nominatim(params: dict, client: httpx.Client) -> dict | None:
    """Executa uma busca no Nominatim. Retorna o primeiro resultado ou None."""
    try:
        r = client.get(
            NOMINATIM_URL,
            params={**params, "format": "jsonv2", "limit": 1, "countrycodes": "br"},
            timeout=15,
        )
        r.raise_for_status()
        results = r.json()
        return results[0] if results else None
    except Exception:
        return None


def _extract_fields(bapi: dict) -> dict:
    """Extrai todos os campos de interesse da resposta da BrasilAPI."""
    cep = "".join(c for c in (bapi.get("cep") or "") if c.isdigit())
    return {
        # Endereço completo
        "logradouro":                    bapi.get("logradouro") or "",
        "descricao_tipo_de_logradouro":  bapi.get("descricao_tipo_de_logradouro") or "",
        "numero":                        bapi.get("numero") or "",
        "complemento":                   bapi.get("complemento") or "",
        "bairro":                        bapi.get("bairro") or "",
        "municipio":                     bapi.get("municipio") or "",
        "uf":                            bapi.get("uf") or "",
        "cep":                           cep,
        "codigo_municipio":              bapi.get("codigo_municipio"),
        "codigo_municipio_ibge":         bapi.get("codigo_municipio_ibge"),
        # Identificação
        "razao_social":                           bapi.get("razao_social") or "",
        "nome_fantasia":                          bapi.get("nome_fantasia") or "",
        "identificador_matriz_filial":            bapi.get("identificador_matriz_filial"),
        "descricao_identificador_matriz_filial":  bapi.get("descricao_identificador_matriz_filial") or "",
        # Atividade econômica
        "cnae_fiscal":              bapi.get("cnae_fiscal"),
        "cnae_fiscal_descricao":    bapi.get("cnae_fiscal_descricao") or "",
        "cnaes_secundarios":        bapi.get("cnaes_secundarios") or [],
        # Situação cadastral
        "situacao_cadastral":                    bapi.get("situacao_cadastral"),
        "descricao_situacao_cadastral":          bapi.get("descricao_situacao_cadastral") or "",
        "motivo_situacao_cadastral":             bapi.get("motivo_situacao_cadastral"),
        "descricao_motivo_situacao_cadastral":   bapi.get("descricao_motivo_situacao_cadastral") or "",
        # Natureza jurídica e porte
        "natureza_juridica":         bapi.get("natureza_juridica") or "",
        "codigo_natureza_juridica":  bapi.get("codigo_natureza_juridica"),
        "porte":                     bapi.get("porte") or "",
        "codigo_porte":              bapi.get("codigo_porte"),
        # Outros
        "data_inicio_atividade": bapi.get("data_inicio_atividade") or "",
        "email":        bapi.get("email") or "",
        "ddd_telefone_1": bapi.get("ddd_telefone_1") or "",
        "ddd_telefone_2": bapi.get("ddd_telefone_2") or "",
    }


def _geolocate(cnpj: str, bc: httpx.Client, nc: httpx.Client) -> dict:
    """
    Consulta BrasilAPI, extrai todos os campos de interesse e geocodifica
    o endereço via Nominatim em três estratégias de confiança decrescente.
    """
    bapi = _fetch_brasilapi(cnpj, bc)
    if not bapi:
        return {
            "lat": None, "lon": None,
            "geo_confidence": "unknown", "geo_source": None,
            "error": "brasilapi_not_found",
        }

    fields = _extract_fields(bapi)
    municipio = fields["municipio"]
    uf = fields["uf"]
    logradouro = fields["logradouro"]
    numero = fields["numero"]
    cep = fields["cep"]

    # Estratégia 1 — endereço completo
    if logradouro and municipio:
        street = f"{logradouro} {numero}".strip()
        time.sleep(NOMINATIM_DELAY)
        result = _nominatim(
            {"street": street, "city": municipio, "state": uf, "country": "Brazil"},
            nc,
        )
        if result:
            return {**fields,
                    "lat": float(result["lat"]), "lon": float(result["lon"]),
                    "city": municipio, "geo_confidence": "exact_address",
                    "geo_source": "nominatim"}

    # Estratégia 2 — CEP
    if cep:
        time.sleep(NOMINATIM_DELAY)
        result = _nominatim({"postalcode": cep, "country": "Brazil"}, nc)
        if result:
            return {**fields,
                    "lat": float(result["lat"]), "lon": float(result["lon"]),
                    "city": municipio, "geo_confidence": "cep_centroid",
                    "geo_source": "nominatim"}

    # Estratégia 3 — município + UF
    if municipio and uf:
        time.sleep(NOMINATIM_DELAY)
        result = _nominatim({"city": municipio, "state": uf, "country": "Brazil"}, nc)
        if result:
            return {**fields,
                    "lat": float(result["lat"]), "lon": float(result["lon"]),
                    "city": municipio, "geo_confidence": "city_centroid",
                    "geo_source": "nominatim"}

    return {**fields, "lat": None, "lon": None,
            "geo_confidence": "unknown", "geo_source": None}


def _cache_path(base: Path) -> Path:
    return base / "normalized" / "geo_cache" / "cnpj.json.gz"


def _load_cache(base: Path) -> dict:
    p = _cache_path(base)
    return read_json_gz(p) if p.exists() else {}


def _save_cache(base: Path, cache: dict) -> None:
    write_json_gz(_cache_path(base), cache)


def _cache_valid(entry: dict) -> bool:
    """Retorna True se a entrada do cache é compatível com a versão atual."""
    return entry.get("cache_version") == CACHE_VERSION


def run(date_str: str, base: Path, force: bool, log) -> dict:
    src = normalized_path(base, date_str, "summary", "orgs.json.gz")
    dst = normalized_path(base, date_str, "summary", "geo_orgs.json.gz")

    if not src.exists():
        raise FileNotFoundError(f"orgs.json.gz não encontrado: {src}. Rode a etapa rdap primeiro.")

    orgs = read_json_gz(src).get("orgs", {})
    cache = {} if force else _load_cache(base)

    ua = _user_agent()
    brasilapi_client = httpx.Client(headers={"User-Agent": ua}, follow_redirects=True)
    nominatim_client = httpx.Client(headers={"User-Agent": ua}, follow_redirects=True)

    results: dict[str, dict] = {}
    cached_count = geolocated = unknown = 0
    total = len(orgs)

    with brasilapi_client, nominatim_client:
        for i, (asn, org) in enumerate(orgs.items(), 1):
            cnpj = org.get("cnpj") or ""

            if not cnpj:
                results[asn] = {"lat": None, "lon": None,
                                "geo_confidence": "unknown", "geo_source": None}
                unknown += 1
                continue

            if cnpj in cache and _cache_valid(cache[cnpj]):
                results[asn] = cache[cnpj]
                cached_count += 1
                if cache[cnpj].get("lat") is not None:
                    geolocated += 1
                continue

            geo = _geolocate(cnpj, brasilapi_client, nominatim_client)
            geo["cached_at"] = now_iso()
            geo["cache_version"] = CACHE_VERSION
            cache[cnpj] = geo
            results[asn] = geo

            if geo.get("lat") is not None:
                geolocated += 1
            else:
                unknown += 1

            if i % 100 == 0:
                log.info("progress", done=i, total=total,
                         cached=cached_count, geolocated=geolocated)
                _save_cache(base, cache)  # checkpoint incremental

    _save_cache(base, cache)

    output = {
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "total": total,
        "geolocated": geolocated,
        "cached": cached_count,
        "unknown": unknown,
        "orgs": {
            asn: {
                "name": orgs[asn]["name"],
                "cnpj": orgs[asn].get("cnpj") or "",
                **results.get(asn, {}),
            }
            for asn in orgs
        },
    }

    write_json_gz(dst, output)
    log.info("geo_orgs saved",
             path=str(dst), total=total, geolocated=geolocated, cached=cached_count)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="`cnpj_geo` — geolocalização de ASNs por CNPJ")
    parser.add_argument("--date", default=today_str())
    parser.add_argument("--force", action="store_true",
                        help="Ignora cache, re-consulta tudo")
    args = parser.parse_args(argv)

    log = configure_logging()
    base = data_dir()

    try:
        run(date_str=args.date, base=base, force=args.force, log=log)
    except FileNotFoundError as e:
        log.error("input not found", error=str(e))
        return 1
    except Exception:
        log.exception("unexpected error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
