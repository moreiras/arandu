# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0/T2 — ARC v2: Naive Bayes, votos de contexto, irmãos, ciclos, relação complexa, histerese, calibração e produto `transito`."""
import dataclasses

import pytest

from api.services import transito as svc
from products.as_relationships import config as cf, estabilidade, refino, restricoes
from products.as_relationships.decisao import Veredito
from products.as_relationships.evidencias import Evidencias
from products.as_relationships.validacao import _ece, calibracao_v2, ece_por_estrato
from products.transito import build as tr

CFG = cf.carregar()


# ── votos de contexto ─────────────────────────────────────────────────────────────────────────────────────────────
def _rot(tab):
    return lambda x, y: tab.get((x, y))


def test_voto_de_todos_os_elos_independe_do_proprio_rotulo():
    # 1 -?-> 2 -D-> 3 -?-> 4: depois de D tudo desce; o elo rotulado (2,3) também vota, mas pelos OUTROS elos (nenhum) → sem voto
    r = refino.votar_todos((1, 2, 3, 4), False, _rot({(2, 3): "D"}))
    assert r == [(3, 4)]                                              # só o elo depois do D recebe voto; o próprio (2,3) e o anterior (1,2) não
    # um 'U' à direita faz tudo antes subir, inclusive um elo já rotulado 'U' (voto pelos outros elos: nenhum além do da direita)
    r = refino.votar_todos((1, 2, 3, 4), False, _rot({(2, 3): "U", (3, 4): "U"}))
    assert (3, 2) in r and (2, 1) in r and (4, 3) not in r


def test_voto_viola_valley_free_nao_vota_e_vp_nao_vota_no_primeiro_elo():
    assert refino.votar_todos((1, 2, 3, 4), False, _rot({(1, 2): "D", (3, 4): "U"})) is None
    assert refino.votar_todos((1, 2, 3), True, _rot({(2, 3): "U"})) == []      # o elo VP→1º AS (índice 0) não vota
    assert refino.votar_todos((1, 2, 3), False, _rot({})) == []


# ── Naive Bayes ───────────────────────────────────────────────────────────────────────────────────────────────────
def _carac(**kw):
    base = {f: "0" for f in refino.CARACTERISTICAS}
    base.update(kw)
    return base


def test_nb_aprende_com_espelho_e_a_temperatura_achata_a_posterior():
    nb = refino.NaiveBayes(1.0)
    amostras = [(_carac(rs="ab"), _carac(rs="ba"), "ab")] * 30 + [(_carac(rs="0"), _carac(rs="0"), "pp")] * 30
    nb.treinar(amostras)
    p = refino.posterior(nb.escores(_carac(rs="ab")))
    assert p["ab"] > 0.8 and abs(sum(p.values()) - 1) < 1e-9
    q = refino.posterior(nb.escores(_carac(rs="ba")))
    assert q["ba"] > 0.8                                              # o espelho foi aprendido: a simetria vale sem rótulo "ba" explícito
    esc = nb.escores(_carac(rs="ab"))
    assert refino.posterior(esc, 8.0)["ab"] < p["ab"]                 # temperatura alta achata


def test_ablacao_de_caracteristica_nao_quebra_e_nb_sem_a_caracteristica_ignora_a_diferenca():
    nb = refino.NaiveBayes(1.0, sem=("rs",))
    nb.treinar([(_carac(rs="ab"), _carac(rs="ba"), "ab")] * 20 + [(_carac(rs="0"), _carac(rs="0"), "pp")] * 20)
    assert refino.posterior(nb.escores(_carac(rs="ab")))["ab"] == pytest.approx(refino.posterior(nb.escores(_carac(rs="0")))["ab"])


def test_caracteristicas_orientadas_e_espelhadas():
    ev = Evidencias()
    ev.adicionar_rs((10, 20), "sp")
    ev.adicionar_rs((10, 30), "sp")
    ev.adicionar_rs((20, 30), "sp")
    ev.aspa_pos = {(10, 20)}
    ev.clique = frozenset({10})
    ctx = refino.Contexto(ev, {10: {20}, 20: {10}}, {10: 40, 20: 2}, {10: "A"}, {(10, 20): "nao"})
    f = ctx.caracteristicas(10, 20, {(10, 20): [9, 3]})
    g = ctx.caracteristicas(20, 10, {(10, 20): [9, 3]})
    assert f["rs"] == "ab" and g["rs"] == "ba" and f["aspa"] == "ab" and g["aspa"] == "ba"
    assert f["tripla"] == "ab+" and g["tripla"] == "ba+"
    assert f["dist_clique"] == "<0" and g["dist_clique"] == ">0"
    assert f["politica"] == "A/-" and f["restricao"] == "nao/-"
    assert f["coloc"] == "1"                                           # os dois estão no PTT 'sp'


def test_distancia_ao_clique():
    assert refino.distancias_ao_clique({1: {2}, 2: {1, 3}, 3: {2}, 9: set()}, [1]) == {1: 0, 2: 1, 3: 2}


# ── irmãos, ciclos e complexas ────────────────────────────────────────────────────────────────────────────────────
def _linha(a, b, tipo="p2c", p=0.9, nivel="provavel", afi=("v4",), **kw):
    return {"a": a, "b": b, "tipo": tipo, "p": p, "nivel": nivel, "afi": list(afi), "evid": {}, "n_vps": 3, "n_ptt": 0, **kw}


def test_grupos_de_irmaos_une_cnpj_e_organizacao_e_ignora_isolados():
    g = restricoes.grupos_de_irmaos({1: "c1", 2: "c1", 3: "c9", 5: "c5"}, {2: "o1", 4: "o1", 3: "o9"})
    assert g == {1: 1, 2: 1, 4: 1}                                     # 1~2 (CNPJ), 2~4 (organização)


def test_irmaos_viram_s2s_com_nivel_pelas_duas_origens_e_aspa_nao_e_desfeito():
    ls = [_linha(1, 2), _linha(2, 4), _linha(7, 8, nivel="declarado")]
    n = restricoes.aplicar_irmaos(ls, {1: "c1", 2: "c1", 7: "c7", 8: "c7"}, {2: "o1", 4: "o1", 1: "o1", 7: "o7", 8: "o7"})
    assert n == 2
    assert ls[0]["tipo"] == "s2s" and ls[0]["nivel"] == "provavel" and ls[0]["evid"]["irmaos"] == {"cnpj": True, "organizacao": True}
    assert ls[1]["tipo"] == "s2s" and ls[1]["nivel"] == "possivel" and ls[1]["evid"]["irmaos"] == {"cnpj": False, "organizacao": True}
    assert ls[2]["tipo"] == "p2c"                                      # declarado (ASPA) fica


def test_ciclo_p2c_rompe_o_elo_mais_fraco_e_nunca_o_declarado():
    ls = [_linha(1, 2, p=0.95, nivel="confirmado"), _linha(2, 3, p=0.9), _linha(3, 1, p=0.75), _linha(4, 5)]
    assert restricoes.quebrar_ciclos(ls, {}) == 1
    assert ls[2]["tipo"] == "sem_classificacao" and ls[2]["evid"]["restricao"] == "ciclo_p2c" and ls[0]["tipo"] == ls[1]["tipo"] == "p2c"
    ls = [_linha(1, 2, nivel="declarado"), _linha(2, 3, nivel="declarado"), _linha(3, 1, p=0.6)]
    assert restricoes.quebrar_ciclos(ls, {}) == 1 and ls[2]["tipo"] == "sem_classificacao"
    ls = [_linha(1, 2, nivel="declarado"), _linha(2, 1, nivel="declarado")]
    assert restricoes.quebrar_ciclos(ls, {}) == 0                       # nenhum elo removível: fica, sem laço infinito


def test_ciclo_com_irmaos_colapsados():
    # 1 e 11 são irmãos: 1 → 2 → 11 forma ciclo depois de colapsar os irmãos
    ls = [_linha(1, 2, p=0.9), _linha(2, 11, p=0.72)]
    assert restricoes.quebrar_ciclos(ls, {1: 1, 11: 1}) == 1 and ls[1]["tipo"] == "sem_classificacao"


def test_complexa_so_quando_v4_e_v6_divergem_com_forca():
    forte = [_linha(1, 2, p=0.9, afi=("v4",), afi_divergente=True), _linha(1, 2, tipo="p2p", p=0.85, afi=("v6",), afi_divergente=True)]
    out, n = restricoes.unir_complexas(forte + [_linha(5, 6)], CFG)
    assert n == 1 and len(out) == 2
    c = out[0]
    assert c["tipo"] == "complexa" and c["afi"] == ["v4", "v6"] and c["evid"]["complexa"]["subtipo"] == "hibrida" and c["p"] == 0.85
    fraca = [_linha(1, 2, p=0.9, afi=("v4",), afi_divergente=True), _linha(1, 2, tipo="p2p", p=0.6, nivel="possivel", afi=("v6",), afi_divergente=True)]
    out, n = restricoes.unir_complexas(fraca, CFG)
    assert n == 0 and len(out) == 2
    inversa = [_linha(1, 2, afi=("v4",), afi_divergente=True), _linha(2, 1, p=0.88, afi=("v6",), afi_divergente=True)]
    out, _ = restricoes.unir_complexas(inversa, CFG)
    assert out[0]["evid"]["complexa"]["subtipo"] == "inversa"


# ── histerese (E6) ────────────────────────────────────────────────────────────────────────────────────────────────
def _doc(linhas):
    return {"relacoes": linhas}


def test_estado_nasce_igual_a_proposta_e_estavel_nao_muda():
    novo = [_linha(1, 2)]
    out, mud, res = estabilidade.aplicar(novo, None, "2026-11-05", "2026-10-30", 2)
    assert out[0]["tipo"] == "p2c" and mud == [] and res["novos"] == 1
    out, mud, res = estabilidade.aplicar([_linha(1, 2, p=0.93)], _doc(out), "2026-11-06", "2026-10-30", 2)
    assert res["estaveis"] == 1 and out[0]["p"] == 0.93 and "pendente" not in out[0]


def test_mudanca_exige_duas_geracoes_de_evidencia_e_mesma_geracao_nao_conta():
    estado = [_linha(1, 2, tipo="p2c", p=0.9)]
    prop = lambda: [_linha(1, 2, tipo="p2p", p=0.8)]                    # noqa: E731
    d1, mud, res = estabilidade.aplicar(prop(), _doc(estado), "2026-11-05", "2026-10-30", 2)
    assert d1[0]["tipo"] == "p2c" and d1[0]["pendente"]["n"] == 1 and mud == [] and res["pendentes"] == 1
    d2, mud, _ = estabilidade.aplicar(prop(), _doc(d1), "2026-11-06", "2026-10-30", 2)         # mesma coleta: não persistiu
    assert d2[0]["tipo"] == "p2c" and d2[0]["pendente"]["n"] == 1 and mud == []
    d3, mud, res = estabilidade.aplicar(prop(), _doc(d2), "2026-11-12", "2026-11-06", 2)       # outra coleta: confirma
    assert d3[0]["tipo"] == "p2p" and "pendente" not in d3[0] and d3[0]["mudou_em"] == "2026-11-12"
    assert len(mud) == 1 and mud[0]["de"]["tipo"] == "p2c" and mud[0]["para"]["tipo"] == "p2p" and mud[0]["proposta_desde"] == "2026-11-05" and res["confirmadas"] == 1


def test_oscilacao_nao_muda_o_estado_e_proposta_de_volta_limpa_o_pendente():
    estado = [_linha(1, 2, tipo="p2c")]
    d1, _, _ = estabilidade.aplicar([_linha(1, 2, tipo="p2p", p=0.8)], _doc(estado), "2026-11-05", "g1", 2)
    d2, mud, _ = estabilidade.aplicar([_linha(1, 2, tipo="p2c", p=0.91)], _doc(d1), "2026-11-12", "g2", 2)
    assert d2[0]["tipo"] == "p2c" and "pendente" not in d2[0] and mud == []
    # proposta diferente da pendente reinicia a contagem
    d3, _, _ = estabilidade.aplicar([_linha(2, 1, tipo="p2c", p=0.8)], _doc(d1), "2026-11-12", "g2", 2)
    assert d3[0]["a"] == 1 and d3[0]["pendente"]["n"] == 1


def test_aspa_declarado_muda_na_hora():
    estado = [_linha(1, 2, tipo="p2p")]
    out, mud, _ = estabilidade.aplicar([_linha(1, 2, nivel="declarado", p=0.99)], _doc(estado), "2026-11-05", "g1", 2)
    assert out[0]["tipo"] == "p2c" and mud[0]["imediata"] is True


def test_geracao_de_evidencia_usa_a_data_da_coleta_mais_antiga():
    assert estabilidade.geracao({"coletores_coletados_em": {"v4": "2026-10-30", "v6": "2026-10-23"}}, "2026-11-05") == "2026-10-23"
    assert estabilidade.geracao({}, "2026-11-05") == "2026-11-05"


# ── calibração ────────────────────────────────────────────────────────────────────────────────────────────────────
def test_ece_perfeito_e_enviesado():
    assert _ece([(1.0, True)] * 10) == pytest.approx(0)
    assert _ece([(0.9, False)] * 10 + [(0.9, True)] * 0) == pytest.approx(0.9)
    assert _ece([]) is None


def test_calibracao_escolhe_temperatura_maior_para_nb_superconfiante():
    import random

    rnd = random.Random(1)
    aspa, escores = [], {}
    for i in range(1, 400):
        lo, hi = 10_000 + 2 * i, 10_001 + 2 * i
        aspa.append({"customer": hi, "providers": [lo if rnd.random() < 0.7 else 999_999]})
        escores[(lo, hi)] = {"ab": 12.0, "ba": 0.0, "pp": 0.0}        # sempre muito confiante em "lo é provedor", mas só 70% confere
    r = calibracao_v2(escores, aspa)
    assert r["temperatura_otima"] > 1 and r["ece_alto_calibrado"] < r["ece_alto_bruto"]
    assert calibracao_v2({}, aspa)["estado"] == "indisponivel"


def test_ece_por_estrato_localiza_onde_a_calibracao_falha():
    """Elos com poucos pontos de vista acertam 50% e os bem vistos 100%, ambos com confiança ~1: o erro de calibração mora no estrato `vps` baixo."""
    aspa, escores, carac, esp = [], {}, {}, {}
    for i in range(1, 121):
        lo, hi = 10_000 + 2 * i, 10_001 + 2 * i
        poucos = i <= 60
        certo = (i % 2 == 0) if poucos else True
        aspa.append({"customer": hi, "providers": [lo if certo else 999_999]})
        escores[(lo, hi)] = {"ab": 12.0, "ba": 0.0, "pp": 0.0}
        carac[(lo, hi)] = {"vps": "1-2" if poucos else "9+", "grau": "0"}
        esp[(lo, hi)] = {"vps": "1-2" if poucos else "9+", "grau": "0"}
    r = ece_por_estrato(escores, carac, esp, aspa, 1.0, caracteristicas=("vps", "grau"))
    v = r["por_caracteristica"]["vps"]
    assert v["1-2"]["ece"] > 0.4 and v["9+"]["ece"] < 0.01 and v["1-2"]["n"] == 60
    assert r["por_caracteristica"]["grau"]["0"]["n"] == 120
    assert r["faixas"][-1]["p_de"] == 0.9 and r["faixas"][-1]["contribuicao_ece"] == round(r["ece_alto"], 4)
    assert ece_por_estrato({}, {}, {}, aspa, 1.0)["ece_alto"] is None


def test_config_v2_padrao_confere_com_o_arquivo():
    assert cf.carregar().refino == cf.Refino() and cf.carregar().versao == 2
    assert dataclasses.replace(cf.carregar(), versao=1).refino.ativo


# ── transito ──────────────────────────────────────────────────────────────────────────────────────────────────────
REL = {"snapshot_date": "2026-11-05", "algoritmo": "ARC v2", "relacoes": [
    {"a": 1, "b": 10, "tipo": "p2c", "p": 0.9, "nivel": "provavel"}, {"a": 1, "b": 11, "tipo": "p2c", "p": 0.97, "nivel": "confirmado"},
    {"a": 10, "b": 20, "tipo": "p2c", "p": 0.8, "nivel": "provavel"}, {"a": 11, "b": 20, "tipo": "p2c", "p": 0.8, "nivel": "provavel"},
    {"a": 2, "b": 20, "tipo": "p2c", "p": 0.9, "nivel": "provavel"}, {"a": 20, "b": 1, "tipo": "p2c", "p": 0.75, "nivel": "provavel"},   # ciclo: cone não trava
    {"a": 1, "b": 99, "tipo": "p2c", "p": 0.6, "nivel": "possivel"}, {"a": 1, "b": 12, "tipo": "s2s", "p": 0.9, "nivel": "provavel"}]}
DOCS = {a: {"uf": uf, "usuarios": u} for a, uf, u in ((10, "ES", 100), (11, "ES", 50), (20, "SP", 10), (1, "SP", 0), (2, "RJ", 0))}


def test_cone_sem_irmaos_e_com_ciclo():
    cl = tr._p2c(REL)
    assert tr.cone(cl, 1, {1}) == {10, 11, 20}
    assert tr.cone(cl, 1, {1, 20}) == {10, 11}


def test_transito_cone_concentracao_e_cobertura():
    asns, ufs, cob = tr.calcular(REL, DOCS, {}, {1: "Provedor 1", 2: "Provedor 2"}, CFG)
    assert asns["1"]["cone_br"] == 3 and asns["1"]["cone_asns"] == 3 and asns["1"]["cone_ufs"] == {"ES": 2, "SP": 1} and asns["1"]["cone_usuarios"] == 160
    assert asns["2"]["posicao_cone_br"] == 1 and asns["1"]["posicao_cone_br"] == 2 and 99 not in tr.cone(tr._p2c(REL), 1, {1})            # possível não entra
    es = ufs["ES"]
    assert es["asns_br"] == 2 and es["asns_com_provedor"] == 2 and es["provedores_distintos"] == 1 and es["hhi_clientes"] == 10000
    assert es["top1_share"] == 1.0 and es["provedores"][0]["nome"] == "Provedor 1" and es["share_provedores_estrangeiros"] == 0.0
    sp = ufs["SP"]
    assert sp["asns_br"] == 2 and sp["provedores_distintos"] == 4 and sp["hhi_clientes"] < 10000     # 20 tem 4 provedores (10, 11, 2, 1 via ciclo)
    assert cob["elos_p2c_firmes"] == 6 and cob["algoritmo"] == "ARC v2"


def test_transito_irmaos_nao_sao_clientes():
    asns, _, _ = tr.calcular(REL, DOCS, {1: 1, 10: 1}, {}, CFG)
    assert asns["1"]["cone_br"] == 2 and asns["1"]["irmaos_excluidos"] == 1


def test_servico_transito_blocos_e_linhas():
    asns, ufs, cob = tr.calcular(REL, DOCS, {}, {}, CFG)
    cab = {"snapshot_date": "2026-11-05", "limites": "x", "fonte": {}, "cobertura": cob}
    ua, aa = {**cab, "ufs": ufs}, {**cab, "asns": asns}
    assert svc.bloco_asn(aa, 99)["com_cliente"] is False and svc.bloco_asn(aa, 99)["cone_asns"] == 0 and svc.bloco_asn(None, 1) is None
    assert svc.bloco_asn(aa, 1)["cone_br"] == 3
    assert svc.bloco_uf(ua, "es")["uf"] == "ES" and svc.bloco_uf(ua, "XX") is None
    r = svc.resumo_ufs(ua)
    assert r["total"] == 3 and all("provedores" not in u for u in r["ufs"])
    assert {x["uf"] for x in svc.linhas_uf(ua)} == {"ES", "SP", "RJ"} and svc.linhas_asn(aa)[0]["asn"] == 1 and svc.linhas_uf(None) == []
