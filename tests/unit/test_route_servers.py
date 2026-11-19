# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Route servers do IX.br: dias no estado, uso do limite, cadastro × sessão e o que não se afirma."""
from products.route_servers import build as rs

REF = "2026-10-31T06:00:00+00:00"


def _s(ixp, asn, ip, estado="up", dias_atras="2026-10-30 10:00:00", recebidas=10, limite=100, erro="", rs_id=None, afi="v4"):
    return {"rs": rs_id or f"{ixp.upper()}-rs1-{afi}", "ixp": ixp, "afi": afi, "neighbor_ip": ip, "asn": asn, "estado": estado, "state_changed": dias_atras,
            "last_error": erro, "rotas": {"recebidas": recebidas, "aceitas": recebidas, "filtradas": 0, "exportadas": 5}, "import_limit": limite}


def _rs(ixp, consultado=True, estado="READY", afi="v4", n="rs1", vizinhos_em="2026-10-31T05:50:00+00:00"):
    return {"rs": f"{ixp.upper()}-{n}-{afi}", "ixp": ixp, "numero": n, "afi": afi, "estado_rotas": estado, "vizinhos_em": vizinhos_em if consultado else None, "consultado": consultado,
            "erro": None if consultado else "x", "sessoes": 0, "sessoes_up": 0}


def test_dias_desde():
    assert rs.dias_desde("2026-10-23 07:34:44", REF) == 7
    assert rs.dias_desde("2026-10-31 07:00:00", REF) == 0
    assert rs.dias_desde("", REF) is None and rs.dias_desde("lixo", REF) is None


def test_uso_do_limite_e_sem_limite():
    assert rs.uso_limite(_s("sp", 1, "1", recebidas=90)) == 0.9
    assert rs.uso_limite(_s("sp", 1, "1", limite=None)) is None and rs.uso_limite(_s("sp", 1, "1", limite=0)) is None


def test_membro_derrubado_so_com_todas_as_sessoes_caidas_ha_n_dias():
    ref = REF
    caida = rs.sessao_compacta(_s("sp", 1, "a", "down", "2026-10-20 00:00:00"), ref)
    no_ar = rs.sessao_compacta(_s("sp", 1, "b"), ref)
    nova = rs.sessao_compacta(_s("sp", 1, "c", "down", "2026-10-29 00:00:00"), ref)
    assert rs.resumo_membro([caida])["membro_down"] is True and rs.resumo_membro([caida])["max_dias_down"] == 11
    assert rs.resumo_membro([caida, no_ar])["membro_down"] is False          # uma sessão no ar: não está down
    assert rs.resumo_membro([nova])["membro_down"] is False and rs.resumo_membro([nova])["todas_down"] is True
    assert rs.resumo_membro([])["membro_down"] is False


def test_perto_do_limite_usa_so_sessao_no_ar():
    ref = REF
    assert rs.resumo_membro([rs.sessao_compacta(_s("sp", 1, "a", recebidas=80), ref)])["perto_do_limite"] is True
    assert rs.resumo_membro([rs.sessao_compacta(_s("sp", 1, "a", recebidas=79), ref)])["perto_do_limite"] is False
    assert rs.resumo_membro([rs.sessao_compacta(_s("sp", 1, "a", "down", recebidas=99), ref)])["perto_do_limite"] is False


def test_cadastro_x_sessao_e_ixp_desconhecido():
    doc = {"generated_at": REF, "rs": [_rs("sp"), _rs("rr-old")],
           "sessoes": [_s("sp", 64496, "1"), _s("sp", 64496, "2", afi="v6"), _s("sp", 64999, "3"), _s("rr-old", 64496, "9")]}
    ixps, asns = rs.calcular(doc, {"sp": {64496: "A", 64497: "B"}}, {"sp": "São Paulo"})
    r = ixps["sp"]["resumo"]
    assert (r["cadastrados"], r["cadastrados_com_sessao"], r["cadastrados_sem_sessao"], r["sessao_sem_cadastro"], r["sessoes"]) == (2, 1, 1, 1, 3)
    m = {x["asn"]: x for x in ixps["sp"]["membros"]}
    assert m[64497]["cadastrado_sem_sessao"] is True and "cadastrado_sem_sessao" not in m[64496] and m[64999]["cadastrado"] is False
    assert "rr-old" not in ixps and list(asns) == ["64496", "64999"]           # PTT fora do config não entra
    assert asns["64496"]["ixps"]["sp"]["sessoes"] == 2 and asns["64496"]["total"]["ixps"] == 1


def test_sem_rs_consultado_nao_se_afirma_cadastrado_sem_sessao():
    doc = {"generated_at": REF, "rs": [_rs("sp", consultado=False)], "sessoes": []}
    ixps, asns = rs.calcular(doc, {"sp": {64496: "A"}}, {"sp": "São Paulo"})
    assert ixps["sp"]["resumo"]["cadastrados_sem_sessao"] == 0 and ixps["sp"]["resumo"]["rs_consultados"] == 0 and asns == {}
    assert "cadastrado_sem_sessao" not in ixps["sp"]["membros"][0]


def test_estado_do_cache_de_rotas_nao_torna_a_sessao_incerta_mas_vizinhos_velhos_sim():
    ses = [_s("sp", 64496, "1", "down", "2026-09-01 00:00:00")]
    busy = {"generated_at": REF, "rs": [_rs("sp", estado="BUSY")], "sessoes": ses}                       # rotas BUSY, vizinhos de 10 min: sessão vale
    ixps, _ = rs.calcular(busy, {"sp": {64496: "A"}}, {"sp": "São Paulo"})
    assert ixps["sp"]["membros"][0]["membro_down"] is True and ixps["sp"]["resumo"]["rs_rotas_prontas"] == 0 and ixps["sp"]["resumo"]["rs_vizinhos_atuais"] == 1
    velho = {"generated_at": REF, "rs": [_rs("sp", vizinhos_em="2026-10-29T06:00:00+00:00")], "sessoes": ses}   # vizinhos de 2 dias: incerta
    ixps, asns = rs.calcular(velho, {"sp": {64496: "A"}}, {"sp": "São Paulo"})
    m = ixps["sp"]["membros"][0]
    assert m["todas_down"] is True and m["membro_down"] is False and m["rs_incerto"] == 1 and "max_dias_down" not in m
    assert asns["64496"]["ixps"]["sp"]["lista"][0]["rs_incerto"] is True
    assert ixps["sp"]["resumo"]["membros_down"] == 0 and ixps["sp"]["resumo"]["membros_com_rs_incerto"] == 1 and ixps["sp"]["resumo"]["rs_vizinhos_atuais"] == 0


def test_vizinhos_sem_cached_at_ou_nao_consultados_sao_incertos():
    doc = {"generated_at": REF, "rs": [_rs("sp", vizinhos_em=None), _rs("sp", n="rs2"), _rs("sp", n="rs3", consultado=False)]}
    assert rs.vizinhos_incertos(doc) == {"SP-rs1-v4", "SP-rs3-v4"}


def test_tempo_de_queda_e_ranking_contam_so_sessao_de_rs_pronto():
    certa = rs.sessao_compacta(_s("sp", 1, "a", "down", "2026-10-20 00:00:00"), REF)
    incerta = rs.sessao_compacta(_s("sp", 1, "b", "down", "2026-06-01 00:00:00"), REF, incerto=True)
    r = rs.resumo_membro([certa, incerta])
    assert (r["down"], r["down_certo"], r["max_dias_down"]) == (2, 1, 11)          # a queda de 5 meses é de um RS BUSY e não entra
    assert r["membro_down"] is False                                                  # há sessão incerta: não se afirma
    assert "max_dias_down" not in rs.resumo_membro([incerta]) and rs.resumo_membro([incerta])["down_certo"] == 0
