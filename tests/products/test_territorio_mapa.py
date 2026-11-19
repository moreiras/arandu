# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — `GET /territorio/mapa`: um indicador NORMALIZADO de todos os municípios para o mapa coroplético."""
import pytest

from api.services import territorio as t


def test_todos_os_indicadores_declaram_a_normalizacao(api):
    for ind in t.INDICADORES:
        r = api.get("/api/v1/territorio/mapa", params={"indicador": ind})
        assert r.status_code == 200, (ind, r.text)
        j = r.json()
        assert j["indicador"] == ind and j["rotulo"] and len(j["normalizacao"]) > 20
        assert j["total"] == len(j["valores"])
        assert j["total"] > 0 or ind in ("km_ptt", "transito_unico_pct"), ind       # o sintético não tem a distância ao PTT em todos os municípios nem relação de trânsito inferida firme
        assert all(isinstance(k, str) and len(k) == 7 for k in j["valores"])


def test_valores_batem_com_as_linhas_do_produto(api):
    store = api.app.state.store
    d = store.latest()
    linhas = {r["ibge"]: r for r in store.territorio_linhas(d)}
    j = api.get("/api/v1/territorio/mapa", params={"indicador": "penetracao"}).json()
    for ibge, v in j["valores"].items():
        assert v == pytest.approx(round(linhas[ibge]["penetracao"] * 100, 2))
    pm = api.get("/api/v1/territorio/mapa", params={"indicador": "acessos_por_mil_hab"}).json()["valores"]
    for ibge, v in pm.items():
        r = linhas[ibge]
        assert v == pytest.approx(round(r["acessos"] / (r.get("populacao_estimada") or r["populacao"]) * 1000, 2))


def test_sem_dado_fica_de_fora_nunca_zero():
    doc = {"snapshot_date": "d", "mes_referencia_sici": "m", "censo_ano": "2022", "pnad_ano": "2025", "fonte": "f", "formulas": {}, "limites": ""}
    linhas = [{"ibge": "1", "penetracao": None}, {"ibge": "2", "penetracao": 0.0}, {"ibge": "3", "penetracao": 0.5}, {"ibge": "4", "acessos": 5, "populacao": 0}]
    assert t.mapa(doc, linhas, "penetracao")["valores"] == {"2": 0.0, "3": 50.0}
    assert t.mapa(doc, linhas, "acessos_por_mil_hab")["valores"] == {}


def test_indicador_invalido_da_400_e_o_valor_absoluto_nao_existe(api):
    assert api.get("/api/v1/territorio/mapa", params={"indicador": "xx"}).status_code == 400
    assert api.get("/api/v1/territorio/mapa", params={"indicador": "acessos"}).status_code == 400      # absoluto: não é indicador de mapa
    assert api.get("/api/v1/territorio/mapa", params={"indicador": "populacao"}).status_code == 400


def test_so_estatistica_por_municipio_sem_contato_nem_pessoa(api):
    import json
    corpo = json.dumps(api.get("/api/v1/territorio/mapa").json())
    assert "@" not in corpo and "contact" not in corpo.lower()


def test_e_metered_nao_e_pagina_de_entrada(api):
    from api.auth.access_policy import classify
    assert classify("GET", "/api/v1/territorio/mapa", {}).cls == "metered"


def test_mapa_do_fust_usa_o_valor_do_proprio_artefato(api):
    store = api.app.state.store
    fust = store.fust_doc(store.latest())
    j = api.get("/api/v1/territorio/mapa", params={"indicador": "fust_por_10mil_hab"}).json()
    esperado = {i: m["por_10mil_hab"] for i, m in fust["municipios"].items() if m.get("por_10mil_hab") is not None}
    assert j["valores"] == esperado and j["total"] == len(esperado)
    assert "por_10mil_hab" not in j["rotulo"] and "10 mil" in j["rotulo"]
