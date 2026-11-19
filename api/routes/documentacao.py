# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Swagger UI em `/api/v1/docs` sem script embutido.

A página que o FastAPI gera inicia o Swagger com um `<script>` embutido, e a CSP do nginx (`script-src 'self'
https://cdn.jsdelivr.net`, sem `'unsafe-inline'`) o bloqueia: a página ficava em branco. Aqui a inicialização vai num script servido
pela própria API (`'self'`) e a biblioteca vem do jsDelivr numa versão fixa, com SRI. A CSP não muda. Fora do OpenAPI."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response

router = APIRouter()

VERSAO = "5.17.14"
_CDN = f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{VERSAO}"
_SRI_JS = "sha384-wmyclcVGX/WhUkdkATwhaK1X1JtiNrr2EoYJ+diV3vj4v6OC5yCeSu+yW13SYJep"
_SRI_CSS = "sha384-wxLW6kwyHktdDGr6Pv1zgm/VGJh99lfUbzSn6HNHBENZlCN7W602k9VkGdxuFvPn"
_CACHE = {"Cache-Control": "public, max-age=3600"}

_INICIAR = """window.addEventListener('load', function () {
  window.ui = SwaggerUIBundle({
    url: '/api/v1/openapi.json',
    dom_id: '#swagger-ui',
    layout: 'BaseLayout',
    deepLinking: true,
    showExtensions: true,
    showCommonExtensions: true,
    presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
  });
});
"""


def pagina(titulo: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="stylesheet" href="{_CDN}/swagger-ui.css" integrity="{_SRI_CSS}" crossorigin="anonymous">
</head>
<body>
<div id="swagger-ui"></div>
<script src="{_CDN}/swagger-ui-bundle.js" integrity="{_SRI_JS}" crossorigin="anonymous"></script>
<script src="/api/v1/docs/iniciar"></script>
</body>
</html>
"""


@router.get("/api/v1/docs", include_in_schema=False)
def swagger() -> HTMLResponse:
    from core.site import SITE
    return HTMLResponse(pagina(f"{SITE.nome} — documentação da API"), headers=_CACHE)


@router.get("/api/v1/docs/iniciar", include_in_schema=False)
def swagger_iniciar() -> Response:
    return Response(_INICIAR, media_type="application/javascript", headers=_CACHE)
