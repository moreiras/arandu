# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Produto `decix_rs`: sessões e rotas do DE-CIX × IX.br × PeeringDB, sobre documentos sintéticos (ASNs de documentação)."""
import json

from core.common import configure_logging, read_json_gz, write_json_gz
from products.decix_rs import build as dx

LOG = configure_logging()
DATA = "2026-11-10"


def _sessao(rs, ixp, afi, asn, estado="up", recebidas=10, nome=None):
    return {"rs": rs, "ixp": ixp, "afi": afi, "asn": asn, "neighbor_ip": f"198.18.0.{asn % 250}", "estado": estado, "descricao": nome or f"AS{asn}",
            "rotas": {"recebidas": recebidas, "aceitas": recebidas, "filtradas": 0}, "id_vizinho": f"R{asn}"}


def _rs(rs, ixp, afi, n="rs1"):
    return {"rs": rs, "ixp": ixp, "numero": n, "afi": afi, "estado_rotas": "READY", "consultado": True, "sessoes": 0, "sessoes_up": 0, "vizinhos_em": "2026-11-10T11:00:00Z"}


def _escreve(base, ixbr=True, rotas=True, bloqueio=False):
    n = base / "normalized" / DATA / "summary"
    n.mkdir(parents=True)
    sess = {"generated_at": "2026-11-10T12:00:00Z", "fonte": "https://lg.de-cix.net (Alice-LG)", "versao_alice": "6.2.0",
            "rs": [_rs("rs1_sao_ipv4_de-cix", "decix-sp", "v4"), _rs("rs1_sao_ipv6_de-cix", "decix-sp", "v6"), _rs("rs1_rio_ipv4_de-cix", "decix-rj", "v4")],
            "sessoes": [_sessao("rs1_sao_ipv4_de-cix", "decix-sp", "v4", 64496, recebidas=3), _sessao("rs1_sao_ipv6_de-cix", "decix-sp", "v6", 64496, recebidas=2),
                        _sessao("rs1_sao_ipv4_de-cix", "decix-sp", "v4", 64497, recebidas=600), _sessao("rs1_sao_ipv4_de-cix", "decix-sp", "v4", 64498, estado="down", recebidas=0),
                        _sessao("rs1_sao_ipv4_de-cix", "decix-sp", "v4", 64499), _sessao("rs1_rio_ipv4_de-cix", "decix-rj", "v4", 64496)]}
    write_json_gz(n / "decix_rs_sessions.json.gz", sess)
    if rotas:
        write_json_gz(n / "decix_rs_rotas.json.gz", {
            "generated_at": "2026-11-10T12:30:00Z",
            "cobertura_rodizio": {"total": {}, "por_ptt": {"decix-sp": {"elegiveis": 3, "lidos_na_rodada": 2, "herdados": 0, "sem_leitura": 1, "idade_max_dias": 0}}},
            "vizinhos": [{"ixp": "decix-sp", "afi": "v4", "asn": 64496, "ip": "x", "total": 3, "lidas": 3, "completo": True, "origens": {"64496": 2, "64510": 1}},
                         {"ixp": "decix-sp", "afi": "v4", "asn": 64497, "ip": "y", "total": 600, "lidas": 500, "completo": False, "origens": {"64520": 250, "64521": 250}},
                         {"ixp": "decix-rj", "afi": "v4", "asn": 64496, "ip": "z", "total": 1, "lidas": 1, "completo": True, "herdado": True, "origens": {"64496": 1}}],
            **({"bloqueio": {"motivo": "HTTP 429"}} if bloqueio else {})})
    p = base / "published" / DATA
    (p / "asns").mkdir(parents=True)
    (p / "asns" / "index.json").write_text(json.dumps([{"asn": a, "is_br": True} for a in (64496, 64497, 64510, 64520)] + [{"asn": 64521, "is_br": False}]), encoding="utf-8")
    (p / "external-ixps").mkdir()
    (p / "external-ixps" / "decix-sp.json").write_text(json.dumps({"members": [{"asn": 64496, "name": "A"}, {"asn": 64500, "name": "B"}, {"asn": 64499, "name": "C"}]}), encoding="utf-8")
    (p / "external-ixps" / "equinix-sp.json").write_text(json.dumps({"members": [{"asn": 64496, "name": "A"}, {"asn": 64497, "name": "D"}, {"asn": 64511, "name": "E"}]}), encoding="utf-8")
    if ixbr:
        (p / "ixps").mkdir()
        (p / "ixps" / "sp.json").write_text(json.dumps({"v4": {"asn_direct": [64496, 64497, 64600, 64601], "br_asns_origin": [64496, 64510]}, "v6": {"asn_direct": [64496, 64602], "br_asns_origin": [64496]}}), encoding="utf-8")


def _publica(tmp_path):
    base = tmp_path
    r = dx.publicar_decix_rs(base, DATA, LOG)
    return r, read_json_gz(base / "published" / DATA / "decix_rs" / "ixps.json.gz")


def test_publica_diretos_originadores_membros_e_comparacao_da_cidade(tmp_path):
    base = tmp_path
    _escreve(base)
    res, d = _publica(base)
    assert res == {"ixps": 2, "sessoes": 6}
    sp = d["ixps"]["decix-sp"]
    assert sp["resumo"]["sessoes"] == 5 and sp["resumo"]["sessoes_up"] == 4 and sp["resumo"]["sessoes_down"] == 1
    assert sp["asn_direct"] == [64496, 64497, 64499]                                         # 64498 só tem sessão down: não é direto
    assert sp["resumo"]["membros"] == 4 and sp["resumo"]["membros_up"] == 3 and sp["br_asns_direct"] == [64496, 64497]
    assert sp["asn_origin"] == [64496, 64510, 64520, 64521] and sp["br_asns_origin"] == [64496, 64510, 64520]
    m = next(x for x in sp["membros"] if x["asn"] == 64496)
    assert m["up"] == 2 and m["v4"] == {"up": 1, "down": 0} and m["v6"] == {"up": 1, "down": 0} and m["recebidas"] == {"v4": 3, "v6": 2}
    # origem é piso: um vizinho incompleto e um sem leitura tornam o conjunto parcial, e o documento diz isso
    assert sp["rotas"]["parcial"] is True and sp["rotas"]["vizinhos_lidos"] == 2 and sp["rotas"]["vizinhos_completos"] == 1 and sp["rotas"]["cobertura"]["sem_leitura"] == 1
    assert d["ixps"]["decix-rj"]["rotas"]["parcial"] is True and d["ixps"]["decix-rj"]["rotas"]["herdados"] == 1
    assert "criterio" in sp and "primeiro salto" in sp["criterio"]["asn_direct"] and d["aviso"]
    c = sp["comparacao_cidade"]
    assert c["ixbr"] == {"ptt": "sp", "asn_direct": 5, "br_asn_origin": 2} and c["decix"]["asn_direct"] == 3
    assert c["interseccao_direct"] == {"ambos": 2, "so_decix": 1, "so_ixbr": 3, "pct_do_decix_no_ixbr": 66.7}
    assert c["no_decix_sem_ixbr"] == {"total": 1, "asns": [64499], "truncado": False}
    assert c["decix_br_origin_no_ixbr"] == {"decix": 3, "ambos": 2, "so_decix": 1}
    assert c["externos"]["equinix-sp"] == {"membros_peeringdb": 3, "ambos_decix_sessao": 2, "ambos_ixbr": 2}
    assert sp["peeringdb"]["cadastrados_sem_sessao_up"] == [64500] and sp["peeringdb"]["sessao_up_sem_cadastro"] == [64497]
    rj = d["ixps"]["decix-rj"]["comparacao_cidade"]
    assert rj["ixbr"] is None and "interseccao_direct" not in rj and d["ixps"]["decix-rj"]["peeringdb"] is None        # PTT do IX.br ou cadastro ausentes: nada inventado


def test_sem_leitura_de_rotas_a_origem_nao_existe_e_o_conjunto_e_parcial(tmp_path):
    base = tmp_path
    _escreve(base, rotas=False)
    _, d = _publica(base)
    sp = d["ixps"]["decix-sp"]
    assert sp["asn_origin"] == [] and sp["rotas"]["parcial"] is True and sp["resumo"]["asn_origin_count"] == 0 and sp["asn_direct"]


def test_bloqueio_vai_para_o_cabecalho_e_sem_route_servers_nao_gera(tmp_path):
    base = tmp_path
    _escreve(base, bloqueio=True)
    _, d = _publica(base)
    assert d["bloqueio"] == {"motivo": "HTTP 429"}
    # coleta bloqueada no nível 0: documento de sessões sem route servers
    write_json_gz(base / "normalized" / DATA / "summary" / "decix_rs_sessions.json.gz", {"rs": [], "sessoes": [], "bloqueio": {"motivo": "HTTP 403"}})
    (base / "published" / DATA / "decix_rs" / "ixps.json.gz").unlink()
    assert dx.publicar_decix_rs(base, DATA, LOG) == {} and not (base / "published" / DATA / "decix_rs" / "ixps.json.gz").exists()


def test_ausencia_do_normalizado_nao_gera(tmp_path):
    base = tmp_path
    assert dx.publicar_decix_rs(base, DATA, LOG) == {}
