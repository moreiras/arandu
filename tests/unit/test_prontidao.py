# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Prontidão em segurança de roteamento: pesos, renormalização, classes e agregados (T0)."""
import pytest

from products.prontidao.build import agregar, calcular, carregar_regras, componentes, pontuar

REGRAS = carregar_regras()
IRR_VAZIO = {"rotas": {}, "aut_num": set(), "aut_num_por_irr": {}}


def _doc(**k):
    base = {"uf": "SP", "cnpj": "11111111000111", "prefixos": ["198.51.100.0/24", "203.0.113.0/24"], "rpki_validation": {"198.51.100.0/24": "valid", "203.0.113.0/24": "valid"},
            "pdb_registered": True, "pdb": {"irr_as_set": "AS-EXEMPLO"}, "usuarios": 1000}
    base.update(k)
    return base


SEG_BOM = {"64500": {"rov": {"validates_pct": 96.0, "amostras": 500}, "faixa_acessos_sici": "ate_1000"}}
SPOOFER_BOM = {"64500": {"suficiente": True, "pct_bloqueado": 100.0, "conclusivas": 8, "sessoes": 9, "ultima_sessao": "2026-10-01"}}
IRR_BOM = {"rotas": {64500: {"198.51.100.0/24", "203.0.113.0/24"}}, "aut_num": {64500}, "aut_num_por_irr": {"TC": {64500}}}


def test_asn_completo_e_bom_vira_pronto_com_os_quatro_pilares():
    r = pontuar(componentes(64500, _doc(), SEG_BOM, SPOOFER_BOM, IRR_BOM, {64500}, REGRAS), REGRAS)
    assert r["classe"] == "pronto" and r["pilares_sem_dado"] == [] and set(r["pilares"]) == {"filtragem", "anti_spoofing", "coordenacao", "validacao_global"}
    assert r["pilares"]["filtragem"]["score"] == pytest.approx((96 * 3 + 100 * 1) / 4, abs=0.1) and r["pilares"]["validacao_global"]["score"] == 100.0 and r["total"] > 95


def test_cenario_roa_invalido_e_sem_aspa_vira_atrasado_ou_em_progresso():
    doc = _doc(rpki_validation={"198.51.100.0/24": "invalid", "203.0.113.0/24": "not_found"}, pdb_registered=False, pdb=None)
    comps = componentes(64500, doc, {"64500": {"rov": {"validates_pct": 2.0, "amostras": 900}, "n_prefixos_bogon": 1}}, {}, IRR_VAZIO, set(), REGRAS)
    assert comps["validacao_global"]["roa"]["valor"] == 0.0 and comps["validacao_global"]["roa"]["detalhe"]["invalidos"] == 1 and comps["validacao_global"]["aspa"] is None
    assert comps["filtragem"]["sem_bogon"]["valor"] == 0.0 and comps["coordenacao"]["irr_as_set"] is None
    r = pontuar(comps, REGRAS)
    assert r["classe"] == "atrasado" and r["total"] < 20 and r["pilares_sem_dado"] == ["anti_spoofing"] and r["pilares"]["filtragem"]["score"] < 10


def test_pilar_e_componente_sem_dado_saem_e_os_pesos_renormalizam():
    comps = componentes(64500, _doc(), {}, {}, IRR_BOM, set(), REGRAS)          # sem segurança: ROV vale None; bogon vale 100
    r = pontuar(comps, REGRAS)
    assert comps["filtragem"]["sem_bogon"]["valor"] == 100.0 and comps["filtragem"]["rov"] is None
    assert "anti_spoofing" not in r["pilares"] and "filtragem" not in r["pilares"] and r["pilares_sem_dado"] == ["filtragem", "anti_spoofing"]      # filtragem exige o ROV
    esperado = (100 * 20 + 100 * 30) / 50
    assert r["total"] == pytest.approx(esperado, abs=0.1)


def test_rov_com_poucas_amostras_nao_conta_e_spoofer_insuficiente_nao_conta():
    comps = componentes(64500, _doc(), {"64500": {"rov": {"validates_pct": 100.0, "amostras": 99}}}, {"64500": {"suficiente": False, "pct_bloqueado": 100.0, "conclusivas": 2, "sessoes": 3}}, IRR_BOM, set(), REGRAS)
    assert comps["filtragem"]["rov"] is None and comps["anti_spoofing"]["spoofer"] is None


def test_menos_de_dois_pilares_e_sem_dados():
    doc = _doc(prefixos=[], rpki_validation={}, pdb_registered=False, pdb=None)
    r = pontuar(componentes(64500, doc, {}, {}, IRR_VAZIO, set(), REGRAS), REGRAS)
    assert r["classe"] == "sem_dados" and r["total"] is None and list(r["pilares"]) == ["coordenacao"]
    assert "filtragem" not in pontuar(componentes(64500, _doc(prefixos=["198.51.100.0/24"]), {}, {}, IRR_VAZIO, set(), REGRAS), REGRAS)["pilares"]       # bogon sozinho não basta


def test_irr_de_qualquer_autor_conta_e_so_o_par_prefixo_origem():
    irr = {"rotas": {64500: {"198.51.100.0/24", "192.0.2.0/24"}}, "aut_num": set(), "aut_num_por_irr": {}}       # 2 objetos, 1 prefixo anunciado coberto
    c = componentes(64500, _doc(), {}, {}, irr, set(), REGRAS)
    assert c["validacao_global"]["irr"]["valor"] == 50.0 and c["validacao_global"]["irr"]["detalhe"] == {"prefixos": 2, "com_objeto": 1} and c["coordenacao"]["irr_aut_num"]["valor"] == 0.0


def test_limites_das_classes():
    base = componentes(64500, _doc(), SEG_BOM, SPOOFER_BOM, IRR_BOM, {64500}, REGRAS)
    total = pontuar(base, REGRAS)["total"]
    assert pontuar(base, {**REGRAS, "classes": {"pronto": total, "em_progresso": 50}})["classe"] == "pronto"                    # o limite inferior é inclusivo
    assert pontuar(base, {**REGRAS, "classes": {"pronto": total + 0.1, "em_progresso": 50}})["classe"] == "em_progresso"
    assert pontuar(base, {**REGRAS, "classes": {"pronto": 101, "em_progresso": total + 0.1}})["classe"] == "atrasado"


def test_calcular_agrega_por_uf_porte_operadora_com_media_ponderada_por_usuarios():
    docs = {64500: _doc(usuarios=900), 64501: _doc(usuarios=100, rpki_validation={}, prefixos=["10.0.0.0/8"], cnpj="11111111000222"), 64502: _doc(uf="RJ", cnpj="22222222000122", usuarios=0, prefixos=[], rpki_validation={}, pdb_registered=False, pdb=None)}
    r = calcular(docs, {**SEG_BOM, "64501": {"faixa_acessos_sici": "ate_1000"}}, SPOOFER_BOM, {"rotas": {"TC": {"64500": ["198.51.100.0/24", "203.0.113.0/24"]}}, "aut_num": {"TC": [64500]}}, {64500}, REGRAS)
    a = r["asns"]
    assert a["64500"]["classe"] == "pronto" and a["64502"]["classe"] == "sem_dados" and a["64502"]["total"] is None
    sp = r["por_uf"]["SP"]
    assert sp["asns"] == 2 and sp["asns_com_indice"] == 2 and sp["usuarios"] == 1000 and sp["media_ponderada_usuarios"] > a["64501"]["total"]
    assert r["por_operadora"]["11111111"]["asns"] == 2 and r["por_uf"]["RJ"]["classes"]["sem_dados"] == 1 and r["brasil"]["asns"] == 3
    assert sp["cobertura_pilares"]["anti_spoofing"] == 1
    assert r["por_faixa_porte"]["ate_1000"]["asns"] == 2 and r["por_faixa_porte"]["sem_usuarios"]["asns"] == 1       # 900 e 100 usuários; 0 = sem estimativa
    assert a["64500"]["faixa_porte"] == "ate_1000" and a["64500"]["faixa_acessos_sici"] == "ate_1000" and a["64502"]["faixa_acessos_sici"] is None


def test_agregar_sem_usuarios_cai_na_media_simples():
    asns = {"1": {"total": 80.0, "classe": "pronto", "pilares": {}, "usuarios": 0}, "2": {"total": 40.0, "classe": "atrasado", "pilares": {}, "usuarios": 0}}
    assert agregar(asns, {"1": "X", "2": "X"})["X"]["media_ponderada_usuarios"] == 60.0


def test_servico_blocos_por_operadora_uf_e_asn():
    from api.services import prontidao as s
    agg = {"asns": 2, "asns_com_indice": 1, "classes": {"pronto": 1, "em_progresso": 0, "atrasado": 0, "sem_dados": 1}, "media_ponderada_usuarios": 90.0, "mediana": 90.0, "usuarios": 10,
           "cobertura_pilares": {"filtragem": 1, "anti_spoofing": 0, "coordenacao": 2, "validacao_global": 1}}
    doc = {"snapshot_date": "2026-11-02", "natureza": "indice_composto", "regras": {"versao": 1}, "fontes": {}, "limites": "x", "brasil": agg, "por_uf": {"SP": agg}, "por_faixa_porte": {"ate_1000": agg}, "por_operadora": {"11111111": agg},
           "asns": {"64500": {"total": 90.0, "classe": "pronto", "pilares": {}, "pilares_sem_dado": [], "usuarios": 10, "uf": "SP"}}}
    assert s.bloco_operadora(doc, "11111111000111")["raiz"] == "11111111" and s.bloco_operadora(doc, "22222222000122") is None
    assert s.bloco_uf(doc, "SP")["uf"] == "SP" and s.bloco_uf(doc, "RJ") is None and s.bloco_asn(doc, 64500)["comparacao_uf"] == agg and s.bloco_asn(doc, 1) is None
    linhas = s.linhas(doc)
    assert [(x["tipo"], x["recorte"]) for x in linhas] == [("brasil", "BR"), ("uf", "SP"), ("porte", "ate_1000")] and not any("asn" in x or "cnpj" in x for x in linhas)
    with pytest.raises(s.ProntidaoErro):
        s.resumo(doc, "XX")


def test_agregar_medicoes_por_componente_media_simples_e_ponderada():
    def a(rov, usuarios, aspa=False):
        comps = {"rov": {"valor": rov, "peso": 3, "detalhe": None}} if rov is not None else {}
        pil = {"filtragem": {"score": rov, "peso": 25, "componentes": comps}} if comps else {}
        if aspa:
            pil["validacao_global"] = {"score": 100.0, "peso": 30, "componentes": {"aspa": {"valor": 100.0, "peso": 1, "detalhe": None}}}
        return {"total": 50.0, "classe": "em_progresso", "pilares": pil, "usuarios": usuarios}
    asns = {"1": a(100.0, 900), "2": a(0.0, 100, aspa=True), "3": a(None, 50)}
    m = agregar(asns, {"1": "X", "2": "X", "3": "X"})["X"]["medicoes"]
    assert m["rov"]["asns"] == 2 and m["rov"]["media"] == 50.0 and m["rov"]["media_ponderada_usuarios"] == 90.0     # 3º ASN sem ROV fica fora
    assert m["aspa"]["asns"] == 1 and m["spoofer"]["asns"] == 0 and m["spoofer"]["media"] is None
