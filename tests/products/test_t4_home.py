# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — os cartões da página inicial (frontend/src/features/home/cartoes.json): cada consulta é válida e responde no dataset sintético."""
import json
import re
from pathlib import Path

import pytest

from tests.products.api_contract import ALLOWED

ROOT = Path(__file__).resolve().parents[2]
CARTOES = json.loads((ROOT / "frontend" / "src" / "features" / "home" / "cartoes.json").read_text(encoding="utf-8"))["cartoes"]
CATALOGO = {f["id"] for f in json.loads((ROOT / "docs" / "fontes.json").read_text(encoding="utf-8"))["fontes"]}
# o dataset sintético (Arandurápolis) não tem municípios dominados nem ASes sem RPKI com IPv6 em 3 PTTs: nesses a consulta tem de ser válida, não necessariamente trazer linhas
PODE_VIR_VAZIO = {"longe-de-ptt", "sem-sici-com-usuarios", "monopolio-local", "grandes-sem-asn", "sem-rpki", "divergencias-apnic-anatel", "o-que-mudou"}


def _responder(api, c):
    q = c["consulta"]
    if q["tipo"] == "derivado":
        # as consultas de um cartão derivado precisam ser válidas; o cruzamento em si é testado no front (derivados.test.ts)
        resp = None
        for passo in q["consultas"]:
            corpo = json.loads(json.dumps(passo["corpo"]).replace('"$cnpjs"', "[]"))
            resp = api.post(f"/api/v1/query/{passo['colecao']}", json=corpo, headers=ALLOWED)
            assert resp.status_code == 200, resp.text[:300]
        return resp
    if q["tipo"] == "query":
        return api.post(f"/api/v1/query/{q['colecao']}", json=q["corpo"], headers=ALLOWED)
    return api.get(q["caminho"], params=q.get("params"), headers=ALLOWED)


def test_ha_de_6_a_10_cartoes_com_ids_unicos():
    assert 6 <= len(CARTOES) <= 10      # de 6 a 10 cartões
    assert len({c["id"] for c in CARTOES}) == len(CARTOES)


@pytest.mark.parametrize("c", CARTOES, ids=lambda c: c["id"])
def test_cada_cartao_responde_200_com_itens(api, c):
    r = _responder(api, c)
    assert r.status_code == 200, r.text[:300]
    itens = r.json().get("items")
    if c["consulta"]["tipo"] == "derivado":
        return
    assert isinstance(itens, list)
    if c["id"] not in PODE_VIR_VAZIO:
        assert itens, f"cartão sem resultado no sintético: {c['id']}"
    for it in itens:
        campos = {c["linha"]["rotulo"], c["linha"]["valor"], *re.findall(r"\{(\w+)\}", c["linha"]["link"])}
        assert campos <= set(it), f"{c['id']}: faltam campos {campos - set(it)} na resposta {sorted(it)}"


@pytest.mark.parametrize("c", CARTOES, ids=lambda c: c["id"])
def test_fontes_existem_no_catalogo_e_o_destino_e_uma_rota_do_front(c):
    assert c["fontes"] and set(c["fontes"]) <= CATALOGO
    rotas = re.findall(r'<Route (?:index|path="([^"]*)")', (ROOT / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8"))
    assert c["destino"]["to"].split("?")[0].lstrip("/") in set(rotas)
