# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — referências de comparação do AS: `GET /asns/{asn}?include=referencias` (posição e medianas entre os ASes BR)."""
from statistics import median


def test_referencias_batem_com_o_indice(api):
    store = api.app.state.store
    d = store.latest()
    br = [a for a in store.asn_index(d) if a.get("is_br")]
    com_usuarios = sorted((a for a in br if (a.get("apnic_users") or 0) > 0), key=lambda a: -a["apnic_users"])
    alvo = com_usuarios[0]
    r = api.get(f"/api/v1/asns/{alvo['asn']}", params={"include": "referencias"})
    assert r.status_code == 200, r.text
    ref = r.json()["referencias"]
    assert ref["total"] == len(br) and ref["usuarios_com_dado"] == len(com_usuarios)
    assert ref["usuarios_posicao"] == 1
    assert ref["ixps_diretos_mediana"] == median([a.get("ixps_direct_count") or 0 for a in br])
    assert ref["universo"].startswith("ASes brasileiros")
    ultimo = api.get(f"/api/v1/asns/{com_usuarios[-1]['asn']}", params={"include": "referencias"}).json()["referencias"]
    assert ultimo["usuarios_posicao"] == len(com_usuarios)


def test_as_sem_estimativa_nao_tem_posicao(api):
    store = api.app.state.store
    d = store.latest()
    sem = next((a for a in store.asn_index(d) if a.get("is_br") and not (a.get("apnic_users") or 0)), None)
    if sem is None:
        return
    ref = api.get(f"/api/v1/asns/{sem['asn']}", params={"include": "referencias"}).json()["referencias"]
    assert ref["usuarios_posicao"] is None


def test_referencias_so_estatistica_sem_pessoa_nem_contato(api):
    import json
    asn = api.get("/api/v1/asns", params={"limit": 1}).json()["items"][0]["asn"]
    corpo = json.dumps(api.get(f"/api/v1/asns/{asn}", params={"include": "referencias"}).json()["referencias"])
    assert "@" not in corpo and "contact" not in corpo.lower()


def test_sem_o_include_o_perfil_nao_muda(api):
    asn = api.get("/api/v1/asns", params={"limit": 1}).json()["items"][0]["asn"]
    assert "referencias" not in api.get(f"/api/v1/asns/{asn}").json()
