# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Geolocalização de outorgas da Anatel via Nominatim: uma lógica para SCM, SMP, STFC e SeAC.

Entrada:  normalized/{date}/summary/anatel_<sigla>.json.gz
Saída:    normalized/{date}/summary/anatel_<sigla>_geo.json.gz
Cache:    data/normalized/geo_cache/<sigla>.json.gz  (persiste entre snapshots)

Estratégias de geocodificação (ordem decrescente de confiança):
  1. logradouro + número + município + UF  →  geo_confidence: exact_address
  2. CEP                                   →  geo_confidence: cep_centroid
  3. município + UF                        →  geo_confidence: city_centroid
  4. sem resultado                         →  geo_confidence: unknown

Os quatro `sources/<sigla>_geo/enrich.py` só dizem qual `Servico` usar. `--checkpoint` (publicar o cache atual sem chamar o
Nominatim) vale para os quatro.
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
from sources.anatel_outorgas.servicos import Servico
from core.site import USER_AGENT

_NOMINATIM_PUBLIC = "https://nominatim.openstreetmap.org/search"
# Se NOMINATIM_URL apontar para instância local (ex.: http://localhost:8088/search),
# o delay é zerado automaticamente (sem limite de taxa).
NOMINATIM_URL = os.environ.get("NOMINATIM_URL", _NOMINATIM_PUBLIC)
NOMINATIM_DELAY = 0.0 if NOMINATIM_URL != _NOMINATIM_PUBLIC else 1.1
CACHE_VERSION = "1"


def _user_agent() -> str:
    return os.environ.get("NOMINATIM_USER_AGENT", USER_AGENT)


class _NominatimError(Exception):
    """Erro de rede/rate-limit — não deve ser cacheado como 'não encontrado'."""


def _nominatim(params: dict, client: httpx.Client) -> dict | None:
    """Retorna o primeiro resultado ou None (não encontrado).

    Lança _NominatimError em caso de falha de rede ou HTTP ≥ 400, para que
    o chamador não armazene falhas transitórias no cache como 'unknown'.
    """
    try:
        r = client.get(
            NOMINATIM_URL,
            params={**params, "format": "jsonv2", "limit": 1, "countrycodes": "br"},
            timeout=15,
        )
        r.raise_for_status()
        results = r.json()
        return results[0] if results else None
    except Exception as exc:
        raise _NominatimError(str(exc)) from exc


def _geolocate(rec: dict, client: httpx.Client) -> dict | None:
    """Geocodifica um registro de outorga via Nominatim.

    Retorna None se houver erro de rede/rate-limit (não deve ser cacheado).
    Retorna dict com lat=None se o Nominatim respondeu mas não encontrou.
    """
    logradouro = rec.get("logradouro") or ""
    numero = rec.get("numero") or ""
    municipio = rec.get("municipio") or ""
    uf = rec.get("uf") or ""
    cep = rec.get("cep") or ""

    try:
        # Estratégia 1 — endereço completo
        if logradouro and municipio:
            street = f"{logradouro} {numero}".strip()
            time.sleep(NOMINATIM_DELAY)
            result = _nominatim(
                {"street": street, "city": municipio, "state": uf, "country": "Brazil"},
                client,
            )
            if result:
                return {
                    "lat": float(result["lat"]),
                    "lon": float(result["lon"]),
                    "geo_confidence": "exact_address",
                    "geo_source": "nominatim",
                }

        # Estratégia 2 — CEP
        if cep:
            time.sleep(NOMINATIM_DELAY)
            result = _nominatim({"postalcode": cep, "country": "Brazil"}, client)
            if result:
                return {
                    "lat": float(result["lat"]),
                    "lon": float(result["lon"]),
                    "geo_confidence": "cep_centroid",
                    "geo_source": "nominatim",
                }

        # Estratégia 3 — município + UF
        if municipio and uf:
            time.sleep(NOMINATIM_DELAY)
            result = _nominatim({"city": municipio, "state": uf, "country": "Brazil"}, client)
            if result:
                return {
                    "lat": float(result["lat"]),
                    "lon": float(result["lon"]),
                    "geo_confidence": "city_centroid",
                    "geo_source": "nominatim",
                }

    except _NominatimError:
        return None  # erro de rede — não cachear

    return {"lat": None, "lon": None, "geo_confidence": "unknown", "geo_source": None}


def _cache_path(base: Path, sigla: str) -> Path:
    return base / "normalized" / "geo_cache" / f"{sigla}.json.gz"


def _load_cache(base: Path, sigla: str) -> dict:
    p = _cache_path(base, sigla)
    return read_json_gz(p) if p.exists() else {}


def _save_cache(base: Path, sigla: str, cache: dict) -> None:
    _cache_path(base, sigla).parent.mkdir(parents=True, exist_ok=True)
    write_json_gz(_cache_path(base, sigla), cache)


def _cache_key(rec: dict) -> str:
    """Chave composta: CNPJ + endereço (outorgas distintas do mesmo CNPJ podem ter endereços diferentes)."""
    return f"{rec.get('cnpj', '')}|{rec.get('logradouro', '')}|{rec.get('municipio', '')}|{rec.get('uf', '')}"


def _seed_from_cnpj_cache(records: list[dict], geo_cache_map: dict, base: Path, log) -> int:
    """Pré-popula o cache do serviço a partir do cache do cnpj_geo (sem chamar o Nominatim).

    CNPJs que o enrich/cnpj_geo já geocodificou (ASNs BR, etc.) têm coordenadas
    reutilizáveis — evita milhares de requisições redundantes ao Nominatim público.
    """
    cnpj_cache_path = base / "normalized" / "geo_cache" / "cnpj.json.gz"
    if not cnpj_cache_path.exists():
        return 0
    cnpj_geo: dict = read_json_gz(cnpj_cache_path)
    seeded = 0
    for rec in records:
        key = _cache_key(rec)
        if key in geo_cache_map:
            continue
        entry = cnpj_geo.get(rec.get("cnpj", ""))
        if entry and entry.get("lat") is not None:
            geo_cache_map[key] = {
                "lat": entry["lat"],
                "lon": entry["lon"],
                "geo_confidence": entry.get("geo_confidence", "address"),
                "geo_source": "cnpj_cache",
                "cache_version": CACHE_VERSION,
                "cached_at": now_iso(),
            }
            seeded += 1
    log.info("seeded from cnpj_geo cache", seeded=seeded)
    return seeded


def _flush_output(servico: Servico, date_str: str, base: Path, records: list[dict], cache: dict, log) -> dict:
    """Gera anatel_<sigla>_geo.json.gz a partir do cache atual, sem chamar o Nominatim.

    Registros sem entrada no cache recebem lat=None/lon=None/geo_confidence=unknown.
    Usado por --checkpoint para publicar resultados parciais sem interromper o progresso.
    """
    dst = normalized_path(base, date_str, "summary", f"anatel_{servico.sigla}_geo.json.gz")
    results: list[dict] = []
    geolocated = cached_count = unknown = 0
    for rec in records:
        key = _cache_key(rec)
        if key in cache and cache[key].get("cache_version") == CACHE_VERSION:
            geo = cache[key]
            cached_count += 1
        else:
            geo = {"lat": None, "lon": None, "geo_confidence": "unknown", "geo_source": None}
            unknown += 1
        enriched = {**rec, **{k: v for k, v in geo.items()
                               if k not in ("cache_version", "cached_at")}}
        results.append(enriched)
        if geo.get("lat") is not None:
            geolocated += 1

    by_cnpj: dict[str, list[dict]] = {}
    for rec in results:
        cnpj = rec.get("cnpj", "")
        if cnpj:
            by_cnpj.setdefault(cnpj, []).append(rec)

    output = {
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "total": len(results),
        "geolocated": geolocated,
        "cached": cached_count,
        "unknown": unknown,
        "unique_cnpjs": len(by_cnpj),
        "checkpoint": True,
        servico.chave: results,
        "by_cnpj": by_cnpj,
    }
    write_json_gz(dst, output)
    log.info("checkpoint saved",
             path=str(dst), total=len(results), geolocated=geolocated,
             cached=cached_count, unknown=unknown)
    return output


def rodar(servico: Servico, date_str: str, base: Path, force: bool, log) -> dict:
    sigla = servico.sigla
    src = normalized_path(base, date_str, "summary", f"anatel_{sigla}.json.gz")
    dst = normalized_path(base, date_str, "summary", f"anatel_{sigla}_geo.json.gz")

    if not src.exists():
        raise FileNotFoundError(f"anatel_{sigla}.json.gz não encontrado: {src}. Execute o coletor {sigla} primeiro.")

    data = read_json_gz(src)
    records = data.get(servico.chave, [])
    cache = {} if force else _load_cache(base, sigla)

    # Pré-popula cache a partir do cnpj_geo (sem chamar Nominatim) para CNPJs que já
    # foram geocodificados em outras etapas do pipeline (ASNs BR, etc.).
    if not force:
        seeded = _seed_from_cnpj_cache(records, cache, base, log)
        if seeded:
            _save_cache(base, sigla, cache)

    local_nominatim = NOMINATIM_URL != _NOMINATIM_PUBLIC
    if local_nominatim:
        log.info("using local nominatim", url=NOMINATIM_URL, delay=NOMINATIM_DELAY)

    ua = _user_agent()
    client = httpx.Client(headers={"User-Agent": ua}, follow_redirects=True)

    results: list[dict] = []
    cached_count = geolocated = unknown = 0
    total = len(records)

    with client:
        for i, rec in enumerate(records, 1):
            key = _cache_key(rec)
            if not force and key in cache and cache[key].get("cache_version") == CACHE_VERSION:
                geo = cache[key]
                cached_count += 1
            else:
                geo = _geolocate(rec, client)
                if geo is None:
                    # Erro de rede/rate-limit: não cacheia, usa unknown temporário
                    geo = {"lat": None, "lon": None, "geo_confidence": "unknown", "geo_source": None}
                else:
                    geo["cache_version"] = CACHE_VERSION
                    geo["cached_at"] = now_iso()
                    cache[key] = geo

            enriched = {**rec, **{k: v for k, v in geo.items()
                                  if k not in ("cache_version", "cached_at")}}
            results.append(enriched)

            if geo.get("lat") is not None:
                geolocated += 1
            else:
                unknown += 1

            if i % 200 == 0:
                log.info("progress", done=i, total=total,
                         cached=cached_count, geolocated=geolocated)
                _save_cache(base, sigla, cache)

    _save_cache(base, sigla, cache)

    # Reconstrói by_cnpj com geo
    by_cnpj: dict[str, list[dict]] = {}
    for rec in results:
        cnpj = rec.get("cnpj", "")
        if cnpj:
            if cnpj not in by_cnpj:
                by_cnpj[cnpj] = []
            by_cnpj[cnpj].append(rec)

    output = {
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "total": total,
        "geolocated": geolocated,
        "cached": cached_count,
        "unknown": unknown,
        "unique_cnpjs": len(by_cnpj),
        servico.chave: results,
        "by_cnpj": by_cnpj,
    }

    write_json_gz(dst, output)
    log.info(f"anatel_{sigla}_geo saved",
             path=str(dst), total=total, geolocated=geolocated, unique_cnpjs=len(by_cnpj))
    return output


def main_geo(servico: Servico, etapa: str, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{etapa} — geolocalização de outorgas {servico.sigla.upper()}")
    parser.add_argument("--date", default=today_str())
    parser.add_argument("--force", action="store_true", help="Ignora cache, re-consulta tudo")
    parser.add_argument(
        "--checkpoint",
        action="store_true",
        help=(
            f"Gera anatel_{servico.sigla}_geo.json.gz a partir do cache atual, sem chamar o Nominatim. "
            "Use para publicar resultados parciais enquanto o processo principal está parado."
        ),
    )
    args = parser.parse_args(argv)

    log = configure_logging()
    base = data_dir()

    try:
        if args.checkpoint:
            src = normalized_path(base, args.date, "summary", f"anatel_{servico.sigla}.json.gz")
            if not src.exists():
                log.error("input not found", path=str(src))
                return 1
            data = read_json_gz(src)
            cache = _load_cache(base, servico.sigla)
            log.info("checkpoint mode", cache_entries=len(cache), total_records=data.get("total", 0))
            _flush_output(servico, args.date, base, data.get(servico.chave, []), cache, log)
        else:
            rodar(servico, date_str=args.date, base=base, force=args.force, log=log)
    except FileNotFoundError as e:
        log.error("input not found", error=str(e))
        return 1
    except Exception:
        log.exception("unexpected error")
        return 1

    return 0
