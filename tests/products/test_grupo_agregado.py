# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — `GET /grupos/{grupo_id}`: grupo consolidado, só estrutura entre empresas (PJ)."""
import json
import re


def _grupos(api):
    return api.get("/api/v1/grupos").json()["grupos"]


def test_grupo_consolida_composicao_mercado_e_rede(api):
    g = next(x for x in _grupos(api) if x["tamanho"] >= 2)
    r = api.get(f"/api/v1/grupos/{g['grupo_id']}")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["grupo_id"] == g["grupo_id"] and j["classificacao"] == g["classificacao"] and j["empresas"] == len({c["cnpj"][:8] for c in g["cnpjs"]})
    assert [c["cnpj"] for c in j["cnpjs"]] == [c["cnpj"] for c in g["cnpjs"]] and j["assinantes"] == g["assinantes"]
    assert j["asns"] == sorted({a for c in g["cnpjs"] for a in (c.get("asns") or [])})
    for parte in ("credito_publico", "sancoes", "contratos"):
        assert j[parte]["natureza"]                                             # toda soma diz o que é e o que não é


def test_somas_batem_com_o_artefato_e_dizem_quantas_empresas_tem_o_dado(api):
    store = api.app.state.store
    d = store.latest()
    ops = (store.financiamento_doc(d) or {}).get("operadoras") or {}
    n_com = 0
    for g in _grupos(api):
        j = api.get(f"/api/v1/grupos/{g['grupo_id']}").json()
        raizes = {c["cnpj"][:8] for c in g["cnpjs"]}
        com = [ops[r]["financiamento"] for r in raizes if (ops.get(r) or {}).get("financiamento")]
        assert j["credito_publico"]["empresas_com_registro"] == len(com)
        assert j["credito_publico"]["operacoes"] == sum(c["operacoes_total"] for c in com)
        n_com += len(com)
    assert n_com > 0                                                            # o sintético tem crédito: a soma não é testada no vazio


def test_nenhum_dado_de_pessoa_fisica_na_resposta(api):
    for g in _grupos(api)[:50]:
        texto = json.dumps(api.get(f"/api/v1/grupos/{g['grupo_id']}").json(), ensure_ascii=False)
        assert not re.search(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", texto), g["grupo_id"]           # CPF
        assert not re.search(r'"(socios?|nomes_em_comum|cpf|cpf_cnpj_socio)"', texto)
        assert "@" not in texto and not re.search(r'"(email|telefone|phone)"', texto)


def test_grupo_desconhecido_e_404(api):
    assert api.get("/api/v1/grupos/nao-existe").status_code == 404
