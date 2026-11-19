# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Coleta de lixo do Python fora do caminho das requisições.

A API guarda o snapshot inteiro em objetos Python (milhões deles). A coleta completa automática (geração 2) percorre todos e para o
processo enquanto isso: com o snapshot aquecido, 1,2 a 1,6 s por coleta (medido num ambiente de teste: 3,9 milhões de objetos
rastreados em 2,1 GiB; a API real tem o dobro). No teste de carga elas apareciam como rajadas em que todas as requisições, até as
triviais (`/auth/me`), demoravam ~2 s ao mesmo tempo.

`gc.freeze()` move os objetos existentes para uma geração permanente que a coleta não percorre: depois do aquecimento, a coleta
seguinte levou 0,0 s. O que o tráfego acrescenta depois (caches sob demanda) é congelado de tempos em tempos, depois de uma coleta que só
percorre o que ainda não está congelado (barata). Na troca de snapshot, `descongelar()` devolve tudo à coleta, para o que for solto poder
ser liberado, e o aquecimento seguinte congela de novo.

Variáveis: `GC_CONGELAR` (padrão 1; 0 desliga tudo) e `GC_CONGELAR_INTERVALO_S` (padrão 600).
"""
from __future__ import annotations

import asyncio
import gc
import logging
import os
import time

_log = logging.getLogger("arandurape")


def ligado() -> bool:
    return os.environ.get("GC_CONGELAR", "1") != "0"


def congelar(motivo: str) -> None:
    """Coleta o que não está congelado e congela o resto."""
    if not ligado():
        return
    t0 = time.perf_counter()
    gc.collect()
    coleta = time.perf_counter() - t0
    gc.freeze()
    _log.info("heap congelado (%s): coleta de %.2f s, %d objetos na geração permanente", motivo, coleta, gc.get_freeze_count())


def descongelar() -> None:
    if ligado():
        gc.unfreeze()


async def congelar_depois(tarefas, motivo: str) -> None:
    """Espera o aquecimento terminar (com ou sem erro) e congela o que ele carregou."""
    await asyncio.gather(*[t for t in tarefas if t is not None], return_exceptions=True)
    congelar(motivo)


async def manter_congelado() -> None:
    intervalo = float(os.environ.get("GC_CONGELAR_INTERVALO_S", "600"))
    while ligado() and intervalo > 0:
        await asyncio.sleep(intervalo)
        congelar("periódico")
