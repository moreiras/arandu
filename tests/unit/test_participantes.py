# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tabela única de participantes do PTT (PT-24 / IXP-E5.5): união das fontes, família sem coleta, rejeição com denominador, idade da coleta, nome vazio e CDNs."""
import pytest

from api.services import participantes as p

SNAP = "2026-11-22"


def _ixp(v6_ok=True):
    return {"v4": {"coleta": "ok", "asn_direct": [100, 200], "br_asns_origin": [100, 200, 300]},
            "v6": {"coleta": "ok" if v6_ok else "vazia", "asn_direct": [100] if v6_ok else [], "br_asns_origin": [100, 300] if v6_ok else []}}


def _rs(extra=()):
    base = [{"asn": 100, "nome": "Rede Cem", "cadastrado": True, "sessoes": 2, "up": 2, "down": 0},
            {"asn": 200, "nome": "", "cadastrado": True, "sessoes": 1, "up": 0, "down": 1, "rs_incerto": 0},
            {"asn": 400, "nome": "Cadastrada sem sessão", "cadastrado": True, "sessoes": 0, "up": 0, "down": 0, "cadastrado_sem_sessao": True},
            {"asn": 500, "nome": "Só sessão", "cadastrado": False, "sessoes": 1, "up": 1, "down": 0}, *extra]
    return {"resumo": {"rs": 1, "rs_consultados": 1}, "membros": base}


def _asns_rs():
    return {"asns": {"100": {"ixps": {"sp": {"lista": [{"estado": "up", "recebidas": 80, "filtradas": 20}, {"estado": "up", "recebidas": 20, "filtradas": 0}]}}},
                     "500": {"ixps": {"sp": {"lista": [{"estado": "up", "recebidas": 0, "filtradas": 0}]}}},
                     "200": {"ixps": {"sp": {"lista": [{"estado": "down", "recebidas": 0, "filtradas": 0}]}}}}}


def _pol():
    return {"asns": {"100": {"ixps": {"sp": {"rejeicoes": {"rotas": 20, "coletado_ate": "2026-11-12T10:00:00Z", "herdado": True, "contagem": "exata"}}}}}}


def _cdns():
    return {"cdns": [{"name": "CDN Alfa", "asns": [100, 999], "ixbr": ["sp"]}, {"name": "CDN Beta", "asns": [200], "ixbr": ["rj"]}]}


def _base(v6_ok=True, rs=True):
    nomes = {"100": {"name": "Nome do ASN 100", "uf": "SP"}, "200": {"name": "Nome do ASN 200", "uf": "RJ"}, "300": {"name": "Só origina", "uf": None}, "400": {"name": "Quatro", "uf": "SP"}}
    return p.montar(SNAP, "sp", _ixp(v6_ok), {100, 200, 400}, _rs() if rs else None, _asns_rs(), _pol(), _cdns(), lambda asns: {k: v for k, v in nomes.items() if int(k) in asns},
                    lambda a: a != 500)


def _linha(base, asn):
    return next(l for l in base["linhas"] if l["asn"] == asn)


def test_linhas_sao_a_uniao_de_cadastro_looking_glass_e_sessoes_sem_incluir_so_originadores():
    b = _base()
    assert [l["asn"] for l in b["linhas"]] == [100, 200, 400, 500]          # 300 só origina: é coluna, não linha
    assert _linha(b, 500)["membro"] is False and _linha(b, 500)["sessao_rs_sem_cadastro"] is True
    c = p.contagens(b["linhas"], b["familias"])
    assert c["todos"] == 4 and c["sessao-sem-cadastro"] == 1 and c["membro-sem-sessao-rs"] == 1


def test_direto_membro_e_sessao_rs_sao_colunas_distintas():
    b = _base()
    l400 = _linha(b, 400)
    assert l400["membro"] is True and l400["sessao_rs"] == {"sessoes": 0, "up": 0, "down": 0, "incertas": 0} and l400["cadastrado_sem_sessao_rs"] is True
    assert l400["direto"] == {"v6": False, "v4": False}
    l200 = _linha(b, 200)
    assert l200["direto"] == {"v6": False, "v4": True} and l200["sessao_rs"]["down"] == 1


def test_familia_sem_coleta_nao_vira_ausencia_nem_entra_nos_filtros():
    b = _base(v6_ok=False)
    assert b["familias"] == {"v6": "vazia", "v4": "ok"}
    for l in b["linhas"]:
        assert l["direto"]["v6"] is None and l["originador"]["v6"] is None
    assert p.contagens(b["linhas"], b["familias"])["sem-v6"] == 0              # nenhum "sem IPv6" quando o IPv6 não foi coletado
    assert p.pagina(b, None, "sem-v6", None, "asn", False, 50, 0)["total"] == 0
    assert p.pagina(b, None, "sem-v4", None, "asn", False, 50, 0)["total"] == 2   # 400 e 500 não têm direto IPv4


def test_originador_so_para_asn_brasileiro():
    b = _base()
    assert _linha(b, 100)["originador"] == {"v6": True, "v4": True}
    assert _linha(b, 500)["originador"] == {"v6": None, "v4": None}           # fora do Brasil: a lista publicada não cobre


def test_rejeicao_tem_denominador_e_so_conta_sessoes_up():
    b = _base()
    assert _linha(b, 100)["rejeicao"] == {"filtradas": 20, "recebidas": 100, "pct": 20.0, "sessoes_up": 2}
    assert _linha(b, 500)["rejeicao"]["pct"] is None                           # 0 recebidas: sem percentual, nunca 0%
    assert _linha(b, 200)["rejeicao"] is None                                  # só sessão down: sem contador
    assert _linha(b, 400)["rejeicao"] is None


def test_idade_da_coleta_do_detalhe_e_heranca():
    d = _linha(_base(), 100)["rejeicao_detalhe"]
    assert d == {"rotas": 20, "coletado_ate": "2026-11-12T10:00:00Z", "idade_dias": 10, "herdado": True, "contagem": "exata"}
    assert _linha(_base(), 200)["rejeicao_detalhe"] is None


def test_nome_vazio_no_route_server_cai_para_o_nome_do_asn():
    b = _base()
    assert _linha(b, 200)["nome"] == "Nome do ASN 200"
    assert _linha(b, 100)["nome"] == "Rede Cem"
    assert _linha(b, 500)["nome"] == "Só sessão"


def test_cdns_so_dos_membros_do_proprio_ptt():
    b = _base()
    assert _linha(b, 100)["cdns"] == ["CDN Alfa"]
    assert _linha(b, 200)["cdns"] == []                                        # CDN Beta é membro do rj, não do sp
    assert p.contagens(b["linhas"], b["familias"])["com-cdn"] == 1


def test_sem_route_server_medido_sessao_e_nula_e_membro_sem_sessao_nao_e_afirmado():
    b = _base(rs=False)
    assert b["route_servers_medido"] is False
    assert all(l["sessao_rs"] is None for l in b["linhas"])
    assert p.contagens(b["linhas"], b["familias"])["membro-sem-sessao-rs"] == 0


def test_busca_ordem_filtro_e_pagina():
    b = _base()
    assert [l["asn"] for l in p.pagina(b, "AS200", "todos", None, "asn", False, 50, 0)["items"]] == [200]
    assert [l["asn"] for l in p.pagina(b, "cadastrada sem", "todos", None, "asn", False, 50, 0)["items"]] == [400]
    assert [l["asn"] for l in p.pagina(b, None, "todos", "SP", "asn", False, 50, 0)["items"]] == [100, 400]
    assert [l["asn"] for l in p.pagina(b, None, "todos", None, "asn", True, 2, 0)["items"]] == [500, 400]
    r = p.pagina(b, None, "todos", None, "asn", False, 2, 2)
    assert r["total"] == 4 and [l["asn"] for l in r["items"]] == [400, 500]
    assert [l["asn"] for l in p.pagina(b, None, "todos", None, "rejeicao", True, 1, 0)["items"]] == [100]
    assert p.pagina(b, None, "sem-direto", None, "asn", False, 50, 0)["total"] == 2        # 400 e 500
    assert p.pagina(b, None, "com-rejeicao", None, "asn", False, 50, 0)["total"] == 1


def test_filtro_e_ordem_invalidos_dao_400():
    b = _base()
    with pytest.raises(p.ParticipantesErro) as e:
        p.pagina(b, None, "x", None, "asn", False, 50, 0)
    assert e.value.status == 400
    with pytest.raises(p.ParticipantesErro):
        p.pagina(b, None, "todos", None, "x", False, 50, 0)


def test_colunas_de_empresa_usuarios_prefixos_e_alcancado_vem_dos_ganchos_e_ordenam():
    usuarios = {100: {"apnic": 1000, "ptt": 250.4}, 200: {"apnic": 500, "ptt": 0.0}}
    nomes = {"100": {"name": "Nome do ASN 100", "uf": "SP"}, "200": {"name": "Nome do ASN 200", "uf": "RJ"}, "400": {"name": "Quatro", "uf": "SP"}}
    b = p.montar(SNAP, "sp", _ixp(), {100, 200, 400}, _rs(), _asns_rs(), _pol(), _cdns(), lambda asns: {k: v for k, v in nomes.items() if int(k) in asns}, lambda a: a != 500,
                 empresa_de=lambda a: {"cnpj": "00000000000191", "nome": None} if a == 100 else None, usuarios_de=lambda a: usuarios.get(a, {"apnic": None, "ptt": None}),
                 prefixos={"v4": {"100": {"own_prefixes": 3, "third_prefixes": 1}}}, pdb_de=lambda a: {"portas_mbps": [10000], "instalacoes": None} if a == 100 else None,
                 alcancado={"v4": {"100": 77}})
    l100, l400 = _linha(b, 100), _linha(b, 400)
    assert l100["empresa"] == {"cnpj": "00000000000191", "nome": None} and l400["empresa"] is None
    assert (l100["usuarios_apnic"], l100["usuarios_ptt"]) == (1000, 250.4) and (l400["usuarios_apnic"], l400["usuarios_ptt"]) == (None, None)
    assert l100["prefixos"] == {"v6": None, "v4": {"own_prefixes": 3, "third_prefixes": 1}} and l400["prefixos"] == {"v6": None, "v4": None}
    assert l100["peeringdb"]["portas_mbps"] == [10000] and l100["sici_alcancado"] == {"v6": None, "v4": 77}
    r = p.pagina(b, None, "todos", None, "usuarios_ptt", True, 10, 0)
    assert [l["asn"] for l in r["items"]][:2] == [100, 200]                     # sem valor (-1) vai ao fim
    r = p.pagina(b, None, "todos", None, "usuarios_apnic", False, 10, 0)
    assert [l["asn"] for l in r["items"]][-2:] == [200, 100]
    assert [l["asn"] for l in p.pagina(b, None, "todos", None, "asn", False, 10, 0)["items"]] == [100, 200, 400, 500]      # a ordem padrão segue neutra


def test_estimativa_por_asn_e_a_unica_conta_do_total_do_ptt():
    """`ixp_estimated_users` soma `ixp_users_por_asn`: o total do PTT e a coluna não podem divergir (prefixos até /24 colapsados, fração limitada a 1)."""
    from api.services.ixp_potencial import IxpPotencialService

    class S:
        def asn_map(self, d):
            return {64496: {"is_br": True, "apnic_users": 1000, "space_v4": 8}, 64497: {"is_br": True, "apnic_users": 300, "space_v4": 2},
                    64498: {"is_br": False, "apnic_users": 999, "space_v4": 4}, 64499: {"is_br": True, "apnic_users": None, "space_v4": 4}}

        def _load_origin_prefixes(self, d, code, afi):
            return {"64496": ["192.0.2.0/24", "192.0.2.0/25", "198.51.100.0/23", "203.0.113.0/25", "2001:db8::/32"],        # 1 + (aninhado, não conta) + 2 = 3 de 8 /24
                    "64497": ["198.18.0.0/22"],                                                                          # 4 de 2: limitado a 1
                    "64498": ["192.0.2.0/24"], "64499": ["192.0.2.0/24"], "abc": ["192.0.2.0/24"]}

    svc = IxpPotencialService(S())
    por_asn = svc.ixp_users_por_asn("2026-11-22", "sp")
    assert set(por_asn) == {64496, 64497}
    assert por_asn[64496]["fracao"] == pytest.approx(3 / 8) and por_asn[64496]["estimado"] == pytest.approx(375)
    assert por_asn[64497]["fracao"] == 1.0 and por_asn[64497]["estimado"] == pytest.approx(300)
    est = svc.ixp_estimated_users("2026-11-22", "sp")
    assert est["estimated_users"] == round(sum(c["estimado"] for c in por_asn.values())) == 675 and est["contributing_asns"] == 2
    assert svc._ixp_user_contributions("2026-11-22", "sp") == {64496: pytest.approx(3 / 8), 64497: 1.0}
