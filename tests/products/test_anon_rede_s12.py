# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cookie inventado ou fingerprint aleatório não livram da cobrança por IP; sessão real e IP diferente não são afetados."""
import dataclasses

from tests.products.api_contract import ANON


def test_cobranca_pela_rede_do_ip(api, monkeypatch):
    from api.auth import access_policy as pol
    rota = next(r for r in ("/api/v1/asns/1/paths", "/api/v1/snapshots/diff", "/api/v1/query/schema", "/api/v1/hilbert/v4")
                if pol.classify("GET", r, {}, None).cls == pol.METERED)
    original = api.app.state.anon_config
    monkeypatch.setattr(api.app.state, "anon_config", dataclasses.replace(original, limit_minutes=1, api_client_cost_seconds=30))
    ip = {"X-Real-IP": "198.51.100.77"}
    vistos = []
    for i in range(3):
        api.cookies.set("anon_sid", f"inventado-{i}")                # cookie que o servidor nunca emitiu
        vistos.append(api.get(rota, headers={**ip, "X-Device-Fingerprint": f"fp-aleatorio-{i}"}).status_code)
    api.cookies.clear()
    assert vistos[-1] == 403, vistos                                  # 60 s de orçamento, 30 s por pedido: o 3º já passa do limite
    assert api.get(rota, headers={"X-Real-IP": "198.51.100.78"}).status_code != 403    # outro IP: conta própria
    assert api.get(rota, headers=ANON).status_code != 403
