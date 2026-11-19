# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — `GET /asns/{asn}/interconexao` e `GET /cdns/alcance`."""


def test_interconexao_do_as_traz_limites_e_so_fatos(api):
    asn = next(a["asn"] for a in api.get("/api/v1/asns", params={"limit": 50}).json()["items"] if a.get("is_br"))
    r = api.get(f"/api/v1/asns/{asn}/interconexao")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["asn"] == asn and "bilateral" in j["limites"]
    assert set(j["resumo"]) == {"origem_sem_direto", "sem_sessao", "sessao_parcial", "ptts_com_rejeicao"}
    for o in j["origem_sem_direto"]:
        assert set(o["familias"]) <= {"v4", "v6"} and o["ixp"]
    assert api.get("/api/v1/asns/1/interconexao").status_code == 404


def test_alcance_de_cdn_fica_entre_0_e_100(api):
    r = api.get("/api/v1/cdns/alcance")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["limites"] and j["usuarios_br_com_uf"] > 0
    for c in j["cdns"]:
        assert 0 <= c["pct"] <= 100 and c["ptts"]
        assert all(0 <= v["pct"] <= 100 and v["alcancados"] <= v["usuarios"] for v in c["por_uf"].values())
