# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""PT-26: fatos de conformidade declaratória (eventos de declaração por município, credenciada de rede virtual).

Só fato com dado: nenhuma causa sem fonte; nenhum texto qualifica infração.
"""
from products.sici_indicadores.build import calcular_indicadores, calcular_sem_declaracao, credenciadas_rede_virtual, somar_meses


def _mes(**ops):
    out = {}
    for cnpj, (total, muns) in ops.items():
        out[cnpj] = {"empresa": f"EMP{cnpj}", "uf": "SP", "acessos": total,
                     "por_municipio": {i: {"uf": "SP", "nome": f"M{i}", "acessos": a} for i, a in muns.items()}}
    return out


def _serie(valores, ate):
    return [[somar_meses(ate, -(len(valores) - 1 - i)), v, 0, v] for i, v in enumerate(valores)]


def test_evento_sem_declaracao_desde_com_ultimo_mes_e_acessos():
    # X declarava em 3550308 em 2026-07 (mês anterior) e em 2025-09; não declara nada em 2026-09; Y segue declarando
    atual = _mes(Y=(900, {"3550308": 900}))
    ant = _mes(Y=(900, {"3550308": 900}), X=(251, {"3550308": 251}))
    ano = _mes(Y=(800, {"3550308": 800}), X=(299, {"3550308": 299}))
    series = {"X": _serie([299, 280, 251], "2026-07"), "Y": _serie([800, 900, 900], "2026-09")}
    r = calcular_indicadores("2026-08", {"2026-08": atual, "2026-07": ant, "2025-08": ano}, series)
    ev = r["municipios"]["3550308"]["eventos"]
    assert len(ev) == 1
    e = ev[0]
    assert (e["cnpj"], e["tipo"], e["acessos"], e["mes_acessos"], e["ultimo_mes_declarado"]) == ("X", "sem_declaracao_desde", 251, "2026-07", "2026-07")
    assert "causa" not in e and "omi" + "ss" not in str(ev).lower()


def test_cnpj_que_declarou_no_mes_mas_saiu_do_municipio_nao_e_evento():
    atual = _mes(Y=(900, {"3550308": 900}), X=(10, {"3304557": 10}))
    ant = _mes(Y=(900, {"3550308": 900}), X=(260, {"3550308": 250, "3304557": 10}))
    series = {"X": _serie([260, 260], "2026-08"), "Y": _serie([900, 900], "2026-08")}
    r = calcular_indicadores("2026-08", {"2026-08": atual, "2026-07": ant}, series)
    assert "eventos" not in r["municipios"]["3550308"]


def test_primeira_declaracao_so_quando_a_serie_comeca_no_mes_de_referencia():
    atual = _mes(Y=(900, {"3550308": 900}), N=(50, {"3550308": 50}))
    ant = _mes(Y=(900, {"3550308": 900}))
    series = {"Y": _serie([900, 900], "2026-08"), "N": _serie([50], "2026-08")}
    r = calcular_indicadores("2026-08", {"2026-08": atual, "2026-07": ant}, series)
    ev = r["municipios"]["3550308"]["eventos"]
    assert [(e["cnpj"], e["tipo"], e["mes"], e["acessos"]) for e in ev] == [("N", "primeira_declaracao", "2026-08", 50)]


def test_municipio_sem_evento_nao_ganha_o_campo():
    atual = _mes(Y=(900, {"3550308": 900}))
    r = calcular_indicadores("2026-08", {"2026-08": atual}, {"Y": _serie([900, 900], "2026-08")})
    assert "eventos" not in r["municipios"]["3550308"]


def test_cnpj_sem_serie_nao_gera_evento_sem_declaracao():
    atual = _mes(Y=(900, {"3550308": 900}))
    ant = _mes(Y=(900, {"3550308": 900}), X=(5, {"3550308": 5}))
    r = calcular_indicadores("2026-08", {"2026-08": atual, "2026-07": ant}, {"Y": _serie([900, 900], "2026-08")})
    assert "eventos" not in r["municipios"]["3550308"]


def test_credenciadas_de_rede_virtual_pelo_smp():
    smp = {"by_cnpj": {
        "11": [{"rede_virtual": {"papel": "credenciada", "prestadora_origem_cnpj": "99"}}],
        "99": [{"rede_virtual": {"papel": "host", "credenciadas_count": 1}}],
        "22": [{"rede_virtual": None}],
    }}
    assert credenciadas_rede_virtual(smp) == {"11": "99"}
    assert credenciadas_rede_virtual(None) == {}


def test_sem_declaracao_traz_a_origem_so_de_quem_e_credenciada():
    scms = [{"cnpj": "11", "razao_social": "Virtual", "uf": "SP", "asns": []}, {"cnpj": "12", "razao_social": "Outra", "uf": "SP", "asns": []}]
    r = calcular_sem_declaracao("2026-08", scms, set(), {}, None, {"11": "99"})
    assert r["itens"]["11"]["rede_virtual_origem"] == "99"
    assert "rede_virtual_origem" not in r["itens"]["12"]
    assert "rede_virtual_origem" not in calcular_sem_declaracao("2026-08", scms, set(), {})["itens"]["11"]


def test_eventos_de_ei_saem_com_o_nome_publico_pela_regra_de_pessoa_natural():
    """O evento traz `cnpj` e `empresa`: a regra de `core.pessoa_natural` o alcança (D1; dado novo com nome de titular precisa do identificador)."""
    from core import pessoa_natural as pn
    idx = pn.Indice()
    idx.adicionar("12345678", cnpj="12345678000190", fantasia="Fibra Rápida", nomes=["MARIA DA SILVA 01234567890"])
    doc = {"municipios": {"3550308": {"eventos": [
        {"cnpj": "12345678000190", "empresa": "MARIA DA SILVA 01234567890", "tipo": "sem_declaracao_desde", "mes": "2026-08", "acessos": 10, "mes_acessos": "2026-07"},
        {"cnpj": "99999999000199", "empresa": "REDE PJ LTDA", "tipo": "primeira_declaracao", "mes": "2026-09", "acessos": 5, "mes_acessos": "2026-09"}]}}}
    saida = pn.aplicar(doc, idx)
    ev = saida["municipios"]["3550308"]["eventos"]
    assert ev[0]["empresa"] == "Fibra Rápida" and ev[1]["empresa"] == "REDE PJ LTDA"
    assert "MARIA" not in str(saida)


def test_cadastro_do_asn_so_com_campos_permitidos_e_a_data_da_leitura():
    from api.services.asn_cadastro import bloco_cadastro
    org = {"cnpj": "01264994000116", "razao_social": "Unilink Redes Ltda", "descricao_situacao_cadastral": "BAIXADA", "descricao_motivo_situacao_cadastral": "EXTINCAO",
           "cnae_fiscal_descricao": "Desenvolvimento de programas", "municipio": "Barueri", "uf": "SP", "codigo_municipio_ibge": 3505708,
           "logradouro": "RUA X", "numero": "1", "cep": "06400000", "lat": -23.5, "lon": -46.8, "ddd_telefone_1": "1144445555", "email": "a@b.c", "cached_at": "2026-06-12T10:00:00+00:00"}
    b = bloco_cadastro(org)
    assert b["descricao_situacao_cadastral"] == "BAIXADA" and b["lido_em"].startswith("2026-06-12") and b["selo"] == "fato"
    assert not ({"logradouro", "numero", "cep", "lat", "lon", "ddd_telefone_1", "email"} & set(b))
    assert bloco_cadastro(None) is None and bloco_cadastro({}) is None


def test_recuperacao_do_asn_so_por_tipo_asn_e_sem_motivo():
    from api.services.asn_cadastro import bloco_recuperacao
    doc = {"em_recuperacao": {"itens": [
        {"tipo": "bloco", "recurso": "198.18.0.0/24", "inicio": "2026-09-01", "fim": "2026-11-30"},
        {"tipo": "asn", "recurso": "22351", "inicio": "2026-09-01", "fim": "2026-11-30", "primeira_vez_visto": "2026-06-28"}]}}
    r = bloco_recuperacao(doc, 22351)
    assert (r["inicio"], r["fim"], r["selo"]) == ("2026-09-01", "2026-11-30", "fato") and "motivo" not in r
    assert bloco_recuperacao(doc, 13357) is None and bloco_recuperacao(None, 1) is None
