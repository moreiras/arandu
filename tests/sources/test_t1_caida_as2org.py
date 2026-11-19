# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — CAIDA as2org (via GraphQL do AS Rank): lista de ASNs do caida_asrank → lotes → normalizado, sem rede."""
import json

import pytest
import respx

from core.common import read_json_gz, write_json_gz
from sources.caida_as2org import collect as fonte


def _resposta(fx):
    return json.loads(fx("caida_as2org", "resposta.json").read_text(encoding="utf-8"))


def _preparar(base, date_str, asns):
    d = base / "normalized" / date_str / "summary"
    d.mkdir(parents=True, exist_ok=True)
    write_json_gz(d / "caida_asrank.json.gz", {"asns": {str(a): {} for a in asns}})


def test_extrair_normaliza_nome_e_omite_asn_sem_organizacao(fx):
    r = fonte.extrair(_resposta(fx))
    assert set(r) == {"64497", "64499", "64500"}
    assert r["64500"]["org_nome"] == "Rede Exemplo S.A." and r["64497"]["membros_total"] == 2 and r["64497"]["org_pais"] == "BR"


def test_erro_do_graphql_falha_alto():
    with pytest.raises(RuntimeError):
        fonte.extrair({"errors": [{"message": "x"}]})


@respx.mock
def test_run_consulta_em_lotes_e_grava(base, log, fx, date_str, monkeypatch):
    monkeypatch.setattr(fonte, "LOTE", 2)
    monkeypatch.setattr(fonte, "MINIMO_COBERTURA", 0.7)          # a resposta sintética deixa 1 de 4 ASNs sem organização
    _preparar(base, date_str, [64497, 64499, 64500, 64501])
    rota = respx.post(fonte.URL).respond(200, json=_resposta(fx))
    r = fonte.run(date_str, base, log, espera_s=0)
    assert rota.call_count == 2 and r["requisicoes"] == 2          # 4 ASNs, lotes de 2
    norm = read_json_gz(base / "normalized" / date_str / "summary" / "caida_as2org.json.gz")
    assert norm["asns"]["64497"]["org_id"] == "aaaaaaaa01" and norm["consultados"] == 4 and "CAIDA" in norm["citacao"]
    assert "64501" not in norm["asns"]
    assert fonte.HEADERS["User-Agent"].startswith("arandurape/")


@respx.mock
def test_cobertura_baixa_falha_alto(base, log, fx, date_str):
    _preparar(base, date_str, list(range(64000, 64040)))           # a resposta só conhece 3 ASNs
    respx.post(fonte.URL).respond(200, json=_resposta(fx))
    with pytest.raises(RuntimeError):
        fonte.run(date_str, base, log, espera_s=0)


def test_sem_caida_asrank_falha_alto(base, log, date_str):
    with pytest.raises(RuntimeError):
        fonte.run(date_str, base, log, espera_s=0)
