# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cobertura de PTT nomeada e coluna de PTTs das instalações (PT-24 / INST-E5.1)."""
from api.services import instalacoes as s

SITE = {"sp": "São Paulo", "ce": "Fortaleza", "ac": "Rio Branco", "rao": "Ribeirão Preto"}


def _doc(sem_instalacao):
    f = {"id": 1, "escopo": "brasil", "pais": "BR", "nome": "SP4", "n_redes": 3, "ixps": [
        {"ix_id": 3478, "tipo": "outro"}, {"ix_id": 2, "code": "decix-sp", "tipo": "externo"}, {"ix_id": 1, "code": "sp", "tipo": "ixbr"}, {"ix_id": 5, "code": "ce", "tipo": "ixbr"}, {"ix_id": 3, "code": "netix", "tipo": "externo"}], "carriers": []}
    return {"snapshot_date": "2026-11-22", "instalacoes": {"1": f}, "cobertura": {"ptts_ixbr": 3, "ptts_ixbr_com_instalacao": 2, "ptts_ixbr_sem_instalacao": sem_instalacao}}


def test_ptts_da_instalacao_ix_br_primeiro_depois_externos_e_os_nao_acompanhados_por_ultimo():
    ptts = s.resumo(_doc([])["instalacoes"]["1"])["ptts_detalhe"]
    assert [(p.get("code"), p["tipo"]) for p in ptts] == [("ce", "ixbr"), ("sp", "ixbr"), ("decix-sp", "externo"), ("netix", "externo"), (None, "outro")]
    assert s.resumo(_doc([])["instalacoes"]["1"])["n_ptts"] == 5


def test_a_cobertura_fecha_com_os_ptts_do_site_e_nomeia_quem_falta():
    cob = s.cobertura_nomeada(_doc(["ac"]), SITE)
    assert cob["ptts_ixbr_site"] == 4 and cob["ptts_ixbr_nomes"]["rao"] == "Ribeirão Preto"
    assert cob["ptts_ixbr_com_instalacao"] == 2 and cob["ptts_ixbr_sem_instalacao"] == ["ac"] and cob["ptts_ixbr_sem_mapeamento"] == ["rao"]
    assert cob["ptts_ixbr_com_instalacao"] + len(cob["ptts_ixbr_sem_instalacao"]) + len(cob["ptts_ixbr_sem_mapeamento"]) == cob["ptts_ixbr_site"]       # 2 + 1 + 1 = 4
    assert cob["ptts_ixbr_fora_do_site"] == []


def test_codigo_que_nao_e_ptt_do_site_nao_entra_na_soma_e_e_apontado():
    doc = _doc(["ac", "santa-maria"])
    doc["instalacoes"]["1"]["ixps"].append({"ix_id": 9, "code": "santa-maria", "tipo": "ixbr"})
    cob = s.cobertura_nomeada(doc, SITE)
    assert cob["ptts_ixbr_fora_do_site"] == ["santa-maria"] and "santa-maria" not in cob["ptts_ixbr_sem_instalacao"]
    assert cob["ptts_ixbr_com_instalacao"] == 2


def test_sem_lista_do_site_ou_sem_cobertura_nada_e_inventado():
    assert s.cobertura_nomeada(_doc(["ac"]), None) == _doc(["ac"])["cobertura"]
    assert s.cobertura_nomeada({"instalacoes": {}}, SITE) is None


def test_lista_traz_a_cobertura_nomeada_e_o_filtro_de_ptt_e_de_carrier():
    doc = _doc(["ac"])
    r = s.lista(doc, None, None, None, "ce", None, False, False, "redes", 100, 0, SITE)
    assert r["cobertura"]["ptts_ixbr_sem_mapeamento"] == ["rao"] and [f["id"] for f in r["items"]] == [1]
    assert s.lista(doc, None, None, None, "ac", None, False, False, "redes", 100, 0, SITE)["items"] == []          # PTT sem instalação: lista vazia, sem erro
    assert s.lista(doc, None, None, None, None, None, False, True, "redes", 100, 0, SITE)["items"] == []            # a instalação de teste não tem carrier
