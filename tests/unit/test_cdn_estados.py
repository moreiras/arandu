# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Três estados por célula da matriz de CDNs (PT-24 / CDNS-E5.1): membro com sessão no route server, membro sem sessão, só via outro AS."""
from api.services import cdn_estados as ce

CDNS = [
    {"name": "Cloudflare", "asns": [13335, 209242], "ixbr": ["ba", "sp"]},
    {"name": "Microsoft / Azure", "asns": [8075], "ixbr": ["rj", "sp"]},
    {"name": "X / Twitter", "asns": [13414, 63179], "ixbr": []},
    {"name": "Google / YouTube", "asns": [15169, 36561], "ixbr": ["rj"]},
    {"name": "OpenCDN", "asns": [64000], "ixbr": ["fec"]},
]
DIRETO = {"sp": {13335}, "ba": {13335}, "rj": set(), "fec": set()}
COLETA = {"sp": True, "ba": True, "rj": True, "fec": False}
ORIGEM = {13335: {"sp", "ba", "pe"}, 209242: {"rj"}, 8075: set(), 13414: {"sp", "rj"}, 63179: set(), 15169: {"rj", "sp"}, 64000: {"fec"}}      # 36561 sem documento


def _est():
    return ce.estados(CDNS, DIRETO, COLETA, lambda a: ORIGEM.get(a))


def test_membro_com_sessao_membro_sem_sessao_e_so_via_outro_as():
    e = _est()["Cloudflare"]
    assert e["ixbr_rs"] == ["ba", "sp"] and e["ixbr_sem_rs"] == []
    assert e["ixbr_origem"] == ["pe", "rj"]                       # origina em PE e RJ sem ser membro; SP e BA já são membro
    m = _est()["Microsoft / Azure"]
    assert m["ixbr_rs"] == [] and m["ixbr_sem_rs"] == ["rj", "sp"] and m["ixbr_origem"] == []


def test_cdn_sem_nenhum_membro_aparece_so_com_origem():
    e = _est()["X / Twitter"]
    assert e["ixbr_rs"] == [] and e["ixbr_sem_rs"] == [] and e["ixbr_origem"] == ["rj", "sp"]
    assert e["sem_rs_em_nenhum_ptt"] is False                      # sem membro não se afirma "sem sessão"


def test_invariantes_rs_dentro_de_membro_e_origem_fora_de_membro():
    for c in CDNS:
        e = _est()[c["name"]]
        membros = set(c["ixbr"])
        assert set(e["ixbr_rs"]) <= membros
        assert not set(e["ixbr_origem"]) & membros
        assert set(e["ixbr_rs"]) | set(e["ixbr_sem_rs"]) | set(e["ixbr_sem_coleta"]) == membros
        assert not set(e["ixbr_rs"]) & set(e["ixbr_sem_rs"])


def test_sem_rs_em_nenhum_ptt_e_fato_so_com_coleta_valida():
    e = _est()
    assert e["Microsoft / Azure"]["sem_rs_em_nenhum_ptt"] is True
    assert e["OpenCDN"]["ixbr_sem_coleta"] == ["fec"] and e["OpenCDN"]["ixbr_sem_rs"] == []       # PTT sem coleta válida não afirma ausência de sessão
    assert e["OpenCDN"]["sem_rs_em_nenhum_ptt"] is False
    assert e["Cloudflare"]["sem_rs_em_nenhum_ptt"] is False


def test_asn_sem_documento_nao_quebra_nem_conta():
    g = _est()["Google / YouTube"]
    assert g["asns_sem_documento"] == [36561]
    assert g["ixbr_origem"] == ["sp"] and g["ixbr_sem_rs"] == ["rj"]


def test_texto_de_leitura_nao_afirma_ausencia_de_troca_de_trafego():
    assert "bilaterais" in ce.LIMITES and "não indica ausência de troca de tráfego" in ce.LIMITES
    assert "inferido" in ce.ESTADOS["ixbr_origem"] and "bilateral" in ce.ESTADOS["ixbr_sem_rs"]
