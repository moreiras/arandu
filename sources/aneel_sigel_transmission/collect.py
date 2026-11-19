# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`aneel_sigel_transmission` — Coleta de linhas de transmissão de alta tensão do SIGEL/ANEEL.

Fonte: SIGEL (Sistema de Informações Georreferenciadas do Setor Elétrico),
camada "ONS" (id 1, dentro do grupo "Linha de Transmissão") do MapServer
PORTAL/Transmissão, servido por ArcGIS Server, sem autenticação. Rede básica
nacional operada pelo ONS — não cobre subtransmissão/distribuição.

Relevância para o Arandurape: linhas de alta tensão frequentemente carregam
cabos OPGW (fibra óptica no cabo para-raios), usados por transmissoras e por
terceiros para telecom de longa distância. O SIGEL não informa quais linhas
de fato têm OPGW — isso é informação comercial/operacional das transmissoras,
não um dado aberto estruturado. Este
coletor publica só a geometria e os atributos disponíveis (tensão, extensão),
sem afirmar presença de OPGW.

Fonte:       https://sigel.aneel.gov.br/arcgis/rest/services/PORTAL/Transmiss%C3%A3o/MapServer/1
Normalizado: data/normalized/{date}/summary/aneel_transmission.json.gz

Uso:
    python -m sources.aneel_sigel_transmission.collect
    python -m sources.aneel_sigel_transmission.collect --date 2026-09-26

Pegadinhas confirmadas em levantamento manual:
  - A camada não tem campos estruturados de tensão/extensão/proprietário/
    situação. `Name` é texto livre (ex.: "Linha LT 230 kV SCHARLAU 2 /
    CHARQUEADAS C 1 RS") e `PopupInfo` é HTML (ex.: "<b>Tensão: </b>230
    Kv<br/><b>Extensão: </b>72,96 Km") — os campos derivados abaixo vêm de
    regex sobre esses dois campos, best-effort; falha de parsing numa feição
    não derruba a coleta, só deixa os campos derivados nulos.
  - `maxRecordCount` do serviço é 1000 (1.817 feições hoje, 2 páginas) —
    pagina-se por `resultOffset`/`resultRecordCount`, não por `startIndex`
    como no WFS da ITU.
  - `f=geojson` responde 200, mas por segurança este coletor usa `f=json`
    (Esri JSON) e converte `paths` → LineString/MultiLineString manualmente,
    para não depender do conversor geojson do serviço.
  - **Bug de dados confirmado no próprio `paths` do serviço** (presente em
    ambos os formatos, não é um artefato de conversão): a maioria das feições
    vem com a lista de vértices duplicada em ciclo exato N vezes (ex.: uma
    linha com 7 vértices reais aparece com 49, sendo os mesmos 7 repetidos 7
    vezes). Confirmado em 1.323 das 1.817 feições no levantamento de
    2026-09-26, com N variando por feição (não é um valor fixo). Este coletor
    detecta o período mínimo de repetição e colapsa para os vértices reais
    (`_dedupe_repeated_cycle`) — sem isso, o geojson publicado teria
    segmentos "riscando" o mapa (o traçado real seguido de segmentos
    redundantes de volta e repetição).
"""

from __future__ import annotations

import argparse
import re
import sys

import httpx

from core.common import (
    configure_logging,
    data_dir,
    normalized_path,
    now_iso,
    today_str,
    write_json_gz,
)
from core.site import USER_AGENT

QUERY_URL = (
    "https://sigel.aneel.gov.br/arcgis/rest/services/"
    "PORTAL/Transmiss%C3%A3o/MapServer/1/query"
)
PAGE_SIZE = 1000
SOURCE = "SIGEL/ANEEL — PORTAL/Transmissão MapServer, camada ONS (rede básica)"

_TENSAO_RE = re.compile(r"Tens[aã]o:\s*</b>\s*([\d.,]+)\s*[Kk][Vv]")
_EXTENSAO_RE = re.compile(r"Extens[aã]o:\s*</b>\s*([\d.,]+)\s*[Kk][Mm]")
_NAME_RE = re.compile(
    # Achados em dados reais que o padrão abaixo precisa tolerar:
    #   - tensão nem sempre numérica limpa: "34P5 kV" (34,5 kV com "P" no lugar da
    #     vírgula) — por isso \S+ no lugar de [\d.,]+ para esse token (a tensão de
    #     verdade vem de PopupInfo via _parse_popup, este token aqui só é descartado);
    #   - circuito após "C" nem sempre numérico: "C 1", "C `bgp_ixp`", "C F3", "C L2";
    #   - UF pode ser dupla em linhas interestaduais/internacionais: "RS/UY", "PI/CE".
    r"^Linha\s+LT\s+\S+\s*kV\s+(?P<se1>.+?)\s*/\s*(?P<se2>.+?)\s+C\s*\S+\s+(?P<uf>[A-Z]{2}(?:/[A-Z]{2})?)\s*$",
    re.IGNORECASE,
)


def _make_client() -> httpx.Client:
    headers = {"User-Agent": USER_AGENT}
    return httpx.Client(headers=headers, timeout=60, follow_redirects=True)


def _parse_float_br(raw: str) -> float | None:
    try:
        return float(raw.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _parse_popup(popup: str | None) -> dict:
    popup = popup or ""
    tensao_m = _TENSAO_RE.search(popup)
    extensao_m = _EXTENSAO_RE.search(popup)
    return {
        "tensao_kv": _parse_float_br(tensao_m.group(1)) if tensao_m else None,
        "extensao_km": _parse_float_br(extensao_m.group(1)) if extensao_m else None,
    }


def _parse_name(name: str | None) -> dict:
    m = _NAME_RE.match(name or "")
    if not m:
        return {"subestacao_origem": None, "subestacao_destino": None, "uf": None}
    return {
        "subestacao_origem": m.group("se1").strip(),
        "subestacao_destino": m.group("se2").strip(),
        "uf": m.group("uf").upper(),
    }


def _dedupe_repeated_cycle(coords: list) -> list:
    """Colapsa uma lista de vértices que se repete em ciclo exato ao seu período mínimo.

    Ver nota no docstring do módulo: o `paths` do SIGEL frequentemente traz os
    vértices reais repetidos N vezes em sequência. Procura o menor período `p`
    (divisor do total de pontos, p >= 2) tal que os pontos sejam `p` vértices
    reais repetidos; se nenhum for encontrado, devolve a lista original
    (path legítimo, sem duplicação).
    """
    n = len(coords)
    if n <= 2:
        return coords
    for p in range(2, n):
        if n % p != 0:
            continue
        unit = coords[:p]
        if all(coords[i * p:(i + 1) * p] == unit for i in range(1, n // p)):
            return unit
    return coords


def _esri_paths_to_geometry(geometry: dict) -> dict | None:
    """Converte geometria Esri JSON (`paths`) para GeoJSON LineString/MultiLineString,
    removendo a duplicação cíclica de vértices de cada parte (ver `_dedupe_repeated_cycle`)."""
    paths = geometry.get("paths")
    if not paths:
        return None
    cleaned = [_dedupe_repeated_cycle(p) for p in paths]
    if len(cleaned) == 1:
        return {"type": "LineString", "coordinates": cleaned[0]}
    return {"type": "MultiLineString", "coordinates": cleaned}


def _fetch_page(client: httpx.Client, offset: int, log) -> list[dict]:
    """Busca uma página em Esri JSON (`f=json`) — ver nota sobre o bug do `f=geojson`."""
    params = {
        "where": "1=1",
        "outFields": "*",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
        "returnGeometry": "true",
        "f": "json",
    }
    resp = client.get(QUERY_URL, params=params)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"SIGEL query error at offset {offset}: {data['error']}")

    features = data.get("features", [])
    log.info("page fetched", offset=offset, returned=len(features))
    return features


def _fetch_all(client: httpx.Client, log) -> list[dict]:
    """Varre a camada inteira paginando por resultOffset/resultRecordCount."""
    features: list[dict] = []
    offset = 0
    while True:
        page = _fetch_page(client, offset, log)
        if not page:
            break
        features.extend(page)
        offset += PAGE_SIZE
        if len(page) < PAGE_SIZE:
            break
    return features


def _normalize_feature(f: dict) -> dict | None:
    geometry = _esri_paths_to_geometry(f.get("geometry") or {})
    props = f.get("attributes") or {}

    if not geometry:
        return None

    name = props.get("Name")
    derived = {**_parse_name(name), **_parse_popup(props.get("PopupInfo"))}

    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "name": name or "",
            **derived,
        },
    }


def run(date_str: str, base, log) -> dict:
    """Coleta a camada ONS de linhas de transmissão inteira (rede básica nacional).

    Returns:
        O dict normalizado gravado em disco: features GeoJSON (geometria +
        atributos derivados de Name/PopupInfo) e total.
    """
    norm_dir = normalized_path(base, date_str, "summary")
    norm_dir.mkdir(parents=True, exist_ok=True)

    with _make_client() as client:
        raw_features = _fetch_all(client, log)

    features = []
    for f in raw_features:
        norm = _normalize_feature(f)
        if norm is not None:
            features.append(norm)

    normalized = {
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "source": SOURCE,
        "total": len(features),
        "features": features,
    }
    norm_file = norm_dir / "aneel_transmission.json.gz"
    write_json_gz(norm_file, normalized)

    log.info("aneel_sigel_transmission done", total=len(features))
    return normalized


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="`aneel_sigel_transmission` — coleta de linhas de transmissão de alta tensão do SIGEL/ANEEL"
    )
    parser.add_argument("--date", default=today_str(),
                        help="Data do snapshot (YYYY-MM-DD); padrão: hoje")
    args = parser.parse_args(argv)

    log = configure_logging()
    base = data_dir()

    try:
        run(date_str=args.date, base=base, log=log)
    except httpx.HTTPStatusError as exc:
        log.error("http error", status=exc.response.status_code, url=str(exc.request.url))
        return 1
    except httpx.RequestError as exc:
        log.error("connection error", error=str(exc))
        return 1
    except Exception:
        log.exception("unexpected error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
