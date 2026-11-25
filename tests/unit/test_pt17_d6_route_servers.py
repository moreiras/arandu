# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""PT-17 (D6): a lista de sessões de route server vem em ordem neutra (PTT e ASN); as ordens por número medido são escolha do usuário."""
from api.services import route_servers as r


def _m(asn, sessoes, up, down_certo, dias=None):
    return {"asn": asn, "nome": f"AS{asn}", "sessoes": sessoes, "up": up, "down": sessoes - up, "down_certo": down_certo, "max_dias_down": dias,
            "max_uso_limite": None, "membro_down": up == 0}


DOC = {"snapshot_date": "2026-11-22", "coletado_em": "2026-11-22T10:00:00Z", "ixps": {
    "sp": {"membros": [_m(300, 2, 0, 2, 40), _m(100, 2, 2, 0), _m(200, 1, 0, 1, 9)]},
    "ba": {"membros": [_m(500, 1, 1, 0)]},
}}


def test_ordem_padrao_e_neutra_por_ptt_e_asn_e_traz_todos_os_membros_com_sessao():
    out = r.ranking(DOC, r.CRITERIO_PADRAO, None, False, 50, 0)
    assert r.CRITERIO_PADRAO == "ptt_asn"
    assert [(x["ixp"], x["asn"]) for x in out["items"]] == [("ba", 500), ("sp", 100), ("sp", 200), ("sp", 300)]      # quem não tem sessão down também está
    assert out["total"] == 4 and [x["posicao"] for x in out["items"]] == [1, 2, 3, 4]
    assert "neutra" in out["criterio"] and "decrescente" not in out["criterio"]


def test_ordem_por_numero_medido_e_escolha_explicita_e_so_traz_quem_tem_o_numero():
    out = r.ranking(DOC, "sessoes_down", None, False, 50, 0)
    assert [(x["ixp"], x["asn"]) for x in out["items"]] == [("sp", 300), ("sp", 200)] and "(decrescente)" in out["criterio"]
    assert [x["asn"] for x in r.ranking(DOC, "dias_down", None, False, 50, 0)["items"]] == [300, 200]


def test_filtro_por_ptt_e_somente_down_continuam_valendo_na_ordem_neutra():
    assert [x["asn"] for x in r.ranking(DOC, "ptt_asn", "sp", False, 50, 0)["items"]] == [100, 200, 300]
    assert [x["asn"] for x in r.ranking(DOC, "ptt_asn", None, True, 50, 0)["items"]] == [200, 300]
