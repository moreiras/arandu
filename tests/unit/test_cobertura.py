# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Matriz de cobertura API × MCP × UI: sem lacuna injustificada e `docs/cobertura.md` em dia."""
import importlib.util
from pathlib import Path

import pytest

from core import cobertura

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def matriz():
    spec = importlib.util.spec_from_file_location("gen_cobertura", ROOT / "scripts" / "gen_cobertura.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, *mod.levantar()


def test_nenhuma_lacuna_sem_justificativa_nem_erro_de_consistencia(matriz):
    _, linhas, erros, _ = matriz
    sem = [f"{l.rota}: {', '.join(l.lacunas)}" for l in linhas if l.lacunas]
    assert not erros and not sem, f"erros: {erros}; lacunas sem justificativa: {sem}"


def test_docs_cobertura_esta_atualizado(matriz):
    mod, _, _, md = matriz
    assert mod.DESTINO.read_text(encoding="utf-8") == md, "rode `python3 scripts/gen_cobertura.py`"


def test_pendencias_usam_o_marcador_pendente(matriz):
    _, linhas, _, _ = matriz
    for l in linhas:
        for j in (l.sem_mcp, l.sem_ui):
            if j and cobertura.PENDENTE.match(j):
                assert j.startswith("pendente:"), f"{l.rota}: marque a pendência com `pendente:`, não com {j.split(':')[0]}"


# --- o motor, com dados controlados ------------------------------------------------------------------------------------------------

OPS = [("GET", "/a/{x}", False), ("GET", "/b", False), ("GET", "/velha", True), ("POST", "/c", False)]


def test_rota_sem_decisao_e_manual_sobrando_sao_erros():
    linhas, erros = cobertura.montar(OPS, "fetch('/api/v1/a/' + x)", {"GET /a/{x}": {"http": "GET /a/{x}", "mcp": "t"}, "GET /fantasma": {"http": "GET /fantasma", "mcp": "t"}})
    assert [l.rota for l in linhas] == ["GET /a/{x}"]                                    # alias deprecated e POST ficam de fora
    assert any("GET /b: rota sem decisão" in e for e in erros) and any("GET /fantasma" in e for e in erros)


def test_ui_detectada_pelo_codigo_e_sem_ui_obsoleto_e_erro():
    codigo = "get(`/api/v1/a/${id}`) ; get('/api/v1/b2')"
    linhas, erros = cobertura.montar(OPS[:2], codigo, {"GET /a/{x}": {"http": "GET /a/{x}", "mcp": "t", "sem_ui": "x"},
                                                         "GET /b": {"http": "GET /b", "sem_mcp": "pendente: depois"}})
    por = {l.rota: l for l in linhas}
    assert por["GET /a/{x}"].ui and not por["GET /b"].ui                                   # /b2 não é /b
    assert por["GET /b"].lacunas == ["ui"] and por["GET /b"].pendente
    assert any("'sem_ui' obsoleto" in e for e in erros)


def test_tool_inexistente_ou_collection_inexistente_e_erro():
    linhas, _ = cobertura.montar(OPS[:2], "", {"GET /a/{x}": {"http": "GET /a/{x}", "mcp": "nao_existe"}, "GET /b": {"http": "GET /b", "mcp": "query:xx"}})
    erros = cobertura.validar_tools(linhas, {"outra"}, {"yy"})
    assert len(erros) == 2


def test_manual_exige_exatamente_um_entre_mcp_e_sem_mcp(tmp_path):
    f = tmp_path / "m.yaml"
    f.write_text("- http: GET /x\n  mcp: a\n  sem_mcp: b\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exatamente um"):
        cobertura.carregar_manuais(f)


def test_marcador_de_pendencia_aceita_o_prefixo_numerico_como_alias():
    assert cobertura.PENDENTE.match("pendente: depois") and cobertura.PENDENTE.match("1.4.6: depois")
    assert not cobertura.PENDENTE.match("coberto por outorga_lista")
