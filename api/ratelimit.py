# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Rate limiting (anti-abuso) via slowapi.

Um único `Limiter` compartilhado entre `api/main.py` (middleware + default) e os
routers (decorators `@limiter.limit(...)` em rotas caras/sensíveis). A chave é o IP
real do cliente, lido dos headers de proxy (a API fica atrás do nginx do frontend).

Armazenamento em memória (por processo) — suficiente para um único worker por
container; sem dependência externa.
"""

from __future__ import annotations

from fastapi import Request
from slowapi import Limiter


def client_ip(request: Request) -> str:
    """IP real do cliente (X-Real-IP do nginx, normalizado) — mesma função do guard de auth."""
    from api.auth.deps import client_ip as _client_ip

    return _client_ip(request)


def chave_do_cliente(request: Request) -> str:
    """Conta (cookie) ou rede (IPv6 pelo /64), como no orçamento geral (api/limites.py); sem a identidade no escopo, a rede do IP."""
    ident = getattr(request.state, "identidade", None)
    if ident is not None:
        return ident.chave
    from api.limites import hash_da_rede
    return "rede:" + hash_da_rede(client_ip(request))


# Limite padrão POR ROTA (o slowapi conta cada rota à parte); o teto por cliente somando todas as rotas é o orçamento de api/limites.py.
limiter = Limiter(key_func=chave_do_cliente, default_limits=["120/minute"])

# Limites nomeados (reutilizados nos decorators das rotas).
LIMIT_CONTACTS = "20/minute"   # /asns/{asn}/contacts — sensível
LIMIT_HEAVY = "30/minute"      # /map/query, /asns/{asn}/paths — caras
LIMIT_QUERY = "60/minute"      # /query: a home dispara 7 consultas e o explorador várias (era 30)

# O MCP não usa o slowapi (o endpoint é uma instância ASGI): o limite dele é o orçamento por cliente de api/limites.py (perfil "mcp").
