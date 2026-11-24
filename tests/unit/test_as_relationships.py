# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0/T2 — algoritmo ARC v1: cenários plantados (rampa de RS, vazamento de membro, VP parcial, poisoning, irmãos, ASPA)."""
import pytest

from products.as_relationships import arc, config as cf
from products.as_relationships.decisao import decidir
from products.as_relationships.evidencias import Evidencias, calcular_clique
from products.as_relationships.propagacao import votar_caminho
from products.as_relationships.sanitiza import sanitizar

CFG = cf.carregar()


def test_config_padrao_confere_com_o_arquivo():
    base = cf.Config()
    assert cf.carregar() == base


@pytest.mark.parametrize("caminho,esperado", [
    ([5, 5, 5, 7, 9], (5, 7, 9)),                        # prepend
    ([5, 26162, 7], (5, 7)),                             # ASN de route server sai
    ([5, 7, 5], None),                                   # laço (poisoning/erro)
    ([5, 23456, 7], None),                               # AS_TRANS
    ([5, 64512, 7], None),                               # privado
    ([5, 4200000001, 7], None),                          # privado 32 bits
    ([5], None), ([], None),
    ([5, 5], None),                                      # só um salto após comprimir
    ([64496, 64497], (64496, 64497)),                    # documentação passa (o sintético os usa)
])
def test_sanitizacao(caminho, esperado):
    assert sanitizar(caminho, CFG) == esperado


def _rotulo_de(tab):
    return lambda x, y: tab.get((x, y))


def test_propagacao_depois_de_descida_tudo_desce_e_antes_de_subida_tudo_sobe():
    # 1 -D-> 2 -?-> 3 -?-> 4   : depois de 'D' tudo é 'D'
    assert votar_caminho((1, 2, 3, 4), False, _rotulo_de({(1, 2): "D"})) == [(1, (2, 3)), (2, (3, 4))]
    # 1 -?-> 2 -?-> 3 -U-> 4   : antes de 'U' tudo é 'U' (o da direita é provedor)
    assert votar_caminho((1, 2, 3, 4), False, _rotulo_de({(3, 4): "U"})) == [(0, (2, 1)), (1, (3, 2))]
    # par no ápice separa: 1 -?-> 2 -P-> 3 -?-> 4
    assert votar_caminho((1, 2, 3, 4), False, _rotulo_de({(2, 3): "P"})) == [(0, (2, 1)), (2, (3, 4))]


def test_propagacao_viola_valley_free_nao_vota():
    # descida seguida de subida (vale): vazamento ou poisoning
    assert votar_caminho((1, 2, 3, 4), False, _rotulo_de({(1, 2): "D", (3, 4): "U"})) is None
    assert votar_caminho((1, 2, 3, 4), False, _rotulo_de({(1, 2): "P", (3, 4): "P"})) is None


def test_elo_do_vp_nao_vota_quando_o_primeiro_as_e_o_proprio_vp():
    r = votar_caminho((1, 2, 3, 4), True, _rotulo_de({(3, 4): "U"}))
    assert r == [(1, (3, 2))]                              # o elo 0 (VP→1º AS) ficou de fora
    assert votar_caminho((1, 2, 3, 4), False, _rotulo_de({(3, 4): "U"}))[0] == (0, (2, 1))


def test_clique_acha_o_topo_e_ignora_quem_nao_e_adjacente_a_todos():
    adj = {1: {2, 3, 10}, 2: {1, 3, 11}, 3: {1, 2}, 10: {1}, 11: {2}, 99: {1}}
    grau = {1: 50, 2: 40, 3: 30, 10: 5, 11: 4, 99: 1}
    assert calcular_clique(adj, grau, 10, 3) == frozenset({1, 2, 3})
    assert calcular_clique(adj, grau, 10, 4) == frozenset()          # abaixo do mínimo: sem clique confiável


# ── mundo plantado ─────────────────────────────────────────────────────────────
#   topo (clique): 1, 2, 3        trânsitos: 10 (cliente de 1), 11 (cliente de 2)
#   acesso: 100 (cliente de 10 e de 11: multihomed), 101 (cliente só de 10)
#   VPs: 500 (par de 1), 501 (par de 2)       RS: PTT 'za' (membros 10, 11, 100) e 'zb' (membros 10, 100)
def _coletores():
    cam = []
    for _ in range(1):
        cam += [((500, 1, 10, 100), 2, True), ((500, 1, 10, 101), 2, True), ((500, 1, 2, 11, 100), 2, True),
                ((501, 2, 11, 100), 1, True), ((501, 2, 1, 10, 100), 1, True), ((501, 2, 1, 10, 101), 1, True),
                ((500, 1, 3, 2, 11), 1, True), ((500, 3, 1, 10), 1, True), ((501, 3, 2, 11), 1, True)]
    return lambda: iter(cam)


RS = [((10, 100), "za"), ((10, 101), "za"), ((11, 100), "za"), ((10, 100), "zb"), ((100,), "za")]


def _por_elo(vs):
    return {(v.a, v.b) if v.tipo == "p2c" else (min(v.a, v.b), max(v.a, v.b), v.tipo): v for v in vs}


def test_mundo_plantado_recupera_a_hierarquia():
    vs, diag = arc.inferir(RS, _coletores(), [], None, {}, CFG)
    por = {(v.a, v.b): v for v in vs if v.tipo == "p2c"}
    assert diag["clique"] == [1, 2, 3]
    for par in [(1, 10), (2, 11), (10, 100), (11, 100), (10, 101)]:
        assert par in por, par
        assert por[par].nivel in ("confirmado", "provavel"), (par, por[par].nivel, por[par].p)
    assert por[(10, 100)].evid["rs"]["ab"]["ptts"] == 2
    pares = {(v.a, v.b) for v in vs if v.tipo == "p2p"}
    assert {(1, 2), (1, 3), (2, 3)} <= pares
    assert all(v.nivel in ("confirmado", "provavel") for v in vs if v.tipo == "p2p" and (v.a, v.b) in {(1, 2), (1, 3), (2, 3)})


def test_sem_coletores_funciona_so_com_rs_aspa_e_caida():
    vs, diag = arc.inferir(RS, None, [{"customer": 101, "providers": [10]}], ([[10, 101]], [[100, 101]]), {}, CFG)
    por = {(v.a, v.b): v for v in vs if v.tipo == "p2c"}
    assert por[(10, 101)].nivel == "declarado" and por[(10, 101)].p > 0.99
    assert (10, 100) in por and por[(10, 100)].nivel != "declarado"
    assert "clique" not in diag
    par = [v for v in vs if (v.a, v.b) == (100, 101)]
    assert par and par[0].tipo == "p2p" and par[0].nivel == "possivel"          # só o CAIDA: nunca passa de 'possível'


def test_aspa_nao_e_veto_mas_a_disputa_aparece():
    # ASPA declara 100→11 como provedor, mas 4 membros/2 PTTs mostram a rampa 100→11 invertida (11 abaixo de 100)
    rs = [((100, 11), "za"), ((100, 11), "zb"), ((200, 100, 11), "za"), ((201, 100, 11), "zb")]
    vs, _ = arc.inferir(rs, None, [{"customer": 11, "providers": [100]}], None, {}, CFG)
    v = next(x for x in vs if {x.a, x.b} == {11, 100})
    assert v.tipo == "p2c" and (v.a, v.b) == (100, 11) and v.nivel == "declarado"
    assert v.evid["fontes"] == ["aspa", "rs"]


def test_aspa_contraria_a_rs_fraca_gera_disputa_visivel():
    rs = [((11, 100), "za")]                                    # rampa fraca diz 11 provedor de 100
    vs, _ = arc.inferir(rs, None, [{"customer": 11, "providers": [100]}], None, {}, CFG)
    v = next(x for x in vs if {x.a, x.b} == {11, 100})
    assert (v.a, v.b) == (100, 11) and v.nivel == "declarado"
    assert (v.evid["contra"]["tipo"], v.evid["contra"]["a"], v.evid["contra"]["b"]) == ("p2c", 11, 100)   # a contrária fica registrada


def test_aspa_negativo_desfavorece_mas_nao_anula():
    ev = Evidencias()
    ev.definir_aspa([{"customer": 50, "providers": [60]}])       # 50 lista 60, não lista 70
    ev.rs_membros[(70, 50)] = {1, 2, 3}
    ev.rs_ptts[(70, 50)] = {"za", "zb"}
    v = decidir(50, 70, ev, CFG, {})
    assert v.tipo == "p2c" and (v.a, v.b) == (70, 50)            # rampa forte vence o negativo fraco
    assert v.evid["aspa"]["ba"] == "nao_lista" and v.p < 0.99


def test_irmaos_so_chegam_a_possivel_e_nunca_ganham_de_aspa():
    ev = Evidencias()
    ev.grupo = {1: "12345678", 2: "12345678"}
    ev.rs_membros[(1, 2)] = {9}
    ev.rs_ptts[(1, 2)] = {"za"}
    v = decidir(1, 2, ev, CFG, {})
    assert v.nivel in ("possivel", "sem_classificacao") or v.tipo != "s2s"
    ev2 = Evidencias()
    ev2.grupo = {1: "x", 2: "x"}
    assert decidir(1, 2, ev2, CFG, {}).tipo == "s2s" and decidir(1, 2, ev2, CFG, {}).nivel == "possivel"
    ev2.definir_aspa([{"customer": 2, "providers": [1]}])
    assert decidir(1, 2, ev2, CFG, {}).tipo == "p2c"


def test_vazamento_de_membro_nao_vira_confirmado():
    # um único membro (7) anuncia ao RS uma rota em que o par 20→21 aparece invertido; os demais mostram 21→20
    rs = [((21, 20), "za"), ((22, 21, 20), "za"), ((23, 21, 20), "zb"), ((7, 20, 21), "za")]
    vs, _ = arc.inferir(rs, None, [], None, {}, CFG)
    v = next(x for x in vs if {x.a, x.b} == {20, 21})
    assert (v.a, v.b) == (21, 20) and v.nivel in ("provavel", "confirmado")
    assert (v.evid["contra"]["a"], v.evid["contra"]["b"], v.evid["contra"]["fontes"]) == (20, 21, ["rs"])   # o vazamento é evidência contrária


def test_poisoning_e_laco_nao_contaminam():
    col = [((500, 1, 10, 1, 100), 1, True)] * 5 + [((500, 1, 10, 100), 1, True)]
    vs, diag = arc.inferir([], lambda: iter(col), [], None, {}, CFG)
    assert diag["col_descartados"] == 5 and diag["col_caminhos"] == 1


def test_elo_so_visto_sem_nenhuma_evidencia_fica_sem_classificacao():
    col = [((500, 7, 8), 1, True)]
    vs, _ = arc.inferir([], lambda: iter(col), [], None, {}, CFG)
    assert {(v.a, v.b): v.tipo for v in vs}[(7, 8)] == "sem_classificacao"


def test_filtro_de_elos_e_determinismo():
    a = arc.inferir(RS, _coletores(), [], None, {}, CFG, so_elos=lambda x, y: 100 in (x, y))[0]
    b = arc.inferir(RS, _coletores(), [], None, {}, CFG, so_elos=lambda x, y: 100 in (x, y))[0]
    assert all(100 in (v.a, v.b) for v in a) and a == b


# ── fragmento por ASN ────────────────────────────────────────────────────────

def _linha(a, b, tipo="p2c", nivel="provavel", p=0.9, afi=("v4",), n_vps=0, n_ptt=0):
    return {"a": a, "b": b, "tipo": tipo, "nivel": nivel, "p": p, "afi": list(afi), "n_vps": n_vps, "n_ptt": n_ptt}


def test_por_asn_agrupa_papeis_e_cria_os_dois_lados():
    from products.as_relationships.por_asn import por_asn

    doc = por_asn([_linha(10, 100), _linha(11, 100, nivel="confirmado"), _linha(100, 200), _linha(100, 300, "p2p", "possivel"),
                   _linha(100, 400, "sem_classificacao", "sem_classificacao", 0.4)], CFG, {"v4": True})
    d = doc[100]
    assert [x["asn"] for x in d["provedores"]] == [11, 10]                     # confirmado antes de provavel
    assert [x["asn"] for x in d["clientes"]] == [200] and [x["asn"] for x in d["pares"]] == [300]
    assert [x["asn"] for x in d["sem_classificacao"]] == [400]
    assert doc[10]["clientes"][0]["asn"] == 100 and doc[200]["provedores"][0]["asn"] == 100
    assert d["n_provedores"] == {"v4": 1, "v6": 0}                              # só confirmado conta em n_provedores
    assert d["n_provedores_provavel"] == {"v4": 2, "v6": 0}                     # provável ou superior: 10 e 11


def test_n_provedores_provavel_exclui_irmaos_e_possiveis():
    """ASN-E4: provável ou superior, sem irmão inferido; `possivel` não conta (a frase diz quantos são só possíveis)."""
    from products.as_relationships.por_asn import por_asn

    doc = por_asn([_linha(174, 13357), _linha(3356, 13357), _linha(14840, 13357, nivel="possivel"), _linha(28158, 13357, nivel="provavel"),
                   _linha(28158, 13357, "s2s", "possivel")], CFG, {"v4": True})
    d = doc[13357]
    assert d["n_provedores_provavel"] == {"v4": 2, "v6": 0} and d["n_provedores"] == {"v4": 0, "v6": 0}


def test_single_homed_so_com_visibilidade_e_sem_provedor_fraco():
    from products.as_relationships.por_asn import por_asn

    um = [_linha(10, 100, n_vps=5)]
    assert por_asn(um, CFG, {"v4": True})[100]["single_homed"] == {"v4": True, "v6": None}
    assert por_asn([_linha(10, 100, n_vps=1, n_ptt=1)], CFG, {"v4": True})[100]["single_homed"]["v4"] is None   # pouca visibilidade
    com_fraco = um + [_linha(11, 100, nivel="possivel", p=0.55)]
    assert por_asn(com_fraco, CFG, {"v4": True})[100]["single_homed"]["v4"] is None                           # há candidato fraco
    dois = um + [_linha(11, 100)]
    d = por_asn(dois, CFG, {"v4": True})[100]
    assert d["multihomed"]["v4"] is True and d["single_homed"]["v4"] is False


def test_por_asn_limita_listas_longas_e_registra_o_total():
    from products.as_relationships.por_asn import por_asn

    linhas = [_linha(1, 1000 + i, p=0.9 - i / 10_000) for i in range(260)]
    d = por_asn(linhas, CFG, {})[1]
    assert len(d["clientes"]) == 200 and d["clientes_total"] == 260 and d["clientes"][0]["asn"] == 1000


def test_por_asn_inclui_nome_quando_conhecido():
    from products.as_relationships.por_asn import por_asn

    d = por_asn([_linha(10, 100)], CFG, {}, {10: "Provedor Exemplo", 100: "X" * 200})
    assert d[100]["provedores"][0]["nome"] == "Provedor Exemplo" and len(d[10]["clientes"][0]["nome"]) == 80
    assert "nome" not in por_asn([_linha(10, 100)], CFG, {})[100]["provedores"][0]
