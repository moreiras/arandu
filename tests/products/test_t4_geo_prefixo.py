# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — nenhuma resposta pública traz latitude, longitude ou cidade de um prefixo ou IP.

O Arandurapé não é um serviço de geolocalização: a posição de cada prefixo é usada por dentro (potencial de PTT, filtro
`near`, camadas agregadas), mas não sai. O teste percorre todas as operações da API sobre o dataset sintético e falha se
achar, em qualquer resposta JSON:
- um objeto com `prefix`/`prefixo` e `lat`/`lon`/`city` (linha de lista, perfil, resultado de consulta);
- um dicionário indexado por CIDR cujos valores tenham `lat`/`lon`/`city`;
- uma feature GeoJSON de ponto com `properties.prefix`.
Posição agregada (por município, PTT ou ASN) é outra coisa e continua permitida.
"""
import ipaddress

import pytest

from tests.products.api_contract import ALLOWED
from tests.products.test_t4_api import _call, _operations, ctx  # noqa: F401  (fixture reaproveitada)

CHAVES_GEO = {"lat", "lon", "latitude", "longitude", "city"}


def _eh_cidr(s) -> bool:
    try:
        ipaddress.ip_network(s, strict=False)
        return "/" in s
    except (ValueError, TypeError):
        return False


def _achados(x, caminho="$"):
    if isinstance(x, dict):
        chaves = set(x)
        if (chaves & {"prefix", "prefixo"}) and (chaves & CHAVES_GEO):
            yield f"{caminho}: objeto de prefixo com {sorted(chaves & CHAVES_GEO)}"
        props = x.get("properties")
        geom = x.get("geometry")
        if isinstance(props, dict) and isinstance(geom, dict) and geom.get("type") == "Point" \
                and (set(props) & {"prefix", "prefixo"}):
            yield f"{caminho}: feature de ponto com properties.prefix"
        cidr = [k for k in x if _eh_cidr(k)]
        if cidr and any(isinstance(x[k], dict) and set(x[k]) & CHAVES_GEO for k in cidr):
            yield f"{caminho}: dicionário por CIDR com {sorted(set(x[cidr[0]]) & CHAVES_GEO)}"
        for k, v in x.items():
            yield from _achados(v, f"{caminho}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x[:200]):
            yield from _achados(v, f"{caminho}[{i}]")


def test_nenhuma_resposta_da_api_geolocaliza_prefixo_ou_ip(api, ctx):  # noqa: F811
    vazamentos = []
    for op in _operations(api):
        r = _call(api, op, ctx, ALLOWED)
        if "json" not in r.headers.get("content-type", "") or r.status_code >= 400:
            continue
        for a in list(_achados(r.json()))[:3]:
            vazamentos.append(f"{op} → {a}")
    assert not vazamentos, "geolocalização por prefixo/IP exposta:\n" + "\n".join(vazamentos)


def _post(api, colecao, corpo):
    return api.post(f"/api/v1/query/{colecao}", json=corpo, headers=ALLOWED)


@pytest.mark.parametrize("colecao", ["prefixes", "global_prefixes"])
def test_query_nao_devolve_nem_aceita_posicao_de_prefixo(api, colecao):
    r = _post(api, colecao, {"limit": 5})
    assert r.status_code == 200 and r.json()["items"]
    for item in r.json()["items"]:
        assert not set(item) & {"lat", "lon", "city"}, item
    for corpo in ({"select": ["prefix", "lat"]}, {"sort": [{"field": "lon"}]}, {"group_by": ["city"]},
                  {"filter": {"field": "lat", "op": "gt", "value": -10}}):
        r = _post(api, colecao, corpo)
        assert r.status_code == 400 and "posição de cada prefixo" in r.text, (corpo, r.text[:200])
    esquema = api.get("/api/v1/schema", params={"collection": colecao}, headers=ALLOWED)
    campos = {f["name"] for f in esquema.json()["fields"]}
    assert "prefix" in campos and not campos & {"lat", "lon", "city"}


def test_near_continua_funcionando_sem_devolver_posicao(api):
    r = _post(api, "global_prefixes", {"near": {"point": [40.0, -74.0], "radius_km": 50}, "limit": 3})
    assert r.status_code == 200 and r.json()["total"] > 0
    for item in r.json()["items"]:
        assert not set(item) & {"lat", "lon", "city"}


def test_lookup_por_ip_e_so_consulta_de_roteamento(api):
    pref = api.get("/api/v1/prefixes", params={"limit": 1}, headers=ALLOWED).json()["items"][0]["prefix"]
    ip = str(next(ipaddress.ip_network(pref).hosts()))
    r = api.get("/api/v1/prefixes/lookup", params={"ip": ip}, headers=ALLOWED)
    assert r.status_code == 200
    assert set(r.json()) == {"prefix", "ip_version", "origin_asn", "registro_asn", "observed_origin_asn", "snapshot_date", "consulta"}


def test_mapa_explorer_responde_as_camadas_do_ptt_e_o_near_ix(api):  # noqa: F811
    """As camadas de prefixos do PTT e o `near_ix` chamam o serviço de geolocalização pelo `Store`: sem a delegação davam 500
    (o teste de vazamento abaixo pula o que não é 200 e não via)."""
    corpos = [{"layers": [c], "ix_code": "sp"} for c in ("prefixos_ix_v4", "prefixos_ix_v6")]
    corpos += [{"layers": ["prefixos_ix_v4"], "ix_code": "sp", "ix_exclude_asns": [64500]},
               {"layers": ["asns_geo"], "near_ix": {"code": "sp", "afi": "v4", "exclude_asns": [64500]}}]
    for corpo in corpos:
        r = api.post("/api/v1/map/query", json=corpo, headers=ALLOWED)
        assert r.status_code == 200, (corpo, r.status_code, r.text[:300])


def test_camadas_explicitas_de_asn_ptt_e_mapa_tambem_nao_geolocalizam_prefixo(api, ctx):  # noqa: F811
    """As camadas pedem argumentos que a requisição padrão não usa; o vazamento delas passaria despercebido."""
    pedidos = []
    asn = ctx.get("asn") or 64496
    for camada in ("fulltable_v4", "fulltable_v6", "ixp_v4", "ixp_v6"):
        pedidos.append(("GET", f"/api/v1/asns/{asn}/geo", {"params": {"layer": camada}}))
    for camada in ("prefixes_v4", "prefixes_v6"):
        pedidos.append(("GET", "/api/v1/ixps/sp/geo", {"params": {"layer": camada}}))
    for camada in ("prefixes_v4", "prefixes_v6", "prefixos_ix_v4", "prefixos_ix_v6", "asns_geo"):
        pedidos.append(("POST", "/api/v1/map/query", {"json": {"layers": [camada], "ix_code": "sp",
                                                               "filter": {"field": "is_br", "op": "eq", "value": True}}}))
    pedidos.append(("POST", "/api/v1/map/query", {"json": {"layers": ["prefixes_v4"], "near_prefixes": {"ixp": "sp", "radius_km": 300}}}))
    vazamentos = []
    for metodo, url, kw in pedidos:
        r = api.request(metodo, url, headers=ALLOWED, **kw)
        if r.status_code != 200:
            continue
        vazamentos += [f"{metodo} {url} {kw} → {a}" for a in list(_achados(r.json()))[:2]]
    assert not vazamentos, "\n".join(vazamentos)
