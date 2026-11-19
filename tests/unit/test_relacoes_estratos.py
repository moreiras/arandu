# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Estratos de evidência independente: definição, ECE por estrato, cobertura e viés do ASPA."""
from products.as_relationships.decisao import Veredito
from products.as_relationships.estratos import classe_estrato, medir


def test_definicao_do_estrato_e_o_conflito():
    assert classe_estrato({"caida": "ab", "tripla": "ab+"}) == "ambos"
    assert classe_estrato({"caida": "ab", "tripla": "ab"}) == "so_caida"            # tripla sem o `+` não confirma, mas não contradiz
    assert classe_estrato({"caida": "0", "tripla": "ab+"}) == "so_tripla"
    assert classe_estrato({"caida": "ab", "tripla": "ba+"}) == "conflito"
    assert classe_estrato({"caida": "ab", "tripla": "ba"}) == "conflito"
    assert classe_estrato({"caida": "pp", "tripla": "ab+"}) == "conflito"
    assert classe_estrato({"caida": "ba", "tripla": "ab+"}) == "conflito"
    assert classe_estrato({"caida": "0", "tripla": "ab", "dist_clique": "<1"}) == "sem_evidencia"      # distância ao clique e VPs não contam
    assert classe_estrato({"caida": "pp", "tripla": "ab"}) == "sem_evidencia"


def _mundo():
    """40 elos com CAIDA (o ASPA confirma 36), 40 sem evidência (o ASPA confirma 10) e 1 em conflito; o IRR diz o que o ARC disse nos desmentidos."""
    aspa, escores, carac, esp, vs, irr = [], {}, {}, {}, [], {}
    def elo(i, caida, tripla, certo, irr_concorda):
        lo, hi = 10_000 + 2 * i, 10_001 + 2 * i
        aspa.append({"customer": hi, "providers": [lo if certo else 999_999]})
        escores[(lo, hi)] = {"ab": 12.0, "ba": 0.0, "pp": 0.0}
        carac[(lo, hi)] = {"caida": caida, "tripla": tripla, "vps": "2"}
        esp[(lo, hi)] = {"caida": "ba", "tripla": "ba+", "vps": "2"}
        vs.append(Veredito(lo, hi, "p2c", 0.99, "provavel"))
        if irr_concorda is not None:
            irr[(lo, hi)] = {"rotulo": "p2c_unilateral", "provedor": lo if irr_concorda else hi, "cliente": hi if irr_concorda else lo}
    for i in range(40):
        elo(i, "ab", "0", i >= 4, True if i < 4 else None)
    for i in range(40, 80):
        elo(i, "0", "0", i >= 70, True if i < 50 else False if i < 55 else None)
    elo(80, "ab", "ba+", True, None)
    return aspa, carac, esp, vs, irr


def test_medir_ece_por_estrato_cobertura_e_vies_do_aspa():
    aspa, carac, esp, vs, irr = _mundo()
    escores = {k: {"ab": 12.0, "ba": 0.0, "pp": 0.0} for k in carac}
    d2 = {"escores": escores, "caracteristicas": carac, "caracteristicas_espelho": esp, "temperatura": 1.0}
    br = {v.b for v in vs}
    r = medir(vs, d2, aspa, irr, br)
    assert r["por_estrato"]["so_caida"]["n"] == 40 and r["por_estrato"]["so_caida"]["acerto"] == 0.9
    assert r["por_estrato"]["so_caida"]["ece"] < 0.11                                   # acerto 0,90 com confiança ~1
    assert r["por_estrato"]["sem_evidencia"]["acerto"] == 0.25 and r["por_estrato"]["sem_evidencia"]["ece"] > 0.7
    assert r["por_estrato"]["conflito"]["n"] == 1 and r["por_estrato"]["conflito"]["ece"] is None       # < 30 eventos: sem ECE
    assert r["com_evidencia"]["n"] == 40 and r["com_evidencia"]["por_vps"]["2"]["n"] == 40
    # cobertura: 40 de 81 p2c têm evidência (1 conflito fica fora)
    assert r["cobertura"]["br"]["so_caida"] == 40 and r["cobertura"]["br"]["conflito"] == 1 and r["cobertura"]["br"]["com_evidencia_pct"] == 49.4
    # viés: dos 4 desmentidos com evidência o IRR concorda com o ARC nos 4; dos 30 sem evidência desmentidos, 10 com IRR a favor e 5 contra
    v = r["vies_aspa"]
    assert v["com_evidencia"]["aspa_desmente"]["irr_concorda"] == 4 and v["com_evidencia"]["desmentidos_com_irr_que_concorda_pct"] == 100.0
    assert v["sem_evidencia"]["aspa_desmente"]["irr_concorda"] == 10 and v["sem_evidencia"]["aspa_desmente"]["irr_discorda"] == 5
    assert v["sem_evidencia"]["desmentidos_com_irr_que_concorda_pct"] == 66.7


def test_medir_sem_irr_e_sem_eventos():
    d2 = {"escores": {}, "caracteristicas": {}, "caracteristicas_espelho": {}, "temperatura": 1.0}
    r = medir([], d2, [], None, set())
    assert r["eventos_aspa_p_alta"] == 0 and "vies_aspa" not in r and r["cobertura"]["br"]["com_evidencia_pct"] is None


def test_filtro_vps0_calibracao_cv_e_rebaixo():
    """300 elos com CAIDA (acerto 90%, confiança ~1; 1 em 10 com `vps=0`) e 100 sem evidência (acerto 10%): a taxa observada calibra melhor que a confiança."""
    aspa, carac, esp, vs = [], {}, {}, []
    for i in range(400):
        lo, hi = 10_000 + 2 * i, 10_001 + 2 * i
        com = i < 300
        certo = (i % 10 != 0) if com else (i % 10 == 0)
        aspa.append({"customer": hi, "providers": [lo if certo else 999_999]})
        vps = "0" if (com and i % 10 == 9) else "1"
        carac[(lo, hi)] = {"caida": "ab" if com else "0", "tripla": "0", "vps": vps}
        esp[(lo, hi)] = {"caida": "ba", "tripla": "0", "vps": vps}
        vs.append(Veredito(lo, hi, "p2c", 0.99, "provavel"))
    escores = {k: {"ab": 12.0, "ba": 0.0, "pp": 0.0} for k in carac}
    d2 = {"escores": escores, "caracteristicas": carac, "caracteristicas_espelho": esp, "temperatura": 1.0}
    r = medir(vs, d2, aspa, None, {v.b for v in vs})
    assert r["com_evidencia"]["n"] == 300 and r["com_evidencia_sem_vps0"]["n"] == 270
    cv = r["calibracao_cv"]["por_estrato"]
    assert cv["eventos"] > 200 and cv["ece_cv"] < 0.05 < r["com_evidencia_sem_vps0"]["ece"]
    # rebaixo: os 100 elos sem evidência saem de "provável" (acerto 10%): a precisão sobe e o recall cai pouco
    b, rb = r["rebaixo"]["base"], r["rebaixo"]["conflito_e_sem_evidencia"]
    assert rb["previstos"] == b["previstos"] - 100 and rb["precisao"] > b["precisao"] and rb["recall"] < b["recall"]
    assert r["rebaixo"]["so_conflito"]["previstos"] == b["previstos"]                                # não há conflito neste mundo
    assert r["rebaixo"]["tudo_fora_do_estrato"]["previstos"] == b["previstos"] - 130                  # sem evidência + com evidência e vps=0
