# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""PT-23 (D5, D6, D11), "Onde atua" na API sintética: parcela e HHI locais na operadora, tabela municipal do grupo e municípios por faixa no Panorama."""
import json

import pytest

from tests.products.api_contract import ALLOWED


def _get(api, path, **params):
    r = api.get(f"/api/v1{path}", params=params or None, headers=ALLOWED)
    assert r.status_code == 200, (path, r.status_code, r.text[:300])
    return r.json()


@pytest.fixture(scope="module")
def com_sici(api):
    """Uma operadora que declara ao SICI, com as linhas municipais."""
    for it in _get(api, "/acessos/operadoras", limit=20)["items"]:
        d = _get(api, f"/acessos/operadora/{it['cnpj']}")
        if d.get("municipios_detalhe"):
            return d
    pytest.skip("o dataset sintético não tem operadora com municípios")


def test_operadora_traz_parcela_declarantes_e_hhi_coerentes_com_o_indice_do_municipio(com_sici):
    for m in com_sici["municipios_detalhe"]:
        assert m["municipio_acessos"] >= m["acessos"] > 0
        assert m["share"] == pytest.approx(100 * m["acessos"] / m["municipio_acessos"], abs=0.01)
        assert 0 < m["share"] <= 100 and m["municipio_operadores"] >= 1 and 0 < m["municipio_hhi"] <= 10000
        if m["municipio_operadores"] == 1:
            assert m["share"] == 100.0 and m["municipio_hhi"] == 10000
    assert com_sici["mes_referencia"]
    assert sum(m["acessos"] for m in com_sici["municipios_detalhe"]) == com_sici["acessos"]       # a soma por município continua igual ao total


def test_hhi_do_municipio_na_operadora_e_o_do_perfil_do_municipio(api, com_sici):
    m = com_sici["municipios_detalhe"][0]
    perfil = _get(api, f"/municipios/{m['ibge']}", include="mercado_grupos")["mercado_grupos"]
    assert abs(perfil["hhi_cnpj"] - m["municipio_hhi"]) <= 1


@pytest.fixture(scope="module")
def grupo(api):
    gs = _get(api, "/grupos")["grupos"]
    return next((x for x in gs if x["tamanho"] >= 2 and x["municipios"]), None) or next(x for x in gs if x["municipios"])


def test_tabela_municipal_do_grupo_fecha_com_o_total_e_com_a_soma_dos_acessos(api, grupo):
    j = _get(api, f"/grupos/{grupo['grupo_id']}/municipios", limit=200)
    assert j["mes_referencia"] and j["limites"] and "inferido" in j["natureza"] and j["ordem"].startswith("acessos")
    assert j["resumo"]["municipios"] == j["total"] == len(grupo["municipios"])
    todas, pag = [], 1
    while len(todas) < j["total"]:
        todas += _get(api, f"/grupos/{grupo['grupo_id']}/municipios", limit=200, page=pag)["items"]
        pag += 1
    assert sum(l["acessos"] for l in todas) == j["resumo"]["acessos"] == grupo["assinantes"]
    assert [l["acessos"] for l in todas] == sorted((l["acessos"] for l in todas), reverse=True)
    for l in todas:
        assert 0 < l["parcela"] <= 100 and l["declarantes"] >= 1 and l["municipio_acessos"] >= l["acessos"]
        assert l["hhi_grupo"] >= l["hhi_cnpj"] - 1                                   # juntar CNPJs nunca reduz a concentração (arredondamento de 1)
        assert l["faixa_grupo"] in {"competitivo", "moderado", "concentrado"}
        if l["declarantes"] == 1:
            assert l["hhi_cnpj"] == 10000 and l["parcela"] == 100.0


def test_filtro_de_uf_busca_e_ordem(api, grupo):
    j = _get(api, f"/grupos/{grupo['grupo_id']}/municipios", limit=200)
    uf = j["items"][0]["uf"]
    so_uf = _get(api, f"/grupos/{grupo['grupo_id']}/municipios", uf=uf, limit=200)
    assert so_uf["total"] == sum(1 for m in grupo["municipios"] if m["uf"] == uf) and all(l["uf"] == uf for l in so_uf["items"])
    nome = j["items"][0]["nome"]
    assert any(l["nome"] == nome for l in _get(api, f"/grupos/{grupo['grupo_id']}/municipios", q=nome[:4].upper(), limit=200)["items"])
    assert api.get(f"/api/v1/grupos/{grupo['grupo_id']}/municipios", params={"ordem": "pior"}, headers=ALLOWED).status_code == 400


def test_grupo_inexistente_404_e_nenhum_dado_de_pessoa(api, grupo):
    assert api.get("/api/v1/grupos/grp_00000000/municipios", headers=ALLOWED).status_code == 404
    txt = json.dumps(_get(api, f"/grupos/{grupo['grupo_id']}/municipios", limit=200), ensure_ascii=False).lower()
    for proibido in ("socio", "sócio", "cpf", "***"):
        assert proibido not in txt


def test_panorama_conta_cada_municipio_em_uma_faixa(api):
    j = _get(api, "/mercado/grupos")
    r = j["resumo"]
    assert sum(r["por_faixa_cnpj"].values()) == sum(r["por_faixa_grupo"].values()) == r["municipios"]
    assert sum(u["municipios"] for u in j["ufs"].values()) == r["municipios"]
    for u in j["ufs"].values():
        assert sum(u["municipios_por_faixa_cnpj"].values()) == u["municipios"]
    if "brasil" in j:
        assert 0 < j["brasil"]["hhi_cnpj"] <= 10000
