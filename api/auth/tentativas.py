# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Limite de tentativas inválidas de chave de MCP, em memória (reiniciar zera; o segredo tem 256 bits, o limite é contra carga).

Por cliente (hash diário do IP, IPv6 por /64; nunca o IP em claro): 10 falhas em 10 min bloqueiam por 15 min; reincidência dobra o bloqueio até
24 h. Global: 200 falhas em 10 min → só a chave inválida recebe 429; a válida passa (sem isso, saturar o global negaria serviço a todas as
chaves). O contador é por cliente, nunca por chave: ninguém trava a chave de outra pessoa errando de propósito.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable, Optional

JANELA_S = 600
FALHAS_POR_CLIENTE = 10
BLOQUEIO_S = 900
BLOQUEIO_MAX_S = 86400
FALHAS_GLOBAIS = 200


class LimiteTentativas:
    def __init__(self, relogio: Callable[[], float] = time.monotonic):
        self._t = relogio
        self._lock = threading.Lock()
        self._falhas: dict[str, deque[float]] = {}
        self._bloqueado_ate: dict[str, float] = {}
        self._reincidencias: dict[str, int] = {}
        self._globais: deque[float] = deque()

    def _podar(self, fila: deque, agora: float) -> None:
        while fila and fila[0] < agora - JANELA_S:
            fila.popleft()

    def espera(self, cliente: str) -> Optional[int]:
        """Segundos até poder tentar de novo (`Retry-After`), ou `None` se pode."""
        with self._lock:
            ate = self._bloqueado_ate.get(cliente)
            agora = self._t()
            if ate and ate > agora:
                return max(1, int(ate - agora))
            return None

    def saturado(self) -> bool:
        with self._lock:
            agora = self._t()
            self._podar(self._globais, agora)
            return len(self._globais) >= FALHAS_GLOBAIS

    def falha(self, cliente: str) -> None:
        with self._lock:
            agora = self._t()
            self._globais.append(agora)
            f = self._falhas.setdefault(cliente, deque())
            f.append(agora)
            self._podar(f, agora)
            if len(f) >= FALHAS_POR_CLIENTE:
                n = self._reincidencias.get(cliente, 0)
                self._reincidencias[cliente] = n + 1
                self._bloqueado_ate[cliente] = agora + min(BLOQUEIO_S * (2 ** n), BLOQUEIO_MAX_S)
                f.clear()

    def sucesso(self, cliente: str) -> None:
        with self._lock:
            self._falhas.pop(cliente, None)
