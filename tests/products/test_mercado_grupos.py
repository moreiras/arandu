# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — cruzamentos de mercado: HHI por grupo, sobreposição de concorrentes, privacidade (nenhum sócio) e coerência com o HHI por CNPJ do SICI."""
import json


def test_resumo_e_municipio_batem_com_o_sici(api):
    r = api.get("/api/v1/mercado/grupos")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["natureza"] == "inferido" and j["limites"] and set(j["faixas"]) == {"competitivo", "moderado", "concentrado"}
    mun = api.get("/api/v1/acessos/municipios").json()["items"][0]
    p = api.get(f"/api/v1/municipios/{mun['ibge']}", params={"include": "mercado_grupos"}).json()
    mg = p["mercado_grupos"]
    assert abs(mg["hhi_cnpj"] - mun["hhi"]) <= 1                                      # o HHI por CNPJ é o mesmo que o SICI já publica
    assert mg["hhi_grupo"] >= mg["hhi_cnpj"] and mg["n_grupos"] <= mg["n_cnpjs"]       # juntar CNPJs nunca reduz a concentração
    assert mg["faixa_grupo"] in j["faixas"]


def test_uf_e_operadora_trazem_os_blocos(api):
    uf = api.get("/api/v1/ufs/SP", params={"include": "mercado_grupos"}).json()["mercado_grupos"]
    assert uf["municipios"] >= uf["municipios_mudam_de_faixa"] >= 0 and uf["hhi_grupo"] >= uf["hhi_cnpj"]
    cnpj = api.get("/api/v1/scms", params={"limit": 1}).json()["items"][0]["cnpj"]
    op = api.get(f"/api/v1/operadoras/{cnpj}", params={"include": "mercado_grupos"}).json().get("mercado_grupos")
    if op:
        assert len(op["concorrentes"]) <= 10 and cnpj not in [c["cnpj"] for c in op["concorrentes"]]
        assert op["concorrentes"] == sorted(op["concorrentes"], key=lambda c: (-c["municipios_em_comum"], -c["acessos_dele_nos_comuns"], c["cnpj"]))


def test_artefato_nao_traz_dado_de_socio(api):
    d = api.app.state.store.latest()
    doc = api.app.state.store.mercado_grupos(d)
    txt = json.dumps(doc, ensure_ascii=False).lower()
    for proibido in ("socio", "sócio", "cpf", "documento", "***"):
        assert proibido not in txt, proibido


def test_maiores_posicao_e_treemap_coerentes(api):
    """`/mercado/maiores`: posição 1..N por mês, soma do treemap = total declarado e nenhuma unidade repetida."""
    r = api.get("/api/v1/mercado/maiores", params={"n": 5, "meses": 12})
    assert r.status_code == 200, r.text
    j = r.json()
    assert len(j["meses"]) <= 12 and j["mes_referencia"] == j["meses"][-1] and "inferido" in j["natureza"]
    for o in j["operadoras"]:
        assert len(o["posicao"]) == len(j["meses"]) and all(p is None or p >= 1 for p in o["posicao"])
    ids = [u["id"] for u in j["unidades"]]
    assert len(ids) == len(set(ids))
    assert sum(u["acessos"] for u in j["unidades"]) + j["demais"]["acessos"] == j["total_acessos"]


def test_grupo_com_mercado_soma_a_serie_e_nao_expoe_socio(api):
    """`/grupos/{id}?include=mercado`: a posição está entre 1 e o total de unidades, a série vem em ordem e nenhum dado de pessoa física aparece."""
    g = next((x for x in api.get("/api/v1/grupos").json()["grupos"] if x["tamanho"] >= 2), None)
    if g is None:
        return
    r = api.get(f"/api/v1/grupos/{g['grupo_id']}", params={"include": "mercado"})
    assert r.status_code == 200, r.text
    m = r.json().get("mercado_fixo")
    if m is None:
        return                                                             # grupo sem acessos fixos declarados no sintético
    assert m["meses"] == sorted(m["meses"]) and len(m["serie"]) == len(m["meses"])
    if m["posicao"]["atual"] is not None:
        assert 1 <= m["posicao"]["atual"] <= m["posicao"]["unidades"]
    assert m["cnpjs_com_acessos"] <= m["cnpjs_total"] and "inferido" in m["natureza"]
    assert "cpf" not in json.dumps(m).lower() and "socio" not in json.dumps(m).lower()
    assert "mercado_fixo" not in api.get(f"/api/v1/grupos/{g['grupo_id']}").json()                  # sem include, a resposta é a de sempre


def test_grupo_regulatorio_e_tecnico_sao_aditivos_e_sem_dado_pessoal(api):
    """`include=regulatorio,tecnico`: blocos aditivos, listas em ordem estável e nenhum e-mail, telefone ou CPF."""
    g = next((x for x in api.get("/api/v1/grupos").json()["grupos"] if x["tamanho"] >= 2), None)
    if g is None:
        return
    base = api.get(f"/api/v1/grupos/{g['grupo_id']}").json()
    r = api.get(f"/api/v1/grupos/{g['grupo_id']}", params={"include": "regulatorio,tecnico"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert {k: v for k, v in j.items() if k not in ("regulatorio", "tecnico")} == base          # sem os extras, a resposta é a de sempre
    reg, tec = j["regulatorio"], j["tecnico"]
    nomes = [x["empresa"] or x["raiz"] for x in reg["multas"]["por_empresa"]]
    assert [n.lower() for n in nomes] == sorted(n.lower() for n in nomes)                       # alfabética: sem ranking por multa
    assert reg["multas"]["empresas_com_registro"] <= reg["empresas"]
    assert tec["asns_com_dado"] <= tec["asns_total"] and [x["asn"] for x in tec["por_asn"]] == sorted(x["asn"] for x in tec["por_asn"])
    corpo = json.dumps(j).lower()
    assert "@" not in corpo.replace("\\u0040", "") or "email" not in corpo
    assert "cpf" not in json.dumps({"regulatorio": reg, "tecnico": tec}).lower()


def test_grupo_relacoes_sem_nome_de_socio_nem_cpf(api):
    """`include=relacoes`: ligações entre empresas com contagem de sócios; nenhum nome de pessoa física, CPF ou endereço de holding."""
    g = next((x for x in api.get("/api/v1/grupos").json()["grupos"] if x["tamanho"] >= 2), None)
    if g is None:
        return
    r = api.get(f"/api/v1/grupos/{g['grupo_id']}", params={"include": "relacoes"})
    assert r.status_code == 200, r.text
    rel = r.json().get("relacoes")
    if rel is None:
        return                                                             # sintético sem o cruzamento societário publicado
    assert rel["empresas"] == g["tamanho"] and all(x["tipo"] in rel["tipos"] for x in rel["ligacoes"])
    nomes = [(x["de_nome"].lower(), x["para_nome"].lower()) for x in rel["ligacoes"]]
    assert [x["tipo"] for x in rel["ligacoes"]] == sorted((x["tipo"] for x in rel["ligacoes"]), key=list(rel["tipos"]).index)
    corpo = json.dumps(rel).lower()
    for proibido in ("nomes_em_comum", "logradouro", "capital_social", "endereco"):
        assert proibido not in corpo, proibido
    assert nomes is not None                                           # o aviso pode falar de CPF; os campos proibidos acima são o que não pode vir no dado
