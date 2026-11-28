# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — área de influência dos PTTs na API: rotas abertas, recortes por PTT e visão, 204 sem o arquivo e nunca cálculo na hora."""
import gzip
import json

from tests.products.api_contract import ALLOWED
from tests.synth.world import T1


ARQUIVO = "territorio/area_influencia_ptt.json.gz"


def _doc(base):
    return json.loads(gzip.open(base / "published" / T1 / ARQUIVO, "rt", encoding="utf-8").read())


def test_rota_nacional_e_aberta_para_anonimo_e_traz_o_metodo(api):
    r = api.get("/api/v1/ixps/area-influencia")                              # sem cabeçalho da allowlist: anônimo
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["visao"] == "todos" and j["natureza"] == "inferido" and j["limites"].startswith("Inferência, não cobertura de rede")
    assert j["campos_municipio"] == ["ptt_principal", "faixa", "acessos_principal", "acessos_municipio", "ptts"] and j["municipios"] and j["ptts"]
    assert "municipios_faixa" not in next(iter(j["ptts"].values()))                  # o resumo nacional não repete as listas por PTT
    d = api.get("/api/v1/ixps/area-influencia", params={"visao": "diretos"}).json()
    assert d["visao"] == "diretos" and d["total"]["acessos_atribuidos"] <= j["total"]["acessos_atribuidos"] and d["municipios"]
    assert api.get("/api/v1/ixps/area-influencia", params={"visao": "x"}).status_code == 422


def test_rota_por_ptt_traz_as_duas_visoes_ou_a_pedida(api, pipeline):
    base, _ = pipeline
    d = _doc(base)
    code = next(c for c, p in d["ptts"].items() if p["visoes"]["diretos"] and p["visoes"]["todos"])
    r = api.get(f"/api/v1/ixps/{code}/area-influencia")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ixp"] == code and set(j["visoes"]) == {"diretos", "todos"} and j["pix"]["pontos"] and j["metodo"]["atribuicao"]
    assert j["visoes"]["todos"]["p50_km"] == d["ptts"][code]["visoes"]["todos"]["p50_km"]
    um = api.get(f"/api/v1/ixps/{code}/area-influencia", params={"visao": "diretos"}).json()
    assert set(um["visoes"]) == {"diretos"} and set(um["totais"]) == {"diretos"}
    assert api.get("/api/v1/ixps/nao-existe/area-influencia").status_code == 404


def test_snapshot_sem_o_arquivo_da_204_com_opcional_e_404_sem_ele_e_nunca_calcula(api, monkeypatch):
    monkeypatch.setattr(api.app.state.store, "area_influencia_doc", lambda d: None)
    assert api.get("/api/v1/ixps/area-influencia", params={"opcional": 1}).status_code == 204
    assert api.get("/api/v1/ixps/za/area-influencia", params={"opcional": 1}).status_code == 204
    assert api.get("/api/v1/ixps/za/area-influencia").status_code == 404
    assert api.get("/api/v1/ixps/area-influencia", headers=ALLOWED).status_code == 404
