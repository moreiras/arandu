# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — política do IRR como referência de relação entre ASes."""
import gzip
import io
from types import SimpleNamespace as V

import pytest

from core import irr
from products.as_relationships import irr_relacao

RPSL = """aut-num: AS64500
import: from AS64501
 action pref=10;
 accept ANY
export: to AS64501 announce AS64500
import: from AS64502 accept AS64502
export: to AS64502 announce AS-64500
import: from AS-SET-X accept ANY
import: from AS1 accept ANY refine from AS2 accept AS3
source: TEST

aut-num: AS64501
import: from AS64500 accept AS-CLI-64501
export: to AS64500 announce ANY
source: TEST

aut-num: AS64502
import: from AS64500 accept AS64500
export: to AS64500 announce AS64502
source: TEST

aut-num: AS64999
import: from AS64500 accept ANY
source: TEST
"""


def test_parser_junta_continuacao_e_ignora_o_que_nao_le_com_seguranca():
    objs = list(irr.objetos(io.StringIO(RPSL), juntar=True))
    pol = irr.politicas_aut_num(objs[0], 64500)
    assert ("in", 64501, "any") in pol and ("out", 64501, "proprio") in pol          # `action` em linha de continuação não atrapalha
    assert ("in", 64502, "par") in pol and ("out", 64502, "as_set") in pol
    assert all(p[1] not in (1, 2) for p in pol) and len(pol) == 4                    # conjunto no lugar do par e `refine` ficam de fora


def test_ler_dump_completo_so_guarda_politica_de_as_brasileiro(tmp_path):
    f = tmp_path / "x.db.gz"
    f.write_bytes(gzip.compress(RPSL.encode()))
    rotas, aut, contagem, pol = irr.ler_dump_completo(f, {64500, 64501, 64502})
    assert aut == {64500, 64501, 64502} and 64999 not in pol and contagem["aut_num_br_com_politica"] == 3
    assert pol[64501] == [("in", 64500, "as_set"), ("out", 64500, "any")]


def _pol():
    objs = list(irr.objetos(io.StringIO(RPSL), juntar=True))
    return {"TC": {str(int(o["aut-num"][0][2:])): [list(x) for x in irr.politicas_aut_num(o, int(o["aut-num"][0][2:]))] for o in objs}}


def test_relacoes_p2c_consistente_unilateral_e_p2p():
    rel = irr_relacao.relacoes(_pol())
    assert rel[(64500, 64501)] == {"rotulo": "p2c_consistente", "provedor": 64501, "cliente": 64500}          # 64500 importa ANY de 64501; 64501 manda ANY a 64500
    assert rel[(64500, 64502)]["rotulo"] == "p2p_consistente"
    uni = irr_relacao.relacoes({"TC": {"10": [["in", 20, "any"]]}})
    assert uni[(10, 20)] == {"rotulo": "p2c_unilateral", "provedor": 20, "cliente": 10}


def test_relacoes_conflito_quando_os_dois_mandam_any_ou_apontam_provedores_opostos():
    ambos = irr_relacao.relacoes({"TC": {"10": [["in", 20, "any"], ["out", 20, "any"]]}})
    assert ambos[(10, 20)]["rotulo"] == "conflito"
    opostos = irr_relacao.relacoes({"TC": {"10": [["in", 20, "any"]], "20": [["in", 10, "any"]]}})
    assert opostos[(10, 20)]["rotulo"] == "conflito"


def test_avaliar_conta_concorda_inverso_e_tipo_diferente():
    rel = irr_relacao.relacoes(_pol())
    vs = [V(a=64501, b=64500, tipo="p2c"), V(a=64502, b=64500, tipo="p2c"), V(a=64500, b=64502, tipo="p2p"), V(a=64500, b=64501, tipo="p2c")]
    r = irr_relacao.avaliar(vs, rel)["rotulos"]
    assert r["p2c_consistente"]["concorda"] == 1 and r["p2c_consistente"]["inverso"] == 1
    assert r["p2p_consistente"]["tipo_diferente"] == 1 and r["p2p_consistente"]["concorda"] == 1


def test_regua_usa_o_irr_mais_recente_que_tenha_politicas(tmp_path):
    from core.common import write_json_gz
    from products.as_relationships import validacao

    assert validacao._irr_com_politicas(tmp_path) is None
    for d, pol in (("2026-11-06", None), ("2026-11-10", {"TC": {}}), ("2026-11-12", {"TC": {"10": [["in", 20, "any"]]}}), ("2026-11-13", None)):
        doc = {"snapshot_date": d, **({"politicas": pol} if pol is not None else {})}
        write_json_gz(tmp_path / "normalized" / d / "summary" / "irr_route_objects.json.gz", doc)
    assert validacao._irr_com_politicas(tmp_path)["snapshot_date"] == "2026-11-12"          # a mais recente COM política (vazia não conta)


# ── `lg_ixbr`: o IRR como característica do Naive Bayes, atrás de `refino.irr` ───────────────────────────────────────────
def test_valor_da_caracteristica_vista_do_candidato_a_provedor():
    rel = {(1, 2): {"rotulo": "p2c_consistente", "provedor": 1, "cliente": 2}, (3, 4): {"rotulo": "p2c_unilateral", "provedor": 4, "cliente": 3},
           (5, 6): {"rotulo": "p2p_consistente"}, (7, 8): {"rotulo": "conflito"}}
    assert irr_relacao.valor(rel, 1, 2) == "ab+" and irr_relacao.valor(rel, 2, 1) == "ba+"        # o espelho inverte
    assert irr_relacao.valor(rel, 3, 4) == "ba" and irr_relacao.valor(rel, 4, 3) == "ab"          # unilateral: sem o "+"
    assert irr_relacao.valor(rel, 5, 6) == "pp" and irr_relacao.valor(rel, 6, 5) == "pp"
    assert irr_relacao.valor(rel, 7, 8) == "conf" and irr_relacao.valor(rel, 9, 10) == "0"


def test_com_politicas_ignora_datas_sem_politicas_e_pega_a_mais_recente(tmp_path):
    from core.common import write_json_gz
    for d, doc in (("2026-11-05", {"snapshot_date": "2026-11-05", "politicas": {"TC": {"1": [["in", 2, "any"]]}}}),
                   ("2026-11-10", {"snapshot_date": "2026-11-10", "politicas": {"TC": {"3": [["in", 4, "any"]]}}}),
                   ("2026-11-13", {"snapshot_date": "2026-11-13"})):          # a mais nova não tem `politicas`: não serve
        write_json_gz(tmp_path / "normalized" / d / "summary" / "irr_route_objects.json.gz", doc)
    assert irr_relacao.com_politicas(tmp_path)["snapshot_date"] == "2026-11-10"
    assert irr_relacao.com_politicas(tmp_path / "vazio") is None


def _amostra(irr: str, classe: str, n: int):
    f = {"tripla": "0", "dist_clique": "?", "grau": "0", "vps": "1", "coloc": "0", "rs": "0", "aspa": "0", "caida": "0", "politica": "-/-", "restricao": "0", "irr": irr}
    return [(f, {**f, "irr": {"ab+": "ba+", "ba+": "ab+"}.get(irr, irr)}, classe, 1.0) for _ in range(n)]


def test_nb_irr_constante_e_neutro_e_irr_informativo_move_o_posterior():
    from products.as_relationships import refino
    base = _amostra("0", "ab", 30) + _amostra("0", "pp", 30)
    com, sem = refino.NaiveBayes(), refino.NaiveBayes(sem=["irr"])
    com.treinar(base), sem.treinar(base)
    f = base[0][0]
    assert com.escores(f) == pytest.approx(sem.escores(f))                      # chave desligada (tudo "0"): nenhum efeito
    # treino em que o IRR acompanha a classe: o posterior de quem tem `ab+` sobe em relação a quem não tem declaração
    nb = refino.NaiveBayes()
    nb.treinar(_amostra("ab+", "ab", 40) + _amostra("0", "ab", 10) + _amostra("0", "pp", 40) + _amostra("ba+", "ba", 10))
    p_irr = refino.posterior(nb.escores({**f, "irr": "ab+"}))
    p_sem = refino.posterior(nb.escores({**f, "irr": "0"}))
    assert p_irr["ab"] > p_sem["ab"] and p_irr["ab"] > 0.8


def test_chave_do_irr_vem_desligada_na_configuracao():
    from products.as_relationships import config as cf
    assert cf.carregar().refino.irr is False
