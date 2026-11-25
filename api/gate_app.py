# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Processo dedicado do gate de acesso (`auth_request` do nginx).

Roda no mesmo container da API, em outra porta (8001) e em OUTRO processo: o gate é
consultado a cada requisição de API (inclusive as servidas do cache do nginx) e não
pode esperar o event loop da API, que às vezes fica ocupado com consultas pesadas
(`/map/query`, índices grandes). Importa só o módulo de decisão de acesso — não
carrega o Store nem os índices —, por isso é leve (dezenas de MB).

Compartilha com a API o banco SQLite de sessões anônimas (WAL) e a mesma decisão
(`api/auth/access.py`). Se este processo falhar, o nginx segue em fail-open.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from api.auth.access import gate_response, limite_anonimo
from api.auth.anon_session import load_anon_config
from api.auth.config import init_auth_config


class _SnapshotLister:
    """Substituto mínimo do Store para `recent_dates` (lista de snapshots publicados)."""

    def __init__(self, base: Path) -> None:
        self._pub = base / "published"

    def list_snapshots(self) -> list[str]:
        if not self._pub.exists():
            return []
        return sorted(
            d.name for d in self._pub.iterdir()
            if d.is_dir() and (d / "manifest.json").exists()
        )


@asynccontextmanager
async def _lifespan(app: Starlette):
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    app.state.auth_config = init_auth_config(data_dir)
    app.state.anon_config = load_anon_config()
    app.state.store = _SnapshotLister(data_dir)
    yield


async def gate(request: Request) -> Response:
    return gate_response(request)


async def limite(request: Request) -> Response:
    """A resposta 429 do orçamento esgotado, para o `@anon_limit` do nginx (que no `auth_request` só vê 403) repassar com o `Retry-After` certo."""
    return limite_anonimo()


async def health(request: Request) -> Response:
    return JSONResponse({"status": "ok", "service": "gate"})


app = Starlette(
    routes=[Route("/auth/gate", gate, methods=["GET"]), Route("/auth/limite", limite, methods=["GET"]), Route("/health", health, methods=["GET"])],
    lifespan=_lifespan,
)
