# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — limite de concorrência da API (api/concurrency.py): teto global, fila com prazo, isenções e devolução da vaga."""
import asyncio

import pytest

from api.concurrency import ConcurrencyLimitMiddleware


class AppLenta:
    """ASGI que trabalha `trabalho_s` antes de responder e `corpo_s` antes de terminar o corpo; conta quantos estão dentro."""

    def __init__(self, trabalho_s=0.05, corpo_s=0.0, falha=False):
        self.trabalho_s, self.corpo_s, self.falha = trabalho_s, corpo_s, falha
        self.dentro = self.pico = 0

    async def __call__(self, scope, receive, send):
        self.dentro += 1
        self.pico = max(self.pico, self.dentro)
        try:
            await asyncio.sleep(self.trabalho_s)
            if self.falha:
                raise RuntimeError("quebrou")
            await send({"type": "http.response.start", "status": 200, "headers": []})
            self.dentro -= 1
            await asyncio.sleep(self.corpo_s)
            await send({"type": "http.response.body", "body": b"ok"})
        except BaseException:
            raise


async def chamar(mw, path="/api/v1/x"):
    msgs = []

    async def receive():
        return {"type": "http.request"}

    async def send(m):
        msgs.append(m)

    await mw({"type": "http", "path": path, "headers": []}, receive, send)
    return msgs[0]["status"], dict(msgs[0].get("headers", []))


@pytest.mark.asyncio
async def test_nunca_passa_do_teto():
    app = AppLenta(trabalho_s=0.05)
    mw = ConcurrencyLimitMiddleware(app, max_inflight=3, queue_timeout_s=5)
    r = await asyncio.gather(*[chamar(mw) for _ in range(12)])
    assert all(s == 200 for s, _ in r)
    assert app.pico <= 3


@pytest.mark.asyncio
async def test_fila_estoura_o_prazo_com_503_e_retry_after():
    app = AppLenta(trabalho_s=0.4)
    mw = ConcurrencyLimitMiddleware(app, max_inflight=1, queue_timeout_s=0.1)
    r = await asyncio.gather(*[chamar(mw) for _ in range(3)])
    status = sorted(s for s, _ in r)
    assert status == [200, 503, 503]
    recusado = next(h for s, h in r if s == 503)
    assert recusado[b"retry-after"] == b"5" and recusado[b"cache-control"] == b"no-store"
    assert mw.rejeitados == 2


@pytest.mark.asyncio
async def test_vaga_volta_quando_a_resposta_comeca_e_nao_quando_o_corpo_termina():
    app = AppLenta(trabalho_s=0.02, corpo_s=0.5)              # corpo lento (cliente lento)
    mw = ConcurrencyLimitMiddleware(app, max_inflight=1, queue_timeout_s=0.3)
    r = await asyncio.gather(*[chamar(mw) for _ in range(3)])
    assert [s for s, _ in r] == [200, 200, 200]               # nenhum esperou o corpo do anterior


@pytest.mark.asyncio
async def test_vaga_volta_quando_a_aplicacao_quebra():
    mw = ConcurrencyLimitMiddleware(AppLenta(falha=True), max_inflight=1, queue_timeout_s=0.2)
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await chamar(mw)
    mw.app = AppLenta()
    assert (await chamar(mw))[0] == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/health", "/auth/me", "/api/v1/internal/diag"])
async def test_health_login_e_diagnostico_nao_entram_na_fila(path):
    app = AppLenta(trabalho_s=0.3)
    mw = ConcurrencyLimitMiddleware(app, max_inflight=1, queue_timeout_s=0.05)
    ocupa = asyncio.create_task(chamar(mw, "/api/v1/x"))      # segura a única vaga
    await asyncio.sleep(0.05)
    assert (await chamar(mw, path))[0] == 200
    await ocupa


@pytest.mark.asyncio
async def test_zero_desliga():
    app = AppLenta(trabalho_s=0.05)
    mw = ConcurrencyLimitMiddleware(app, max_inflight=0)
    await asyncio.gather(*[chamar(mw) for _ in range(10)])
    assert app.pico == 10
