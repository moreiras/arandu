# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Rotas pesadas (medidas): `/mercado/maiores` (~0,5 s por chamada, sem memória) e o índice da busca (~25 s, montado por
cada pedido simultâneo a frio)."""
import threading
import time
from types import SimpleNamespace


def test_indice_da_busca_montado_uma_vez_com_pedidos_simultaneos(monkeypatch):
    from api import busca
    chamadas = []

    def montar(store, d):
        chamadas.append(d)
        time.sleep(0.2)
        return []

    monkeypatch.setattr(busca, "montar", montar)
    monkeypatch.setattr(busca, "_CACHE", {})
    store = object()
    ts = [threading.Thread(target=busca.indice, args=(store, "2026-11-13")) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert chamadas == ["2026-11-13"]


def test_mercado_maiores_memorizado(monkeypatch):
    from api.routes import sici_indicadores as r
    from api.services import sici_indicadores as s
    calculos = []
    monkeypatch.setattr(s, "maiores", lambda dados, grupos, n, meses: calculos.append((n, meses)) or {"n": n, "meses": meses})
    monkeypatch.setattr(r, "_MAIORES", r._SafeLRU(maxsize=8))
    store = SimpleNamespace(resolve_date=lambda d: "2026-11-13", _load_sici=lambda d: {"serie_por_cnpj": {}}, grupos_societarios_overview=lambda d: [])
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(store=store)))
    a = r.mercado_maiores(req, None, 8, 24)
    assert r.mercado_maiores(req, None, 8, 24) is a and calculos == [(8, 24)]
    r.mercado_maiores(req, None, 5, 24)
    assert calculos == [(8, 24), (5, 24)]
