# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — `?opcional=1`: 404 vira 204 só quando a página pede; o resto do contrato não muda."""
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api import main as principal


def _app():
    app = FastAPI()
    app.add_exception_handler(principal.StarletteHTTPException, principal._http_exception_handler)

    @app.get("/x")
    def x():
        raise HTTPException(404, "não achei")

    @app.get("/proibido")
    def proibido():
        raise HTTPException(403, "não")

    return TestClient(app)


def test_sem_o_parametro_404_continua_404():
    r = _app().get("/x")
    assert r.status_code == 404 and r.json() == {"detail": "não achei"}


def test_com_opcional_o_404_vira_204_sem_corpo_e_sem_cache():
    for v in ("1", "true"):
        r = _app().get(f"/x?opcional={v}")
        assert r.status_code == 204 and r.content == b"" and r.headers["cache-control"] == "no-store"


def test_opcional_nao_esconde_outros_erros():
    assert _app().get("/proibido?opcional=1").status_code == 403
    assert _app().get("/x?opcional=0").status_code == 404
