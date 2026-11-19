# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Congelamento do heap (api/heap.py): depois do aquecimento, a coleta completa não percorre o que foi carregado."""
import asyncio
import gc

from api import heap


def test_congela_depois_do_aquecimento_e_descongela(monkeypatch):
    monkeypatch.setenv("GC_CONGELAR", "1")
    carregado = [{"i": i, "lista": [i]} for i in range(50_000)]          # o "snapshot"
    try:
        async def aquecimento():
            await asyncio.sleep(0.01)
        async def cenario():
            await heap.congelar_depois([asyncio.create_task(aquecimento()), None], "teste")
        asyncio.run(cenario())
        assert gc.get_freeze_count() >= len(carregado)
    finally:
        heap.descongelar()
    assert gc.get_freeze_count() == 0


def test_desligado_nao_congela(monkeypatch):
    monkeypatch.setenv("GC_CONGELAR", "0")
    heap.congelar("teste")
    assert gc.get_freeze_count() == 0
