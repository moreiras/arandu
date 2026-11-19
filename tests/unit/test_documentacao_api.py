# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""O Swagger não pode depender de script embutido (a CSP do nginx não tem 'unsafe-inline'),
e o script de inicialização não pode terminar em `.js` (o nginx do frontend manda `*.js` aos arquivos estáticos)."""
import re

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import documentacao


def _cliente() -> TestClient:
    app = FastAPI(docs_url=None)
    app.include_router(documentacao.router)
    return TestClient(app)


def test_pagina_do_swagger_nao_tem_script_embutido_e_usa_sri():
    html = _cliente().get("/api/v1/docs").text
    scripts = re.findall(r"<script([^>]*)>(.*?)</script>", html, flags=re.S)
    assert scripts and all(corpo.strip() == "" and "src=" in attrs for attrs, corpo in scripts)
    assert all("integrity=" in attrs for attrs, _ in scripts if "cdn.jsdelivr.net" in attrs)
    srcs = [re.search(r'src="([^"]+)"', a).group(1) for a, _ in scripts]
    locais = [s for s in srcs if s.startswith("/")]
    assert locais and not any(s.endswith(".js") for s in locais)


def test_script_de_inicializacao_e_javascript():
    r = _cliente().get("/api/v1/docs/iniciar")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/javascript")
    assert "SwaggerUIBundle" in r.text and "/api/v1/openapi.json" in r.text
