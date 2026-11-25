# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 (PT-21 / DADOS-E2): o exemplo de consulta da página /dados roda e responde à pergunta que faz.

O corpo vem do código do frontend (`lib/exemplosDados.ts`), com a UF trocada por uma que o dataset sintético tem (ele não tem o ES).
"""
import json
import re
from pathlib import Path

from tests.products.api_contract import ALLOWED
from tests.synth.world import T1

ROOT = Path(__file__).resolve().parents[2]


def _corpo(uf: str) -> dict:
    src = (ROOT / "frontend" / "src" / "lib" / "exemplosDados.ts").read_text(encoding="utf-8")
    bruto = re.search(r"CORPO_EXEMPLO_CONSULTA = '(\{.*\})'", src).group(1)
    corpo = json.loads(bruto)
    assert corpo["filter"]["value"] == "ES"
    corpo["filter"]["value"] = uf
    return corpo


def _linhas(api, uf: str) -> list[dict]:
    r = api.post("/api/v1/query/acessos_municipio", params={"date": T1}, json={"filter": {"field": "uf", "op": "eq", "value": uf}, "limit": 1000}, headers=ALLOWED)
    assert r.status_code == 200, r.text[:300]
    return r.json()["items"]


def test_exemplo_soma_os_acessos_por_operadora_na_uf_com_o_mes_de_referencia(api):
    uf = "SP"
    linhas = _linhas(api, uf)
    assert linhas, "o dataset sintético precisa ter acessos em SP"
    esperado: dict[str, int] = {}
    for x in linhas:
        esperado[x["empresa"]] = esperado.get(x["empresa"], 0) + x["acessos"]
    meses = {x["mes_referencia"] for x in linhas}
    assert len(meses) == 1 and None not in meses

    r = api.post("/api/v1/query/acessos_municipio", params={"date": T1}, json=_corpo(uf), headers=ALLOWED)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert d["snapshot_date"] == T1
    grupos = d["groups"]
    assert 0 < len(grupos) <= 5
    somas = [g["sum_acessos"] for g in grupos]
    assert somas == sorted(somas, reverse=True), "o exemplo ordena pela maior soma"
    assert somas[0] == max(esperado.values())
    for g in grupos:
        assert g["sum_acessos"] == esperado[g["key"]["empresa"]]
        assert g["key"]["mes_referencia"] == next(iter(meses)), "a resposta mostra o mês de referência do SICI"


def test_exemplo_nao_usa_operadoras_por_sede():
    """O exemplo antigo (`operadoras` por `uf_sede`) listava quem tem sede na UF, não quem atende lá: 467 linhas, 242 inativas (DADOS-E2)."""
    src = (ROOT / "frontend" / "src" / "lib" / "exemplosDados.ts").read_text(encoding="utf-8")
    pagina = (ROOT / "frontend" / "src" / "pages" / "DadosPage.tsx").read_text(encoding="utf-8")
    corpo = re.search(r"CORPO_EXEMPLO_CONSULTA = '(.*)'", src).group(1)
    assert "uf_sede" not in corpo and "/api/v1/query/acessos_municipio" in pagina and "/api/v1/query/operadoras" not in pagina
