# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Rejeições, communities e política nos route servers do IX.br: decodificação, perfil inferido, amostras, cobertura e o que não se afirma."""
import pytest

from products.rs_policy import build as pol
from tests.synth import market
from tests.synth.world import T1, build_world

NOMES = {"za": "ZA", "zb": "ZB", "zc": "ZC"}


@pytest.fixture(scope="module")
def sint():
    w = build_world(T1)
    rs, dic = market.route_servers(w)
    f, c = market.rs_rotas(w, rs)
    return pol.calcular(f, c, dic, rs, NOMES), f, c, dic, rs


def _v(asn, total, comunidades=None, motivos=None, ixp="za", afi="v4", amostra=None, **kw):
    d = {"rs": f"{ixp.upper()}-rs1-{afi}", "ixp": ixp, "afi": afi, "asn": asn, "ip": f"198.18.0.{asn % 250}", "coletado_em": "2026-01-01T00:00:00Z", "total": total, "contagem": "exata", **kw}
    if comunidades is not None:
        d["comunidades"] = comunidades
    if motivos is not None:
        d["motivos"] = motivos
        d["amostra"] = amostra or []
    return d


def test_rejeicoes_por_motivo_com_rotulo_do_dicionario_e_amostra_limitada(sint):
    out = sint[0]
    a = out["asns"]["64498"]["ixps"]["za"]["rejeicoes"]
    assert a["rotas"] == 40 and [(m["codigo"], m["rotulo"], m["rotas"]) for m in a["motivos"]] == [
        ("26162:300:0", "Invalid on RPKI", 25), ("26162:190:1", "Bogon prefix", 10), ("26162:190:4", "Never via route server", 5)]
    assert len(a["motivos"][0]["amostra"]) == pol.AMOSTRA_PREFIXOS          # 7 prefixos na amostra do coletor, no máximo 5 publicados
    assert a["sem_motivo"] == 0 and a["contagem"] == "exata"
    ev = out["asns"]["64498"]["evidencia_rs"]
    assert ev["rpki_invalido"] == 25 and ev["bogon"] == 10 and ev["nunca_via_rs"] == 5 and ev["rotas_rejeitadas"] == 40 and ev["ptts"] == 1


def test_ixp_resume_rejeicoes_e_cobertura(sint):
    za = sint[0]["ixps"]["za"]
    r = za["rejeicoes"]
    assert r["asns_com_rejeicao"] == 2 and r["rotas_rejeitadas"] == 43 and r["rotas_com_motivo_decodificado"] == 43 and r["soma_dos_motivos"] == 43
    assert [(m["codigo"], m["rotas"], m["asns"]) for m in r["por_motivo"]][:2] == [("26162:300:0", 25, 1), ("26162:190:1", 10, 1)]
    assert r["asns"][0]["asn"] == 64498 and r["cobertura"]["coletados"] == 2 and r["cobertura"]["elegiveis"] > r["cobertura"]["coletados"]
    assert sint[0]["ixps"]["zc"]["politica"]["asns_com_dado"] == 0 and sint[0]["ixps"]["zc"]["politica"]["perfis"] == {}       # PTT sem coleta: sem dado, não "aberto"


def test_perfis_restritivo_seletivo_aberto_sao_rotulados_como_inferidos(sint):
    por = {a: d["ixps"]["za"]["politica"] for a, d in sint[0]["asns"].items() if "politica" in d["ixps"].get("za", {})}
    assert (por["64498"]["perfil"], por["64499"]["perfil"], por["64500"]["perfil"]) == ("restritivo", "seletivo", "aberto")
    assert all(p["perfil_inferido"] is True and p["perfil_criterio"] for p in por.values())
    assert sint[0]["ixps"]["za"]["politica"]["perfis"] == {"aberto": 1, "restritivo": 1, "seletivo": 1}


def test_mesma_intencao_em_duas_formas_conta_a_maior_nao_a_soma(sint):
    p = sint[0]["asns"]["64499"]["ixps"]["za"]["politica"]
    alvos = {a["alvo"]: a for a in p["acoes"]["nao_exportar_para"]["alvos"]}
    assert alvos[64510]["rotas"] == 30 and alvos[64510]["forma"] == "dicionario"          # 65000:0:64510 (30) e 65000:64510 (30): 30, não 60
    assert p["acoes"]["nao_exportar_para"]["alvos_total"] == 3 and p["blackhole_rotas"] == 2


def test_forma_estendida_e_por_ptt(sint):
    p = sint[0]["asns"]["64504"]["ixps"]["zb"]["politica"]
    ne = p["acoes"]["nao_exportar_para"]["alvos"][0]
    assert (ne["alvo"], ne["rotas"], ne["forma"]) == (262704, 20, "equivalente_padrao")
    assert p["acoes"]["nao_exportar_ptt"]["alvos"][0]["rotulo"] == "No export to IX.br Rio de Janeiro/RJ" and p["perfil"] == "seletivo"


def test_grafo_declarado_e_explorador_de_communities(sint):
    out = sint[0]
    g = {(a["ixp"], a["de"], a["para"], a["tipo"]): a for a in out["grafo"]}
    assert g[("za", 64498, 64500, "exporta_somente_para")]["fracao"] == 1.0 and g[("za", 64499, 64510, "nao_exporta_para")]["rotas"] == 30
    assert ("zb", 64504, 262704, "nao_exporta_para") in g
    c = {x["community"]: x for x in out["communities"]}
    k = c["65000:0:64510"]
    assert (k["classe"], k["rotulo"], k["asns_total"], k["rotas_total"]) == ("nao_exportar_para", "No export to AS64510", 1, 30) and k["ixps"]["za"]["top"][0]["asn"] == 64499
    assert c["65000:64510"]["forma"] == "equivalente_padrao" and c["65535:666"]["classe"] == "blackhole"
    assert out["linhas"]["rs_communities"] and {r["classe"] for r in out["linhas"]["rs_filtradas"]} == {"rejeicao", "blackhole"}


def test_perfil_exige_rotas_suficientes_e_dicionario_vazio_nao_inventa():
    p = pol.politica_do_asn([_v(1, 5, {"65001:0:2": 5})], pol.Dicionario(market._dicionario_alice()))
    assert p["perfil"] is None and "menos de" in p["perfil_criterio"]
    vazio = pol.politica_do_asn([_v(1, 100, {"65001:0:2": 100})], pol.Dicionario(None))
    assert vazio["acoes"] == {} and vazio["perfil"] is None and "ausente" in vazio["perfil_criterio"]         # sem dicionário nada é decodificado: não se chama de "aberto"
    assert pol.classificar_perfil(100, {"nao_exportar_para": {"alvos_total": 60, "fracao_max": 0.6}})[0] == "restritivo"
    assert pol.classificar_perfil(100, {"nao_exportar_para": {"alvos_total": 60, "fracao_max": 0.4}})[0] == "seletivo"
    assert pol.classificar_perfil(100, {"nao_exportar_rir": {"alvos_total": 1, "fracao_max": 0.09}})[0] == "aberto"


def test_ixp_fora_do_config_e_vizinho_herdado():
    dic = market._dicionario_alice()
    f = {"cobertura": {}, "vizinhos": [_v(1, 4, motivos={"26162:300:0": 4}, ixp="za", herdado=True), _v(2, 3, motivos={"26162:300:0": 3}, ixp="rr-old")]}
    out = pol.calcular(f, None, dic, None, NOMES)
    assert list(out["asns"]) == ["1"] and out["asns"]["1"]["ixps"]["za"]["rejeicoes"]["herdado"] is True and "rr-old" not in out["ixps"]
    assert out["asns"]["1"]["ixps"]["za"]["rejeicoes"]["sem_motivo"] == 0


def test_so_nivel_3_ou_so_nivel_2_geram_o_que_podem(sint):
    _, f, c, dic, rs = sint
    so2 = pol.calcular(f, None, dic, rs, NOMES)
    assert so2["communities"] == [] and so2["grafo"] == [] and so2["asns"]["64498"]["ixps"]["za"].get("politica") is None and so2["ixps"]["za"]["politica"] is None
    so3 = pol.calcular(None, c, dic, rs, NOMES)
    assert "rejeicoes" not in so3["asns"]["64498"]["ixps"]["za"] and so3["ixps"]["za"]["rejeicoes"] is None


def test_rota_com_dois_motivos_faz_a_soma_passar_do_total_sem_inventar_rota_sem_motivo():
    dic = market._dicionario_alice()
    f = {"cobertura": {}, "vizinhos": [_v(1, 10, motivos={"26162:300:0": 8, "26162:100:0": 5}, ixp="za")]}          # 13 > 10: 3 rotas têm os dois motivos
    r = pol.calcular(f, None, dic, None, NOMES)["ixps"]["za"]["rejeicoes"]
    assert (r["rotas_rejeitadas"], r["soma_dos_motivos"], r["rotas_com_motivo_decodificado"]) == (10, 13, 10)
