# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""MCP_HOSTS_EXTRAS: sem ele, o MCP chamado por outro nome (ex.: o IP de um ambiente de teste) responde 421."""
import importlib


def test_hosts_extras_e_o_do_site_entram_na_protecao(monkeypatch):
    """O host do SITE_URL entra sempre; os de MCP_HOSTS_EXTRAS, normalizados. Nenhum domínio fixo."""
    import mcp_server.contexto as ctx
    from core.site import carregar
    monkeypatch.setattr(ctx, "SITE", carregar({"SITE_URL": "https://exemplo.example"}))
    assert {"exemplo.example", "www.exemplo.example"} <= set(ctx._hosts_extras())
    monkeypatch.setenv("MCP_HOSTS_EXTRAS", " 10.0.0.10 , EXEMPLO.example")
    assert "10.0.0.10" in ctx._hosts_extras() and ctx._hosts_extras().count("exemplo.example") == 1
    monkeypatch.delenv("MCP_HOSTS_EXTRAS")
    assert "10.0.0.10" not in ctx._hosts_extras()
