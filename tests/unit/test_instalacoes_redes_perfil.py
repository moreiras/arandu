# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Redes do prédio com a situação no PTT local (PT-24 / INST-E5.1): quatro situações, família sem coleta, ASN fora do Brasil, PTT externo sem dado de sessão."""
from api.services import instalacoes as s

OK = {"v6": "ok", "v4": "ok"}
PTT = {"nome": "Fortaleza", "coleta": OK, "direto": {1, 2}, "membros": {1, 2, 3}, "origem": {1, 2, 3, 4}}
DET = {"id": 5140, "escopo": "brasil", "redes": [
    {"asn": 1, "nome": "A", "is_br": True}, {"asn": 3, "nome": "C", "is_br": True}, {"asn": 4, "nome": "D", "is_br": True}, {"asn": 5, "nome": "E", "is_br": True},
    {"asn": 99, "nome": "Estrangeira", "is_br": False}]}
INFO = {1: {"usuarios": 1131927, "ipv6": True}, 3: {"usuarios": None, "ipv6": True}}


def _perfil(ptts=None, externos=None):
    return s.redes_perfil(DET, {"ce": PTT} if ptts is None else ptts, externos or [], lambda a: INFO.get(a, {}))


def test_quatro_situacoes_e_soma_igual_as_redes_do_brasil():
    r = _perfil()
    sit = {x["asn"]: x["situacao"]["ce"] for x in r["redes"] if "situacao" in x}
    assert sit == {1: "sessao_rs", 3: "membro_sem_sessao_rs", 4: "so_origina", 5: "sem_presenca"}
    res = r["redes_perfil"]["resumo"][0]
    assert (res["sessao_rs"], res["membro_sem_sessao_rs"], res["so_origina"], res["sem_presenca"], res["sem_coleta"]) == (1, 1, 1, 1, 0)
    assert res["redes_do_brasil"] == 4 == sum(res[k] for k in s.SITUACOES)       # a soma fecha com as redes do Brasil
    assert "so_origina" in r["redes_perfil"]["inferidas"] and "sessao_rs" not in r["redes_perfil"]["inferidas"]


def test_rede_de_fora_do_brasil_nao_entra_na_conta_nem_ganha_situacao():
    ln = next(x for x in _perfil()["redes"] if x["asn"] == 99)
    assert "situacao" not in ln and "usuarios_apnic" not in ln


def test_usuarios_apnic_nulo_fica_nulo_e_ipv6_vem_do_indice():
    por_asn = {x["asn"]: x for x in _perfil()["redes"]}
    assert por_asn[1]["usuarios_apnic"] == 1131927 and por_asn[1]["ipv6"] is True
    assert por_asn[3]["usuarios_apnic"] is None                                  # sem estimativa: nunca zero
    assert por_asn[5]["usuarios_apnic"] is None and por_asn[5]["ipv6"] is None


def test_ptt_sem_coleta_valida_nao_afirma_ausencia():
    r = _perfil({"ce": {**PTT, "coleta": {"v6": "vazia", "v4": "missing"}}})
    assert {x["situacao"]["ce"] for x in r["redes"] if "situacao" in x} == {"sem_coleta"}
    assert r["redes_perfil"]["resumo"][0]["sem_presenca"] == 0


def test_uma_familia_com_coleta_basta_para_medir_e_a_outra_nao_conta_como_direta():
    ptt = {**PTT, "coleta": {"v6": "vazia", "v4": "ok"}, "direto": {1}}
    assert s.situacao_no_ptt(1, ptt) == "sessao_rs" and s.situacao_no_ptt(2, ptt) == "membro_sem_sessao_rs"


def test_ptt_externo_vai_como_sem_dado_de_sessao_e_a_nota_nao_induz_leitura():
    r = _perfil(externos=[{"ix_id": 5, "code": "netix", "nome": "NetIX", "tipo": "externo"}])
    assert r["redes_perfil"]["ptts_sem_dado_de_sessao"][0]["code"] == "netix"
    nota = r["redes_perfil"]["nota"]
    assert "bilateral" in nota and "inferido" in nota
    assert not any(p in nota.lower() for p in ("oportunidade", "ausente", "falha"))
    assert "Nenhum rótulo diz que uma rede deveria estar no PTT" in nota
