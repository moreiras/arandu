# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""PT-10 (D5), grupo societário na API sintética: só quem tem participação liga, nome por regra, `grupo_id` estável e redirecionamento, cabeçalho da operadora."""
import json

import pytest

from tests.products.api_contract import ALLOWED


def _get(api, path, **params):
    r = api.get(f"/api/v1{path}", params=params or None, headers=ALLOWED)
    assert r.status_code == 200, (path, r.status_code, r.text[:200])
    return r.json()


@pytest.fixture(scope="module")
def grupos(api):
    return _get(api, "/grupos")["grupos"]


def test_diretor_e_presidente_em_comum_nao_formam_grupo(api, grupos):
    """Cenário 11: as duas últimas operadoras sem ASN dividem diretor (10) e presidente (16), sem participação."""
    individuais = {g["cnpjs"][0]["cnpj"]: g for g in grupos if g["classificacao"] == "individual"}
    sem_asn = sorted(c for c, g in individuais.items() if (g["cnpjs"][0]["empresa"] or "").startswith("Provedor Sem ASN"))
    assert len(sem_asn) >= 2
    # a empresa individual `ind_<raiz>` das duas continua individual e sem relacionadas
    for cnpj in sem_asn[-2:]:
        rel = _get(api, f"/grupos/empresa/{cnpj}")
        assert rel["grupo_id"] == f"ind_{cnpj[:8]}" and not rel["mesmo_grupo"] and not rel["relacionadas_parcial"]


def test_grupo_id_e_o_menor_cnpj_basico_do_componente(grupos):
    reais = [g for g in grupos if g["classificacao"] != "individual"]
    assert reais
    for g in reais:
        assert g["grupo_id"] == "grp_" + min(c["cnpj"][:8] for c in g["cnpjs"])


def test_nome_do_grupo_por_regra_visivel(grupos):
    for g in grupos:
        assert g["nome"] and g["nome_regra"] in ("marca_curada", "maior_acesso_sici", "menor_cnpj") and g["nome_regra_texto"]
        if g["nome_regra"] == "maior_acesso_sici":
            maior = min(g["cnpjs"], key=lambda c: (-c["assinantes"], c["cnpj"]))
            assert g["nome"] == maior["empresa"] and g["nome_base"] == maior["cnpj"]       # o CNPJ com mais acessos no SICI, não o nome mais longo


def test_link_antigo_de_grupo_redireciona_para_o_id_estavel(api, grupos):
    g = next(x for x in grupos if x["classificacao"] != "individual" and x["tamanho"] >= 2)
    outro = sorted({c["cnpj"][:8] for c in g["cnpjs"]})[-1]            # um membro que não é o menor: era um id possível da union-find
    antigo = f"grp_{outro}"
    assert antigo != g["grupo_id"]
    r = _get(api, f"/grupos/{antigo}")
    assert r["grupo_id"] == g["grupo_id"] and r["redirecionado_de"] == antigo
    assert _get(api, f"/grupos/{g['grupo_id']}")["redirecionado_de"] is None
    assert _get(api, f"/grupos/{antigo}/prefixos-geo")["grupo_id"] == g["grupo_id"]
    assert api.get("/api/v1/grupos/grp_00000000", headers=ALLOWED).status_code == 404       # id sem nenhum CNPJ da base não vira outro grupo
    # empresa individual que depois entrou num grupo: `ind_<raiz>` leva ao grupo atual
    assert _get(api, f"/grupos/ind_{outro}")["grupo_id"] == g["grupo_id"]


def test_ligacoes_com_forca_e_classe_sem_nome(api, grupos):
    g = next(x for x in grupos if x["classificacao"] != "individual")
    rel = _get(api, f"/grupos/{g['grupo_id']}", include="relacoes")["relacoes"]
    assert rel["ligacoes"] and all(x["forca"] in ("forte", "fraca") for x in rel["ligacoes"])
    assert all(set(x["classes_qualificacao"]) <= {"socio", "socio_administrador", "acionista", "titular"} for x in rel["ligacoes"])
    assert any(x["classes_qualificacao"] for x in rel["ligacoes"])
    assert rel["resumo"]["ligacoes"] == len(rel["ligacoes"]) == rel["resumo"]["fortes"] + rel["resumo"]["fracas"]
    corpo = json.dumps(rel, ensure_ascii=False)
    for nome in ("Ana Exemplo", "Bruno Exemplo", "Carla Exemplo", "Diego Exemplo", "Socio Unico"):
        assert nome not in corpo
    assert "regra_ligacao" in rel


def test_cabecalho_da_operadora_traz_o_grupo_societario(api, grupos):
    g = next(x for x in grupos if x["classificacao"] != "individual" and x["tamanho"] >= 2)
    cnpj = g["cnpjs"][0]["cnpj"]
    r = _get(api, f"/grupos/empresa/{cnpj}")
    gs = r["grupo_societario"]
    assert gs["grupo_id"] == g["grupo_id"] == r["grupo_id"] and gs["tamanho"] == g["tamanho"] and gs["nome"] == g["nome"] and gs["nome_regra"] == g["nome_regra"]
    assert cnpj not in {i["cnpj"] for i in gs["integrantes"]} and gs["integrantes_total"] == len(g["cnpjs"]) - 1
    ind = next(x for x in grupos if x["classificacao"] == "individual")
    gi = _get(api, f"/grupos/empresa/{ind['cnpjs'][0]['cnpj']}")["grupo_societario"]
    assert gi["classificacao"] == "individual" and gi["integrantes"] == [] and gi["tamanho"] == 1
