# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Os limites de uso em vigor, publicados em `GET /api/v1/limites`, no `llms.txt` e na página /dados.

Fonte única: nada aqui é número escrito à mão. Os valores vêm das constantes e da leitura do ambiente de `api/limites.py` (janelas da API e do
MCP, custo por rota), `api/auth/anon_session.py` (orçamento de sessão sem login e custo por chamada de script), `api/auth/access_policy.py`
(prévia e snapshots atuais), `api/contatos_cota.py` (contatos por conta) e `mcp_server/chave.py` (cota diária da chave de MCP). O que não se publica:
o limiar de sessões novas por rede (`anon_session.py`), o teto global e o da rede de contatos e a suspensão automática (ensinariam a esgotar a cota
dos demais). O nginx (rajada por segundo) é configuração da borda e não entra aqui.
"""
from __future__ import annotations

from api import contatos_cota, limites
from api.auth import anon_session, chaves_mcp
from api.auth.access_policy import N_DATAS_ATUAIS, PREVIEW_LIMIT

# rotas-exemplo de cada faixa de custo: o custo vem de `limites.custo_api`, não de uma tabela repetida
_EXEMPLOS_DE_CUSTO = ("/api/v1/asns", "/api/v1/query", "/api/v1/map/query")


def _chave_mcp() -> dict:
    from mcp_server import chave          # carregado na hora: o MCP é outro processo, e a API só lê as constantes dele

    cota = chave.cota_diaria()
    return {"ativa": chaves_mcp.ativa(), "cota_diaria": cota or None, "sem_teto_diario": cota == 0,
            "contagem": "requisições POST ao MCP por dia UTC"}


def limites_publicados() -> dict:
    cfg = anon_session.load_anon_config()
    custo = cfg.api_client_cost_seconds
    return {
        "sem_conta": {
            "identificacao": "rede de origem: IPv4 inteiro, IPv6 pelo prefixo /64",
            "orcamento_diario_segundos": cfg.limit_seconds,
            "custo_por_chamada_segundos": custo,
            "chamadas_medidas_por_dia": (cfg.limit_seconds // custo) if custo else None,
            "renovacao": "meia-noite UTC",
            "ao_esgotar": {"status": 429, "cabecalho": "Retry-After", "corpo": "anon_limit_reached"},
            "previa_linhas": PREVIEW_LIMIT,
            "snapshots_atuais": N_DATAS_ATUAIS,
        },
        "api": {
            "sem_conta": limites.janelas_efetivas("api", "anon"),
            "com_conta": limites.janelas_efetivas("api", "conta"),
            "custo_por_rota": {rota: limites.custo_api(rota) for rota in _EXEMPLOS_DE_CUSTO} | {"demais": limites.custo_api("/api/v1/")},
            "chave_na_rest": False,
        },
        "mcp": {
            "sem_chave": limites.janelas_efetivas("mcp", "anon"),
            "com_chave": limites.janelas_efetivas("mcp", "conta"),
            "chave": _chave_mcp(),
        },
        "contatos": contatos_cota.tetos_da_conta(),
    }
