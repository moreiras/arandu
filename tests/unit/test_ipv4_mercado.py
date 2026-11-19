# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Mercado de IPv4: operações, casamento com ASN, mercado, recuperação e blocos do Brasil, sobre o mundo sintético com casos plantados."""
import pytest

from products.ipv4 import build as B
from tests.synth import market
from tests.synth.world import build_world

D = "2026-09-20"


@pytest.fixture(scope="module")
def dados():
    w = build_world()
    listas, estado, ev = market.ipv4(w, D)
    br = sorted((a for a in w.ases.values() if a.is_br and a.role == "access"), key=lambda a: a.asn)[:4]
    idx = {b: {"asn": a.asn, "org": a.name, "cnpj": a.cnpj} for a in br for b in a.v4}
    return listas, estado, ev, idx, br


def test_lote_do_mesmo_dia_e_partes_e_uma_operacao_so(dados):
    listas, _, _, idx, br = dados
    ops = B.operacoes(listas, idx)
    lote = next(o for o in ops if o["data"] == "2026-03-01")
    assert lote["n_blocos"] == 2 and lote["enderecos"] == 512 and lote["direcao"] == "br_br" and lote["tamanho"] == "22_a_23" and lote["anterior_a_coleta"] is True and lote["defasagem_dias"] is None
    assert len(ops) == 4 and lote["casamento"]["asn"] == br[1].asn


def test_pessoa_fisica_e_mascarada_e_defasagem_so_para_o_que_apareceu_depois_do_inicio_da_coleta(dados):
    listas, _, _, idx, _ = dados
    pf = next(o for o in B.operacoes(listas, idx) if o["data"] == "2026-08-20")
    assert pf["origem"]["nome"] == "Pessoa física" and pf["origem"]["pessoa"] == "pf_provavel" and pf["defasagem_dias"] == 31 and pf["anterior_a_coleta"] is False


def test_operacao_nos_dois_registros_junta_as_fontes_e_a_so_do_lacnic_entra_separada(dados):
    listas, _, _, idx, _ = dados
    ops = B.operacoes(listas, idx)
    ext = next(o for o in ops if o["data"] == "2026-09-10")
    assert ext["fontes"] == ["registrobr", "lacnic"] and ext["direcao"] == "br_exterior"
    so_lacnic = next(o for o in ops if o["data"] == "2026-07-15")
    assert so_lacnic["fontes"] == ["lacnic"] and so_lacnic["direcao"] == "exterior_br" and so_lacnic["destino"]["pais"] == "BR"
    assert not any(o["data"] == "2026-02-01" for o in ops)                                          # transferência sem o Brasil fica de fora


def test_mercado_soma_por_ano_direcao_e_tamanho_e_mede_o_casamento(dados):
    listas, _, _, idx, _ = dados
    m = B.mercado(B.operacoes(listas, idx))
    assert m["operacoes"] == 4 and m["blocos"] == 5 and m["enderecos"] == 512 + 512 + 256 + 256 and set(m["por_ano"]) == {"2026"}
    assert m["por_ano"]["2026"]["por_direcao"]["br_br"]["operacoes"] == 2 and m["maior_operacao"]["blocos"] == 2
    assert m["defasagem"]["operacoes_com_medida"] == 2 and m["casamento"]["destino_br"] == 3 and m["casamento"]["com_asn"] == 3
    assert all(p["nome"] != "Pessoa física" for p in m["concentracao"]["top_origens"])


def test_casar_aceita_bloco_contido_no_alocado():
    idx = {"198.18.0.0/22": {"asn": 1, "org": "X", "cnpj": None}}
    assert B.casar("198.18.1.0/24", idx)["asn"] == 1 and B.casar("198.18.0.0/22", idx)["asn"] == 1 and B.casar("198.19.0.0/24", idx) is None


def test_recuperacao_cruza_o_status_do_delegated_e_resume_eventos_por_mes(dados):
    listas, estado, ev, _, _ = dados
    eventos = [e for lst in ev.values() for e in lst]
    r = B.recuperacao(listas, estado, eventos)
    bloco = next(i for i in r["em_recuperacao"]["itens"] if i["tipo"] == "bloco")
    assert bloco["status_delegated"] == "reserved" and r["em_recuperacao"]["por_tipo"] == {"bloco": 1, "asn": 1} and r["recuperados"]["total"] == 2
    assert r["eventos_por_mes"] == {"2026-09": {"recuperacao": 256}}


def test_blocos_br_so_do_brasil_com_asn_e_organizacao(dados):
    _, estado, _, idx, br = dados
    bl = B.blocos_br(estado, idx)
    assert all(b[2] == "allocated" for b in bl)                                                      # o reservado não tem país
    p3 = next(b for b in bl if b[0] == br[2].v4[0].split("/")[0])                                    # 64498 é o único dono deste bloco (o 198.18.0.0/24 é MOAS no mundo sintético)
    assert p3[5] == br[2].asn and p3[6] == br[2].name and p3[1] == 512


def test_concentracao_junta_grafias_do_mesmo_nome():
    mk = lambda nome, e: {"data": "2026-01-01", "n_blocos": 1, "enderecos": e, "tamanho": "ate_24", "direcao": "br_br", "origem": {"nome": "X LTDA", "pessoa": "pj", "pais": "BR"},   # noqa: E731
                          "destino": {"nome": nome, "pessoa": "pj", "pais": "BR"}, "defasagem_dias": None, "casamento": None}
    m = B.mercado([mk("TIM S.A.", 256), mk("TIM SA", 512), mk("Tim S/A", 256), mk("OUTRA LTDA", 300)])
    assert m["concentracao"]["top_destinos"][0] == {"nome": "TIM S.A.", "enderecos": 1024, "pct": 77.4} or m["concentracao"]["top_destinos"][0]["enderecos"] == 1024
    assert len(m["concentracao"]["top_destinos"]) == 2
