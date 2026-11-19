# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Entrada tolerante do MCP: formas que os modelos menores mandam de fato."""
import pytest

from api import query as q
from mcp_server import entrada as e

PTTS = {"ce": "Fortaleza", "ba": "Salvador", "sp": "São Paulo", "vix": "Vitória"}
SNAPS = ["2026-11-06", "2026-11-13"]


@pytest.fixture(autouse=True)
def _ptts():
    e.registrar_fonte_ptts(lambda: PTTS)
    yield
    e.registrar_fonte_ptts(None)


def _schema(**props):
    req = [k for k, v in props.items() if v.pop("_req", False)]
    return {"properties": props, "required": req}


OPC_STR = {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None}
OPC_INT = {"anyOf": [{"type": "integer"}, {"type": "null"}], "default": None}
OPC_BOOL = {"anyOf": [{"type": "boolean"}, {"type": "null"}], "default": None}


def norm(tool, args, schema):
    return e.normalizar(tool, args, schema, lambda: SNAPS)


def test_nulos_booleanos_e_numeros_em_texto():
    s = _schema(uf=dict(OPC_STR), com_asn=dict(OPC_BOOL), limit={"type": "integer", "default": 10}, ibge=dict(OPC_STR))
    args, aj = norm("operadora_ranking", {"uf": "null", "com_asn": "False", "limit": "8", "ibge": ""}, s)
    assert args == {"com_asn": False, "limit": 8}
    assert {a["campo"] for a in aj} == {"uf", "com_asn", "limit"}


def test_valor_embrulhado_no_formato_do_schema():
    s = _schema(collection={"type": "string", "_req": True}, date=dict(OPC_STR))
    args, aj = norm("query", {"collection": {"type": "string", "value": "asns"}, "date": {"type": "null"}}, s)
    assert args == {"collection": "asns"}
    assert aj[0]["motivo"].startswith("valor desembrulhado")


def test_asn_com_prefixo_e_lista_em_texto():
    s = _schema(asn={"type": "integer", "_req": True}, asns={"type": "array", "items": {"type": "integer"}})
    args, _ = norm("asn_lote", {"asn": "AS28126", "asns": "28126, 7738"}, s)
    assert args == {"asn": 28126, "asns": [28126, 7738]}


def test_data_inexistente_e_recusada_com_a_lista():
    s = _schema(date=dict(OPC_STR))
    with pytest.raises(e.EntradaInvalida, match="2026-11-13"):
        norm("ixp_detalhe", {"date": "2022-01-01"}, s)
    assert norm("ixp_detalhe", {"date": "2026-11-06"}, s)[0] == {"date": "2026-11-06"}


def test_cnpj_e_ibge():
    s = _schema(cnpj=dict(OPC_STR), ibge=dict(OPC_STR))
    assert norm("x", {"cnpj": "04.601.397/0001-28"}, s)[0]["cnpj"] == "04601397000128"
    with pytest.raises(e.EntradaInvalida, match="12 dígitos"):
        norm("x", {"cnpj": "30.291.856-00-01"}, s)
    with pytest.raises(e.EntradaInvalida, match="dígito verificador"):
        norm("x", {"cnpj": "04601397000129"}, s)
    assert norm("x", {"cnpj": "04601397"}, s)[0]["cnpj"] == "04601397"          # raiz
    with pytest.raises(e.EntradaInvalida, match="7 dígitos"):
        norm("x", {"ibge": "59723-000"}, s)


def test_uf_por_nome_e_sigla_invalida():
    s = _schema(uf=dict(OPC_STR))
    assert norm("ixp_lista", {"uf": "Bahia"}, s)[0] == {"uf": "BA"}
    assert norm("ixp_lista", {"uf": "ce"}, s)[0] == {"uf": "CE"}
    with pytest.raises(e.EntradaInvalida, match="UF desconhecida"):
        norm("ixp_lista", {"uf": "XX"}, s)


def test_codigo_de_ptt_por_cidade_e_desconhecido():
    s = _schema(code={"type": "string", "_req": True})
    args, aj = norm("ixp_detalhe", {"code": "Fortaleza"}, s)
    assert args == {"code": "ce"} and aj[0]["usado"] == "ce"
    assert norm("ixp_detalhe", {"code": "IX.br Vitória"}, s)[0] == {"code": "vix"}
    with pytest.raises(e.EntradaInvalida, match="Código de PTT desconhecido: 'sal'"):
        norm("ixp_detalhe", {"code": "sal"}, s)
    # PTT externo só vai para minúsculas
    assert norm("ixp_externo", {"code": "DECIX-SP"}, s)[0] == {"code": "decix-sp"}


QS = _schema(collection={"type": "string", "_req": True}, filter={"anyOf": [{"type": "object"}, {"type": "null"}]},
             sort={"anyOf": [{"type": "array", "items": {}}, {"type": "null"}]},
             aggregate={"anyOf": [{"type": "array", "items": {}}, {"type": "null"}]},
             group_by={"anyOf": [{"type": "array", "items": {}}, {"type": "null"}]})


def test_query_filtro_em_texto_e_formas_abreviadas():
    args, _ = norm("query", {"collection": "asns", "filter": '{and: [{field: "uf", op: "eq", value: "SC"}]}'}, QS)
    assert args["filter"] == {"and": [{"field": "uf", "op": "eq", "value": "SC"}]}
    args, _ = norm("query", {"collection": "asns", "filter": {"contains": ["ixps_direct", "Fortaleza"]}}, QS)
    assert args["filter"] == {"field": "ixps_direct", "op": "contains", "value": "ce"}
    args, _ = norm("query", {"collection": "asns", "filter": {"ixps_direct": {"ncontains": "ba"}}}, QS)
    assert args["filter"] == {"field": "ixps_direct", "op": "ncontains", "value": "ba"}
    args, _ = norm("query", {"collection": "asns", "filter": {}}, QS)
    assert "filter" not in args
    with pytest.raises(e.EntradaInvalida, match="'sal'"):
        norm("query", {"collection": "asns", "filter": {"field": "ixps_direct", "op": "ncontains", "value": "sal"}}, QS)


def test_query_sort_e_aggregate():
    for forma in ("apnic_users desc", "-apnic_users", [{"field": "apnic_users", "desc": True}], [{"field": "apnic_users", "order": "DESC"}]):
        args, _ = norm("query", {"collection": "asns", "sort": forma}, QS)
        assert args["sort"] == [{"field": "apnic_users", "dir": "desc"}], forma
    args, _ = norm("query", {"collection": "asns", "aggregate": ["count", "sum:apnic_users", {"avg": "pct_v6"}], "group_by": "uf"}, QS)
    assert args["aggregate"] == [{"fn": "count"}, {"fn": "sum", "field": "apnic_users"}, {"fn": "avg", "field": "pct_v6"}]
    assert args["group_by"] == ["uf"]


def test_argumento_desconhecido_vira_ajuste():
    s = _schema(asn={"type": "integer", "_req": True})
    args, aj = norm("asn_detalhe", {"asn": 1, "blocos": ["x"]}, s)
    assert args == {"asn": 1} and "não existe" in aj[0]["motivo"]


def test_compactar_acrescenta_ajustes():
    from mcp.types import TextContent
    out = e.compactar([TextContent(type="text", text='{\n  "a": 1\n}')], [{"campo": "x"}])
    assert out[0].text == '{"a":1,"ajustes":[{"campo":"x"}]}'


# ── camada de consulta (compartilhada com a API) ─────────────────────────────────────────────────────────────────────────────────────
ROWS = [{"asn": 1, "name": "beta", "ixps_direct": ["ce"]}, {"asn": 2, "name": "alfa", "ixps_direct": ["ba", "ce"]},
        {"asn": 3, "name": "gama", "ixps_direct": []}]


def test_sort_com_chave_desconhecida_e_recusado():
    with pytest.raises(q.QueryError, match="sort inválido"):
        q.validate("asns", {"sort": [{"field": "apnic_users", "desc": True}]})
    q.validate("asns", {"sort": [{"field": "apnic_users", "dir": "desc"}]})


def test_desc_em_campo_de_texto():
    r = q.execute(ROWS, {"sort": [{"field": "name", "dir": "desc"}]})
    assert [i["name"] for i in r["items"]] == ["gama", "beta", "alfa"]


def test_valor_de_lista_que_nao_existe():
    with pytest.raises(q.QueryError, match="'sal' não aparece"):
        q.validar_valores_de_lista(ROWS, {"filter": {"field": "ixps_direct", "op": "ncontains", "value": "sal"}})
    q.validar_valores_de_lista(ROWS, {"filter": {"field": "ixps_direct", "op": "contains", "value": "ba"}})


def test_municipio_com_uf_e_sem_acento():
    assert e.separa_uf("Mossoró, RN") == ("Mossoró", "RN")
    assert e.separa_uf("Boa Vista (Roraima)") == ("Boa Vista", "RR")
    assert e.separa_uf("Feira de Santana") == ("Feira de Santana", None)
    muns = [{"nome": "Boa Vista", "uf": "RR"}, {"nome": "Boa Vista", "uf": "PB"}, {"nome": "Mossoró", "uf": "RN"},
            {"nome": "Palmas", "uf": "TO"}, {"nome": "Palmas de Monte Alto", "uf": "BA"}]
    assert e.casa_municipio("Mossoro", muns)[0] == [muns[2]]
    assert len(e.casa_municipio("Boa Vista", muns)[0]) == 2                     # homônimos: quem chama devolve os candidatos
    assert e.casa_municipio("Boa Vista, PB", muns)[0] == [muns[1]]
    assert e.casa_municipio("Palmas", muns)[0] == [muns[3]]                     # igualdade antes de trecho
    assert e.casa_municipio("Mosoro", muns) == ([], ["Mossoró (RN)"])


def test_sem_socios_pessoa_fisica():
    from core.cpf import sem_socios_pessoa_fisica
    doc = {"by_cnpj": {"1": {"socios": [{"tipo": "fisica", "nome": "FULANO", "documento": "***123456**", "qualificacao": "49"},
                                        {"tipo": "juridica", "nome": "HOLDING X LTDA", "documento": "12345678", "qualificacao": "22"},
                                        {"tipo": "estrangeiro", "nome": "JOHN DOE", "documento": "", "qualificacao": "37"}],
                             "relacionadas_parcial": [{"cnpj": "2", "socios_em_comum": 2, "nomes_em_comum": ["FULANO", "HOLDING X LTDA"]}]}}}
    r = sem_socios_pessoa_fisica(doc)["by_cnpj"]["1"]
    assert r["socios"] == [{"tipo": "fisica", "qualificacao": "49"}, {"tipo": "juridica", "nome": "HOLDING X LTDA", "documento": "12345678", "qualificacao": "22"},
                           {"tipo": "estrangeiro", "qualificacao": "37"}]
    assert r["relacionadas_parcial"][0] == {"cnpj": "2", "socios_em_comum": 2, "nomes_em_comum": ["HOLDING X LTDA"]}
    assert "FULANO" not in str(sem_socios_pessoa_fisica(doc)) and sem_socios_pessoa_fisica({"x": 1}) == {"x": 1}
