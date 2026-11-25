# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Leitura de registros de geolocalização por IP.

A base é o DB-IP City Lite (CC BY 4.0). Diferenças que importam em relação ao GeoLite2 que ela substitui:
- a subdivisão vem só com o nome do estado (sem `iso_code`), que `UF_POR_NOME` traduz;
- a "cidade" muitas vezes é bairro ou distrito (ex.: Pinheiros); `municipio()` a transforma em município pelo nome
  (na UF) e, se não casar, pelo centroide municipal mais próximo (tabelas do IBGE em `config/`).

Registros no formato do GeoLite2 (com `iso_code`) continuam lidos, para os testes e para os snapshots antigos.
"""
from __future__ import annotations

import difflib
import json
import math
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Optional

from core.geo import haversine_km

_CONFIG = Path(__file__).resolve().parent.parent / "config"

# O centroide mais próximo só vale se estiver a até esse nº de raios equivalentes do município (raio = √(área/π)); além
# disso mantém a cidade da base. Medir em raios evita escolher o vizinho pequeno para um bairro de uma capital.
RAIOS_MAX = 2.0
RAIO_PADRAO_KM = 10.0     # municípios sem área na tabela
# Semelhança mínima para aceitar um nome com erro de grafia da base ("Culaba" → Cuiabá) como o município da UF.
LIMIAR_NOME = 0.8

UF_POR_NOME = {
    "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM", "Bahia": "BA", "Ceará": "CE",
    "Federal District": "DF", "Distrito Federal": "DF", "Espírito Santo": "ES", "Goiás": "GO", "Maranhão": "MA",
    "Mato Grosso": "MT", "Mato Grosso do Sul": "MS", "Minas Gerais": "MG", "Pará": "PA", "Paraíba": "PB",
    "Paraná": "PR", "Pernambuco": "PE", "Piauí": "PI", "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN",
    "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR", "Santa Catarina": "SC", "São Paulo": "SP",
    "Sergipe": "SE", "Tocantins": "TO",
}


def normaliza(s: str) -> str:
    """Sem diacríticos, maiúsculas e sem pontuação: chave de comparação de nomes de município."""
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().upper()
    return " ".join("".join(c if c.isalnum() else " " for c in s).split())


@lru_cache(maxsize=1)
def _tabelas() -> tuple[dict, dict, dict]:
    """(nomes por (UF, nome normalizado) → nome oficial, centroides por UF → [(nome, lat, lon, raio_km)], centro por (UF, nome))."""
    try:
        ref = json.loads((_CONFIG / "municipios-referencia.json").read_text(encoding="utf-8"))
        cen = json.loads((_CONFIG / "municipios-centroides.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}, {}, {}
    nomes: dict[tuple[str, str], str] = {}
    por_uf: dict[str, list[tuple[str, float, float, float]]] = {}
    centros: dict[tuple[str, str], tuple[float, float]] = {}
    for codigo, (nome, uf, area) in ref.items():
        nomes[(uf, normaliza(nome))] = nome
        if codigo in cen:
            lon, lat = cen[codigo]
            raio = math.sqrt(area / math.pi) if area else RAIO_PADRAO_KM
            por_uf.setdefault(uf, []).append((nome, lat, lon, raio))
            centros[(uf, nome)] = (lat, lon)
    return nomes, por_uf, centros


def uf_do_registro(record: dict) -> str:
    """UF (sigla) do registro: `iso_code` "BR-SP" (GeoLite) ou o nome do estado (DB-IP). Vazio fora do Brasil."""
    pais = (record.get("country") or record.get("registered_country") or {}).get("iso_code", "")
    sub = (record.get("subdivisions") or [{}])[0]
    iso = sub.get("iso_code", "")
    if iso:
        return iso.removeprefix("BR-")
    if pais != "BR":
        return ""
    return UF_POR_NOME.get((sub.get("names") or {}).get("en", ""), "")


def centroide_municipio(nome: str, uf: Optional[str] = None) -> Optional[tuple[float, float, str, str]]:
    """(lat, lon, nome oficial, UF) do centroide IBGE do município de nome `nome`; sem `uf`, só quando o nome é de um município só.
    None se o nome não está na tabela (ou é ambíguo sem UF)."""
    nomes, _, centros = _tabelas()
    chave = normaliza((nome or "").split("(")[0])
    ufs = [uf.upper()] if uf else sorted({u for (u, k) in nomes if k == chave})
    achados = [(u, nomes[(u, chave)]) for u in ufs if (u, chave) in nomes and (u, nomes[(u, chave)]) in centros]
    if len(achados) != 1:
        return None
    u, oficial = achados[0]
    lat, lon = centros[(u, oficial)]
    return lat, lon, oficial, u


def _perto(chave: str, uf: str, lat: float, lon: float) -> bool:
    """O município de nome `chave` está a até 3 raios do ponto? (descarta nomes parecidos mas distantes)"""
    nomes, por_uf, _ = _tabelas()
    alvo = nomes.get((uf, chave))
    for nome, mlat, mlon, raio in por_uf.get(uf, ()):
        if nome == alvo:
            return haversine_km(lat, lon, mlat, mlon) / raio <= 3.0
    return True            # sem centroide (município novo): fica só o critério do nome


@lru_cache(maxsize=200_000)
def municipio(cidade: str, uf: str, lat: float, lon: float) -> str:
    """Nome do município para a cidade/bairro da base. Sem UF ou sem tabela, devolve a cidade como veio."""
    if not uf:
        return cidade
    nomes, por_uf, _ = _tabelas()
    chave = normaliza(cidade.split("(")[0])
    achado = nomes.get((uf, chave))
    if achado:
        return achado
    if len(chave) >= 5:
        proximos = difflib.get_close_matches(chave, [k[1] for k in nomes if k[0] == uf], n=2, cutoff=LIMIAR_NOME)
        if len(proximos) == 1 and _perto(proximos[0], uf, lat, lon):
            return nomes[(uf, proximos[0])]
    melhor, d_melhor = None, RAIOS_MAX
    for nome, mlat, mlon, raio in por_uf.get(uf, ()):
        d = haversine_km(lat, lon, mlat, mlon) / raio
        if d < d_melhor:
            melhor, d_melhor = nome, d
    return melhor or cidade


def extrair_geo(record: Optional[dict]) -> Optional[dict]:
    """{lat, lon, city, country, uf} de um registro da base; None se sem coordenadas. `city` já é o município."""
    if not record:
        return None
    loc = record.get("location") or {}
    lat, lon = loc.get("latitude"), loc.get("longitude")
    if lat is None or lon is None:
        return None
    nomes = (record.get("city") or {}).get("names") or {}
    cidade = nomes.get("pt-BR") or nomes.get("en") or ""
    pais = (record.get("country") or record.get("registered_country") or {}).get("iso_code", "")
    uf = uf_do_registro(record)
    if pais == "BR":
        cidade = municipio(cidade, uf, round(float(lat), 3), round(float(lon), 3))
    return {"lat": lat, "lon": lon, "city": cidade, "country": pais, "uf": uf}


# Posição individual de um prefixo ou IP: usada por dentro (potencial de PTT, `near`, camadas agregadas), nunca devolvida.
CAMPOS_POSICAO = ("lat", "lon", "latitude", "longitude", "city")


def sem_posicao(d: dict) -> dict:
    """Cópia de `d` sem as chaves de posição individual (`lat`, `lon`, `city`…); o resto fica como está."""
    return {k: v for k, v in d.items() if k not in CAMPOS_POSICAO}


def agrega_prefixos(features: list[dict]) -> list[dict]:
    """Camada de prefixos sem identificar nenhum: uma feição por (ASN, versão IP, município) com `prefix_count`.

    O ponto é o centroide do município (a posição do prefixo não é preservada); sem o município na tabela, a do primeiro
    prefixo do grupo, arredondada a ~1 km. Nenhuma feição carrega o prefixo."""
    centros = _tabelas()[2]
    grupos: dict[tuple, dict] = {}
    for f in features:
        p = f.get("properties") or {}
        coords = (f.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2:
            continue
        chave = (p.get("origin_asn"), p.get("ip_version"), p.get("city") or "", p.get("uf") or "", p.get("country") or "")
        g = grupos.get(chave)
        if g is None:
            lat, lon = centros.get((chave[3], chave[2])) or (round(coords[1], 2), round(coords[0], 2))
            grupos[chave] = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(lon, 4), round(lat, 4)]},
                             "properties": {"origin_asn": chave[0], "ip_version": chave[1], "city": chave[2], "uf": chave[3],
                                            "country": chave[4], "prefix_count": 1,
                                            "geo_confidence": p.get("geo_confidence"), "geo_source": p.get("geo_source")}}
        else:
            g["properties"]["prefix_count"] += 1
    return list(grupos.values())
