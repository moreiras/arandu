# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — fuzz do OpenAPI (schemathesis) sobre a API servindo o dataset sintético.

Critério: nenhuma entrada gerada a partir do esquema pode produzir erro 5xx. Parâmetros inválidos devem
virar 4xx definidos (400/404/422), nunca exceção não tratada.
"""
import pytest
import schemathesis
from hypothesis import HealthCheck, settings

from api.main import app
from tests.products.api_contract import ALLOWED

# O esquema vem do próprio app (sem subir o lifespan na importação); as chamadas saem pelo cliente da fixture
# `api`, que mantém a API de pé sobre o dataset sintético.
schema = schemathesis.openapi.from_dict(app.openapi())


@pytest.fixture(autouse=True)
def _api_ativa(api):
    return api


@schema.parametrize()
@settings(max_examples=15, deadline=None, suppress_health_check=list(HealthCheck), database=None)
def test_nenhuma_entrada_do_esquema_gera_5xx(case, api):
    kw = case.as_transport_kwargs(base_url="http://testserver")
    kw["headers"] = {**(kw.get("headers") or {}), **ALLOWED}
    method = kw.pop("method")
    url = kw.pop("url")
    for k in ("timeout", "verify", "allow_redirects", "stream", "cert", "proxies"):
        kw.pop(k, None)
    r = api.request(method, url, **kw)
    assert r.status_code < 500, f"{case.method} {case.formatted_path} → {r.status_code}: {r.text[:200]}"
