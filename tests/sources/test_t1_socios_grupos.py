# SPDX-License-Identifier: AGPL-3.0-or-later
"""T1 — cruzamento societário (grupos): propriedade direta, sócio em comum, quadro idêntico e holdings externas."""
import httpx
import pytest
import respx

from sources.socios_grupos import enrich as sg
from tests.sources.conftest import read_gz, write_gz


def s(ident, nome, doc, qual="49"):
    return {"identificador_socio": ident, "nome_socio": nome, "cnpj_cpf_socio": doc, "qualificacao_socio": qual,
            "data_entrada_sociedade": "20200101", "representante_legal": "", "nome_representante": "", "faixa_etaria": "3"}


BASICOS = {"A": "10000001", "B": "10000002", "C": "10000003", "D": "10000004", "E": "10000005", "F": "10000006"}


@pytest.fixture()
def cenario(base, date_str, monkeypatch):
    monkeypatch.setattr(sg, "BRASILAPI_DELAY", 0)
    cnpj = lambda k: BASICOS[k] + "0001" + sg._cnpj_check_digits(BASICOS[k] + "0001")
    write_gz(base / "normalized" / date_str / "summary" / "anatel_scm.json.gz", {"by_cnpj": {
        cnpj(k): [{"logradouro": f"Rua {k}", "municipio": "Cidade", "uf": "SP"}] for k in "ABCDEF"}})
    holding = "99887766"                                   # PJ externa à base
    write_gz(base / "normalized" / date_str / "summary" / "receita_socios.json.gz", {
        "dump_reference": "2026-09", "generated_at": "2026-09-28T00:00:00",
        "by_cnpj_basico": {
            # A e B: mesma holding externa e o mesmo PF → quadro idêntico
            BASICOS["A"]: [s("1", "HOLDING EXTERNA SA", holding), s("2", "Maria da Silva", "***111222**")],
            BASICOS["B"]: [s("1", "HOLDING EXTERNA SA", holding), s("2", "MARIA DA SILVA", "***111222**")],
            # C controla D com exclusividade (D tem C como única sócia)
            BASICOS["C"]: [s("2", "Pedro Souza", "***333444**")],
            BASICOS["D"]: [s("1", "C OPERADORA", BASICOS["C"])],
            # E tem C entre vários sócios → controle parcial; F compartilha só um PF com E
            BASICOS["E"]: [s("1", "C OPERADORA", BASICOS["C"]), s("2", "Joana Lima", "***555666**")],
            BASICOS["F"]: [s("2", "Joana Lima", "***555666**"), s("2", "Outro Sócio", "***777888**")],
        }})
    return {k: cnpj(k) for k in "ABCDEF"}, holding


def brasilapi_holding(respx_mock, holding):
    matriz = sg._matriz_cnpj(holding)
    return respx_mock.get(f"https://brasilapi.com.br/api/cnpj/v1/{matriz}").respond(200, json={
        "razao_social": "HOLDING EXTERNA PARTICIPACOES S.A.", "nome_fantasia": "", "descricao_situacao_cadastral": "ATIVA",
        "natureza_juridica": "Sociedade Anônima Fechada", "porte": "DEMAIS", "capital_social": 1000000,
        "municipio": "SAO PAULO", "uf": "SP", "cep": "01000000", "logradouro": "RUA X", "numero": "1"})


@respx.mock
def test_agrupa_e_classifica_relacoes(base, log, cenario, date_str):
    cn, holding = cenario
    brasilapi_holding(respx, holding)
    r = sg.run(date_str, base, log)
    grupos = {tuple(g["cnpj_basicos"]): g for g in r["grupos"]}
    ab = grupos[tuple(sorted([BASICOS["A"], BASICOS["B"]]))]
    assert ab["tamanho"] == 2 and ab["classificacao"] == "total"                  # quadro idêntico
    cdef = [g for g in r["grupos"] if BASICOS["C"] in g["cnpj_basicos"]][0]
    assert set(cdef["cnpj_basicos"]) == {BASICOS[k] for k in "CDEF"}
    assert cdef["classificacao"] == "misto"                                         # controle exclusivo + parcial
    assert r["total_grupos"] == 2 and r["total_cnpjs_em_grupo"] == 6


@respx.mock
def test_relacao_total_e_parcial_por_empresa(base, log, cenario, date_str):
    cn, holding = cenario
    brasilapi_holding(respx, holding)
    by = sg.run(date_str, base, log)["by_cnpj"]
    d = by[cn["D"]]
    assert [m["tipo_relacao"] for m in d["mesmo_grupo"]] == ["controle_exclusivo_recebido"] and d["mesmo_grupo"][0]["cnpj"] == cn["C"]
    e = by[cn["E"]]
    tipos = {(x["cnpj"], x["tipo_relacao"]) for x in e["relacionadas_parcial"]}
    assert (cn["C"], "controle_parcial_recebido") in tipos and (cn["F"], "socios_em_comum") in tipos
    f = [x for x in e["relacionadas_parcial"] if x["cnpj"] == cn["F"]][0]
    assert f["socios_em_comum"] == 1 and f["nomes_em_comum"] == []                # Joana Lima é pessoa física: conta, mas o nome não é gravado
    socios = [s for r in by.values() for s in r["socios"]]
    assert all("nome" not in s and "documento" not in s for s in socios if s["tipo"] != "juridica")
    assert any(s.get("nome") for s in socios if s["tipo"] == "juridica")          # sócio PJ (holding) continua com nome
    assert by[cn["A"]]["mesmo_grupo"][0]["tipo_relacao"] == "quadro_identico"


@respx.mock
def test_sem_transitividade_nas_arestas_diretas(base, log, cenario, date_str):
    cn, holding = cenario
    brasilapi_holding(respx, holding)
    by = sg.run(date_str, base, log)["by_cnpj"]
    # D e F estão no mesmo grupo (via C/E), mas NÃO têm relação direta entre si
    diretos_d = {x["cnpj"] for x in by[cn["D"]]["mesmo_grupo"] + by[cn["D"]]["relacionadas_parcial"]}
    assert cn["F"] not in diretos_d and by[cn["D"]]["grupo_id"] == by[cn["F"]]["grupo_id"]


@respx.mock
def test_holding_externa_resolvida_pela_matriz_e_cacheada(base, log, cenario, date_str):
    cn, holding = cenario
    route = brasilapi_holding(respx, holding)
    by = sg.run(date_str, base, log)["by_cnpj"]
    h = by[cn["A"]]["holdings_externas"][0]
    assert h["cnpj_basico"] == holding and h["razao_social"].startswith("HOLDING EXTERNA") and h["uf"] == "SP"
    assert route.call_count == 1                                                    # A e B compartilham a mesma holding
    sg.run(date_str, base, log)
    assert route.call_count == 1                                                    # 2ª execução vem do cache
    assert holding in read_gz(base / "normalized" / "holdings_cache" / "cartoes.json.gz")


@respx.mock
def test_falha_da_brasilapi_deixa_holding_vazia_sem_derrubar(base, log, cenario, date_str):
    cn, holding = cenario
    respx.get(url__regex=r"https://brasilapi\.com\.br/api/cnpj/v1/\d+").respond(500)
    h = sg.run(date_str, base, log)["by_cnpj"][cn["A"]]["holdings_externas"][0]
    assert h["razao_social"] == "" and h["cnpj_basico"] == "99887766"


@respx.mock
def test_retenta_uma_vez_em_429(base, log, cenario, date_str, monkeypatch):
    cn, holding = cenario
    monkeypatch.setattr(sg.time, "sleep", lambda s: None)
    route = respx.get(f"https://brasilapi.com.br/api/cnpj/v1/{sg._matriz_cnpj(holding)}")
    route.side_effect = [httpx.Response(429), httpx.Response(200, json={"razao_social": "OK SA"})]
    assert sg.run(date_str, base, log)["by_cnpj"][cn["A"]]["holdings_externas"][0]["razao_social"] == "OK SA"


def test_sem_receita_socios_levanta(base, log, date_str):
    with pytest.raises(FileNotFoundError, match="receita_socios"):
        sg.run(date_str, base, log)


@pytest.mark.parametrize("base12, dv", [("112223330001", "81"), ("000000000001", "91"), ("114447770001", "61")])
def test_digitos_verificadores_do_cnpj(base12, dv):
    assert sg._cnpj_check_digits(base12) == dv


def test_matriz_cnpj_completa_14_digitos():
    m = sg._matriz_cnpj("11222333")
    assert m == "11222333000181" and len(m) == 14


@pytest.mark.parametrize("nome, esperado", [("  José  Açaí  Ltda ", "JOSE ACAI LTDA"), ("MARIA", "MARIA"), ("", ""), (None, "")])
def test_normalize_name(nome, esperado):
    assert sg._normalize_name(nome) == esperado


def test_chaves_de_identidade_ignoram_estrangeiro_e_documento_vazio():
    keys = sg._socio_identity_keys([
        s("1", "PJ", "12345678"), s("2", "Fulano", "***1**"), s("3", "Foreign", ""), s("2", "", "***2**"), s("2", "Sem Doc", ""),
    ])
    assert keys == {"cnpj:12345678", "pf:FULANO|***1**"}


def test_union_find():
    u = sg._UnionFind(["a", "b", "c", "d"])
    u.union("a", "b")
    u.union("c", "b")
    assert u.find("a") == u.find("c") and u.find("a") != u.find("d")
