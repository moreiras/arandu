# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — os tetos de uso publicados em /dados e no Sobre (D9) são os padrões do código."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _limites() -> dict:
    """Os valores que `GET /api/v1/limites` publica (PT-21): o front não repete número, então Uso aceitável e Sobre se conferem contra a rota."""
    from api.limites_publicos import limites_publicados
    return limites_publicados()


def test_custo_por_chamada_e_orcamento_diario_sao_os_padroes_da_sessao_anonima(monkeypatch):
    for v in ("ANON_SESSION_LIMIT_MINUTES", "ANON_API_CLIENT_COST_SECONDS"):
        monkeypatch.delenv(v, raising=False)
    from api.auth.anon_session import load_anon_config
    cfg = load_anon_config()
    d = _limites()["sem_conta"]
    assert d["custo_por_chamada_segundos"] == cfg.api_client_cost_seconds == 3
    assert d["orcamento_diario_segundos"] == cfg.limit_seconds == 600


def test_limitadores_por_rede_da_api_e_do_mcp_sao_os_padroes(monkeypatch):
    for v in ("API_ORCAMENTO_ANON", "MCP_ORCAMENTO_ANON"):
        monkeypatch.delenv(v, raising=False)
    from api.limites import PADROES
    d = _limites()
    assert [(j["limite"], j["janela"]) for j in d["api"]["sem_conta"]] == [(120, "minuto"), (1500, "hora"), (6000, "dia")]
    assert "120/minute" in PADROES["api"]["anon"] and "1500/hour" in PADROES["api"]["anon"] and "6000/day" in PADROES["api"]["anon"]
    assert [(j["limite"], j["janela"]) for j in d["mcp"]["sem_chave"]] == [(60, "minuto"), (1000, "hora"), (5000, "dia")]


def test_cota_diaria_do_mcp_com_chave(monkeypatch):
    monkeypatch.delenv("MCP_COTA_DIARIA", raising=False)
    from mcp_server import chave
    assert chave.COTA_DIARIA_PADRAO == chave.cota_diaria() == _limites()["mcp"]["chave"]["cota_diaria"] == 1000


def test_identificacao_por_rede_ipv4_inteiro_e_ipv6_64():
    from api.auth.anon_session import rede_do_ip
    assert rede_do_ip("203.0.113.9") == "203.0.113.9"
    assert rede_do_ip("2001:db8:a:b:1:2:3:4") == rede_do_ip("2001:db8:a:b:ffff::1") == "2001:db8:a:b::/64"


def test_uso_aceitavel_publica_os_tetos_do_codigo():
    """PT-12b: o texto aprovado de /uso-aceitavel cita 600 s, 3 s e a rede (IPv4 inteiro ou IPv6 /64); os números são os que a rota publica."""
    uso = " ".join((ROOT / "frontend" / "src" / "pages" / "UsoAceitavel.tsx").read_text(encoding="utf-8").split())
    d = _limites()["sem_conta"]
    assert f"o orçamento diário é de {d['orcamento_diario_segundos']} s e cada chamada de script custa {d['custo_por_chamada_segundos']} s" in uso
    assert "429 com Retry-After até a meia-noite UTC. A rede é o IPv4 inteiro ou o prefixo IPv6 /64." in uso


def test_sobre_e_dados_publicam_os_tetos_e_o_aviso_do_link_de_citacao():
    for pagina, componente in (("Sobre.tsx", "<TetosDeUso"), ("DadosPage.tsx", "<EscolhaSeuAcesso")):
        assert componente in (ROOT / "frontend" / "src" / "pages" / pagina).read_text(encoding="utf-8"), pagina
    comp = (ROOT / "frontend" / "src" / "components" / "TetosDeUso.tsx").read_text(encoding="utf-8")
    for trecho in ("useLimites", "orcamento_diario_segundos", "custo_por_chamada_segundos", "IPv6 pelo prefixo /64", "cota_diaria", "Retry-After", "meia-noite UTC"):
        assert trecho in comp, trecho
    sobre = (ROOT / "frontend" / "src" / "pages" / "Sobre.tsx").read_text(encoding="utf-8")
    assert "abre sem login enquanto o snapshot estiver entre os dois mais recentes" in sobre
    assert "snapshots anteriores podem ser consultados individualmente" not in sobre          # a frase prometia o que o corte da política desmente (INST-E1)


def test_dados_nao_traz_numero_de_limite_escrito_a_mao():
    """O quadro de /dados e o componente de limites lêem `/api/v1/limites`; nada de 600, 3 s, 120, 1.500 no front."""
    for f in ("components/TetosDeUso.tsx", "components/EscolhaSeuAcesso.tsx", "pages/DadosPage.tsx"):
        src = (ROOT / "frontend" / "src" / f).read_text(encoding="utf-8")
        assert "useLimites" in src, f
        assert not re.search(r"(?<![-\w])(600|1[.,]?500|6[.,]?000|5[.,]?000)(?![-\w])", src), f
    assert not (ROOT / "frontend" / "src" / "lib" / "tetos.ts").exists()
