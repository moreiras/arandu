# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — os tetos de uso publicados em /dados e no Sobre (D9) são os padrões do código."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TS = (ROOT / "frontend" / "src" / "lib" / "tetos.ts").read_text(encoding="utf-8")


def _teto(nome: str) -> int:
    m = re.search(rf"\b{nome}:\s*(\d+)", TS)
    assert m, f"{nome} não está em frontend/src/lib/tetos.ts"
    return int(m.group(1))


def test_custo_por_chamada_e_orcamento_diario_sao_os_padroes_da_sessao_anonima(monkeypatch):
    for v in ("ANON_SESSION_LIMIT_MINUTES", "ANON_API_CLIENT_COST_SECONDS"):
        monkeypatch.delenv(v, raising=False)
    from api.auth.anon_session import load_anon_config
    cfg = load_anon_config()
    assert _teto("custoPorChamadaSegundos") == cfg.api_client_cost_seconds == 3
    assert _teto("orcamentoDiarioSegundos") == cfg.limit_seconds == 600


def test_limitadores_por_rede_da_api_e_do_mcp_sao_os_padroes():
    from api.limites import PADROES
    assert "120/minute" in PADROES["api"]["anon"] and "1500/hour" in PADROES["api"]["anon"] and "6000/day" in PADROES["api"]["anon"]
    assert (_teto("apiAnonimoPorMinuto"), _teto("apiAnonimoPorHora"), _teto("apiAnonimoPorDia")) == (120, 1500, 6000)
    assert "60/minute" in PADROES["mcp"]["anon"] and "1000/hour" in PADROES["mcp"]["anon"] and "5000/day" in PADROES["mcp"]["anon"]
    assert (_teto("mcpAnonimoPorMinuto"), _teto("mcpAnonimoPorHora"), _teto("mcpAnonimoPorDia")) == (60, 1000, 5000)


def test_cota_diaria_do_mcp_com_chave(monkeypatch):
    monkeypatch.delenv("MCP_COTA_DIARIA", raising=False)
    from mcp_server import chave
    assert chave.COTA_DIARIA_PADRAO == chave.cota_diaria() == _teto("mcpCotaDiariaComChave") == 1000


def test_identificacao_por_rede_ipv4_inteiro_e_ipv6_64():
    from api.auth.anon_session import rede_do_ip
    assert rede_do_ip("203.0.113.9") == "203.0.113.9"
    assert rede_do_ip("2001:db8:a:b:1:2:3:4") == rede_do_ip("2001:db8:a:b:ffff::1") == "2001:db8:a:b::/64"


def test_uso_aceitavel_publica_os_tetos_do_codigo():
    """PT-12b: o texto aprovado de /uso-aceitavel cita 600 s, 3 s e a rede (IPv4 inteiro ou IPv6 /64), os mesmos números de `lib/tetos.ts`."""
    uso = " ".join((ROOT / "frontend" / "src" / "pages" / "UsoAceitavel.tsx").read_text(encoding="utf-8").split())
    assert f"o orçamento diário é de {_teto('orcamentoDiarioSegundos')} s e cada chamada de script custa {_teto('custoPorChamadaSegundos')} s" in uso
    assert "429 com Retry-After até a meia-noite UTC. A rede é o IPv4 inteiro ou o prefixo IPv6 /64." in uso


def test_sobre_e_dados_publicam_os_tetos_e_o_aviso_do_link_de_citacao():
    for pagina in ("Sobre.tsx", "DadosPage.tsx"):
        assert "<TetosDeUso" in (ROOT / "frontend" / "src" / "pages" / pagina).read_text(encoding="utf-8"), pagina
    comp = (ROOT / "frontend" / "src" / "components" / "TetosDeUso.tsx").read_text(encoding="utf-8")
    for trecho in ("TETOS.custoPorChamadaSegundos", "TETOS.orcamentoDiarioSegundos", "IPv6 pelo prefixo /64", "TETOS.mcpCotaDiariaComChave", "Retry-After", "meia-noite UTC"):
        assert trecho in comp, trecho
    sobre = (ROOT / "frontend" / "src" / "pages" / "Sobre.tsx").read_text(encoding="utf-8")
    assert "abre sem login enquanto o snapshot estiver entre os dois mais recentes" in sobre
    assert "snapshots anteriores podem ser consultados individualmente" not in sobre          # a frase prometia o que o corte da política desmente (INST-E1)
