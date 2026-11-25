# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — os callbacks OAuth (Google, LinkedIn, PeeringDB) gravam a versão vigente da política e a data do aceite."""
import hashlib
import hmac

import pytest

from api.auth import contas, router
from api.auth.politica import POLITICA_NAO_REGISTRADA, POLITICA_VERSAO_VIGENTE


class _Resp:
    def __init__(self, dados):
        self._d = dados
        self.status_code = 200
        self.text = ""

    def json(self):
        return self._d


def _cliente_falso(userinfo):
    class _C:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **k):
            return _Resp({"access_token": "t"})

        async def get(self, *a, **k):
            return _Resp(userinfo)

    return _C


def _estado(secret):
    dados = "nonce123:/"
    return f"{dados}:{hmac.new(secret.encode(), dados.encode(), hashlib.sha256).hexdigest()[:16]}"


@pytest.mark.parametrize("provedor", ["google", "linkedin", "peeringdb"])
def test_callback_grava_aceite(api, monkeypatch, provedor):
    cfg = api.app.state.auth_config
    email = f"aceite-{provedor}@example.org"
    monkeypatch.setattr(router.httpx, "AsyncClient", _cliente_falso({"email": email, "name": "Aceite"}))
    try:
        r = api.get(f"/auth/{provedor}/callback", params={"code": "c", "state": _estado(cfg.jwt_secret)}, follow_redirects=False)
        assert r.status_code in (302, 307) and "auth_token" in r.headers.get("set-cookie", "")
        c = contas.por_email(cfg.data_dir, email)
        assert c.provedor == provedor and c.politica_versao == POLITICA_VERSAO_VIGENTE and c.aceite_em
        assert c.politica_versao != POLITICA_NAO_REGISTRADA
    finally:
        c = contas.por_email(cfg.data_dir, email)
        if c:
            contas.apagar(cfg.data_dir, c.conta_id)
