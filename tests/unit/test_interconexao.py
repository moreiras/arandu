# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — interconexão mensurável e alcance de CDN: só fatos observados, nunca "não troca tráfego com B"."""
from api.services.interconexao import LIMITES_OPORTUNIDADES, alcance_cdns, oportunidades

IXPS = {"sp": {"nome": "São Paulo", "uf": "SP"}, "rj": {"nome": "Rio", "uf": "RJ"}, "ce": {"nome": "Fortaleza", "uf": "CE"}}


def _doc():
    return {"asn": 64500, "apnic_users": 1000, "ixp_presence": {
        "sp": {"v4": {"origin": True, "direct": False}, "v6": {"origin": True, "direct": False}},
        "rj": {"v4": {"origin": True, "direct": True}, "v6": {"origin": True, "direct": False}},
        "ce": {"v4": {"origin": True, "direct": False}}},
        # formato do pipeline (`_parse_route_file`): ASes entre a origem e o PTT, sem a origem, na ordem origem → PTT; o último é o par do PTT
        "ixp_paths": {"sp": [[10], [20, 10], [30]]}}


def test_origem_sem_direto_ordena_por_mesma_uf_e_conta_carregadores():
    r = oportunidades(_doc(), None, None, None, IXPS, "CE")
    assert [o["ixp"] for o in r["origem_sem_direto"]] == ["ce", "sp", "rj"]            # mesma UF primeiro; depois mais famílias
    sp = next(o for o in r["origem_sem_direto"] if o["ixp"] == "sp")
    assert sp["familias"] == ["v4", "v6"] and [(c["asn"], c["caminhos"], c["via"]) for c in sp["carregadores"]] == [(10, 2, [20]), (30, 1, [])]
    assert next(o for o in r["origem_sem_direto"] if o["ixp"] == "rj")["familias"] == ["v6"]      # direto em v4: só a família sem sessão direta entra
    assert r["resumo"]["origem_sem_direto"] == 3


def test_sessoes_distinguem_sem_sessao_de_so_uma_familia():
    rs_asn = {"ixps": {"sp": {"cadastrado": True, "sessoes": 0, "lista": []}, "rj": {"cadastrado": True, "sessoes": 1, "lista": [{"afi": "v4"}]}}}
    rs_ixps = {"ixps": {"sp": {"rs": [{"afi": "v4"}, {"afi": "v6"}]}, "rj": {"rs": [{"afi": "v4"}, {"afi": "v6"}]}}}
    r = oportunidades(_doc(), rs_asn, rs_ixps, None, IXPS, "SP")
    assert [(s["ixp"], s["situacao"]) for s in r["sessoes"]] == [("sp", "sem_sessao"), ("rj", "sem_v6")]
    assert r["resumo"]["sem_sessao"] == 1 and r["resumo"]["sessao_parcial"] == 1


def test_rejeicoes_e_o_aviso_de_que_peering_bilateral_nao_e_visivel():
    pol = {"ixps": {"sp": {"rejeicoes": {"rotas": 40, "motivos": [{"rotulo": "Invalid on RPKI", "codigo": "x", "rotas": 25, "classe": "rejeicao"}, {"rotulo": "info", "classe": "informativa", "rotas": 3}]},
                           "politica": {"perfil": "restritivo", "perfil_inferido": True, "acoes": {"exportar_somente_para": {}}}}}}
    r = oportunidades(_doc(), None, None, pol, IXPS, None)
    rej = r["rejeicoes"][0]
    assert rej["rotas_rejeitadas"] == 40 and [m["rotulo"] for m in rej["motivos"]] == ["Invalid on RPKI"] and rej["acoes"] == ["exportar_somente_para"]
    assert "bilateral" in LIMITES_OPORTUNIDADES and "não aparece" in LIMITES_OPORTUNIDADES


def test_alcance_de_cdn_por_uf_usa_membros_dos_ptts_da_cdn():
    cdns = [{"name": "X", "ixbr": ["sp", "rj"]}, {"name": "Y", "ixbr": ["ce"]}, {"name": "Z", "ixbr": []}]
    membros = {1: ["sp"], 2: ["ce"], 3: [], 4: ["rj", "ce"]}
    usuarios = {1: 100, 2: 300, 3: 600, 4: 200}
    uf = {1: "SP", 2: "CE", 3: "CE", 4: "RJ"}
    r = alcance_cdns(cdns, membros, usuarios, uf)
    x = next(c for c in r["cdns"] if c["name"] == "X")
    assert r["usuarios_br_com_uf"] == 1200 and x["usuarios_alcancados"] == 300 and x["pct"] == 25.0
    assert x["por_uf"]["CE"] == {"usuarios": 900, "alcancados": 0, "pct": 0.0} and x["por_uf"]["SP"]["pct"] == 100.0
    assert [c["name"] for c in r["cdns"]] == ["Y", "X"]                              # CDN sem PTT no IX.br não entra; maior alcance primeiro


def test_origem_sem_direto_ordena_pela_distancia_da_sede_quando_ha_coordenada():
    doc = {"asn": 1, "ixp_presence": {"sp": {"v4": {"origin": True, "direct": False}}, "ce": {"v4": {"origin": True, "direct": False}}, "rj": {"v6": {"origin": True, "direct": False}}}}
    ixps = {"sp": {"nome": "SP", "uf": "SP"}, "ce": {"nome": "CE", "uf": "CE"}, "rj": {"nome": "RJ", "uf": "RJ"}}
    r = oportunidades(doc, None, None, None, ixps, "SP", {"sp": 15.0, "rj": 360.0, "ce": 2350.0})
    assert [(o["ixp"], o["km_da_sede"]) for o in r["origem_sem_direto"]] == [("sp", 15.0), ("rj", 360.0), ("ce", 2350.0)]      # mais perto primeiro, mesmo sendo outra UF
    sem = oportunidades(doc, None, None, None, ixps, "SP", None)
    assert [o["ixp"] for o in sem["origem_sem_direto"]][0] == "sp" and all(o["km_da_sede"] is None for o in sem["origem_sem_direto"])   # sem coordenada, cai para a UF


def _rotas_gz(tmp_path, rotas):
    import gzip
    import json
    p = tmp_path / "routes-v4.json.gz"
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump({"routes": [{"aspath": a} for a in rotas]}, f)
    return p


def test_carregador_e_o_ultimo_as_do_caminho_gravado_pelo_pipeline(tmp_path):
    """ASN-E1: os caminhos vêm de `_parse_route_file`, como no pipeline; o par do PTT é o último e o caminho de um AS é o próprio vizinho."""
    from products.asn_docs.build import _parse_route_file
    # AS_PATH do looking glass: par do PTT primeiro, origem por último
    idx = _parse_route_file(_rotas_gz(tmp_path, [[28158, 13357], [28158, 28158, 13357],          # vizinho direto (com prepend)
                                                 [16735, 53062, 64500], [53062, 64500],           # via AS53062 até AS16735; AS53062 direto
                                                 [1031, 263444, 64500],                            # via AS263444 até AS1031
                                                 [64500]]))                                         # o próprio par: não é carregador
    assert idx[13357] == {(28158,): 2} and idx[64500] == {(53062, 16735): 1, (53062,): 1, (263444, 1031): 1}
    doc = {"asn": 13357, "relacoes": {"irmaos": []}, "ixp_presence": {c: {"v4": {"origin": True, "direct": False}} for c in ("cac", "igu", "mgf")},
           "ixp_paths": {c: [list(t) for t in idx[13357]] for c in ("cac", "igu", "mgf")}}
    r = oportunidades(doc, None, None, None, {}, None, None, {28158})
    assert [(o["ixp"], o["carregadores"]) for o in r["origem_sem_direto"]] == [
        (c, [{"asn": 28158, "caminhos": 1, "via": [], "vinculo": "mesmo_cnpj"}]) for c in ("cac", "igu", "mgf")]
    assert r["carregadores_disponiveis"] is True
    doc2 = {"asn": 64500, "relacoes": {"irmaos": [{"asn": 1031}]}, "ixp_presence": {"cas": {"v4": {"origin": True}}},
            "ixp_paths": {"cas": [list(t) for t in idx[64500]]}}
    cs = oportunidades(doc2, None, None, None, {}, None)["origem_sem_direto"][0]["carregadores"]
    assert {c["asn"]: (c["via"], c["vinculo"]) for c in cs} == {16735: ([53062], None), 53062: ([], None), 1031: ([263444], "mesma_org")}
    assert all(c["asn"] != 64500 for c in cs)                                                        # nunca o próprio AS


def test_carregadores_ignoram_caminho_vazio_ou_malformado():
    doc = {"asn": 1, "ixp_presence": {"sp": {"v6": {"origin": True}}}, "ixp_paths": {"sp": [[], None, "x", [7]]}}
    assert oportunidades(doc, None, None, None, {}, None)["origem_sem_direto"][0]["carregadores"] == [{"asn": 7, "caminhos": 1, "via": [], "vinculo": None}]
