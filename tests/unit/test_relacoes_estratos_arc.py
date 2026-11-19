# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Estratos no ARC publicado: classe, rebaixo de "provável" a "possível" e `p_calibrada` (só `ambos`/`so_caida` com VPs)."""
import dataclasses

from products.as_relationships import build, config as cf, por_asn, refino
from products.as_relationships.decisao import Veredito
from products.as_relationships.evidencias import Evidencias

CFG = cf.carregar()
A, B = 100, 200                                    # a < b: `carac` vê `a` como candidato a provedor, `carac_esp` vê `b`


def _v(carac, esp=None, c="ab", nivel_v1="provavel", cfg=CFG, afi="v4", p=0.9):
    ev = Evidencias()
    v1 = Veredito(A, B, "p2c", 0.9, nivel_v1, evid={"colecao": {"votos": 9}})
    pc = {"ab": 0.0, "ba": 0.0, "pp": 0.0} | {c: p, "pp": 1 - p if c != "pp" else p}
    carac = {"tripla": "0", "caida": "0", "vps": "1", "dist_clique": "=1", "grau": "0", **carac}
    esp = {"tripla": "0", "caida": "0", "vps": "1", "dist_clique": "=1", "grau": "0", **(esp or {})}
    votos = {(A, B): [9]} if c == "ab" else {(B, A): [9]}          # uma fonte independente (coletores): sem ela o nível nunca chega a `provavel`
    return refino._veredito(v1, (A, B), c, pc, ev, votos, cfg, carac, "ab", esp, afi)


def test_classe_do_estrato_e_a_mesma_do_diagnostico():
    f = refino.classe_estrato
    assert f({"caida": "ab", "tripla": "ab+"}) == "ambos" and f({"caida": "ab", "tripla": "ab"}) == "so_caida" and f({"caida": "0", "tripla": "ab+"}) == "so_tripla"
    assert f({"caida": "pp", "tripla": "ab+"}) == "conflito" and f({"caida": "ab", "tripla": "ba"}) == "conflito" and f({"caida": "0", "tripla": "0"}) == "sem_evidencia"


def test_sem_evidencia_provavel_e_rebaixado_e_nao_tem_p_calibrada():
    v = _v({})
    assert v.tipo == "p2c" and v.nivel == "possivel"
    assert v.evid["estrato"] == {"classe": "sem_evidencia", "p_calibrada": None}
    assert v.evid["refino"]["rebaixado_por_estrato"] == "sem_evidencia"


def test_ambos_mantem_o_nivel_e_traz_a_taxa_observada_por_familia():
    v4, v6 = _v({"caida": "ab", "tripla": "ab+"}), _v({"caida": "ab", "tripla": "ab+"}, afi="v6")
    assert v4.nivel == "provavel" and v4.evid["estrato"] == {"classe": "ambos", "p_calibrada": 0.9241} and v6.evid["estrato"]["p_calibrada"] == 0.9509
    assert "rebaixado_por_estrato" not in v4.evid["refino"]


def test_vps_zero_perde_a_p_calibrada_e_so_tripla_nunca_a_tem():
    assert _v({"caida": "ab", "tripla": "ab+", "vps": "0"}).evid["estrato"]["p_calibrada"] is None
    assert _v({"tripla": "ab+"}).evid["estrato"] == {"classe": "so_tripla", "p_calibrada": None}
    assert _v({"caida": "ab"}).evid["estrato"] == {"classe": "so_caida", "p_calibrada": 0.9058}


def test_estrato_visto_do_provedor_quando_o_provedor_e_o_maior_asn():
    # p2c b→a (classe "ba"): vale o espelho; CAIDA confirma b como provedor
    v = _v({"caida": "ba"}, {"caida": "ab", "tripla": "ab+"}, c="ba")
    assert v.a == B and v.evid["estrato"]["classe"] == "ambos"


def test_so_provavel_e_rebaixado_e_a_chave_desliga():
    assert _v({}, nivel_v1="possivel").nivel == "possivel" and "rebaixado_por_estrato" not in _v({}, nivel_v1="possivel").evid["refino"]
    off = dataclasses.replace(CFG, refino=dataclasses.replace(CFG.refino, estratos=dataclasses.replace(CFG.refino.estratos, ativo=False)))
    v = _v({}, cfg=off)
    assert v.nivel == "provavel" and v.evid["estrato"] == {"classe": "sem_evidencia", "p_calibrada": None}      # a classe continua informada; nada muda no nível


def test_p2p_nao_tem_estrato_e_a_linha_e_o_item_por_asn_trazem_os_campos():
    assert "estrato" not in _v({}, c="pp").evid
    ambos = _v({"caida": "ab", "tripla": "ab+"})
    linhas = build._juntar({"v4": [ambos]})
    assert linhas[0]["estrato"] == "ambos" and linhas[0]["p_calibrada"] == 0.9241
    doc = por_asn.por_asn(linhas, CFG, {"v4": True, "v6": True})
    item = doc[B]["provedores"][0]
    assert item["estrato"] == "ambos" and item["p_calibrada"] == 0.9241
    sem = build._juntar({"v4": [_v({})]})
    assert por_asn.por_asn(sem, CFG, {"v4": True, "v6": True})[B]["provedores"][0]["p_calibrada"] is None
