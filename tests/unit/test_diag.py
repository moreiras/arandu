# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — api/diag.py: tamanho de objetos, estimativa por amostragem e relatório do Store."""
from types import SimpleNamespace

from api import diag


def _docs(n):
    return [{"asn": i, "name": f"AS{i} Telecom", "prefixes": [f"10.{i % 255}.0.0/24"] * 3, "meta": {"a": i, "b": "x" * 20}}
            for i in range(n)]


def test_deep_size_nao_conta_duas_vezes_o_mesmo_objeto():
    shared = {"k": "v" * 1000}
    once, ok = diag.deep_size([shared])
    twice, _ = diag.deep_size([shared, shared])
    assert ok and twice < once + 200          # a 2ª referência custa só o ponteiro da lista


def test_deep_size_respeita_o_orcamento_de_nos():
    size, complete = diag.deep_size(_docs(5000), budget=100)
    assert not complete and size > 0


def test_estimativa_por_amostragem_fica_perto_do_valor_exato():
    data = _docs(3000)
    exact, _ = diag.deep_size(data)
    est, estimated = diag.estimate_size(data, sample=100)
    assert estimated and 0.7 * exact < est < 1.3 * exact


def test_colecao_pequena_e_medida_por_inteiro():
    est, estimated = diag.estimate_size(_docs(10), sample=64)
    assert not estimated and est == diag.deep_size(_docs(10))[0]


def test_relatorio_do_store_acha_datas_e_ordena_pelo_maior():
    store = SimpleNamespace(
        base="x",
        _asn_map={"2026-10-11": {i: d for i, d in enumerate(_docs(2000))}, "2026-10-04": {i: d for i, d in enumerate(_docs(10))}},
        _ixp_geo_cache={("2026-10-11", "sp", "prefixes"): {"features": []}},
        _pequeno={"nao-e-data": 1},
        _nao_container=5,
        publico=[1, 2, 3],
    )
    leve = diag.store_report(store)
    assert leve["datas_residentes"] == ["2026-10-04", "2026-10-11"]
    nomes = {c["nome"] for c in leve["caches"]}
    assert nomes == {"_asn_map", "_ixp_geo_cache", "_pequeno"}            # só atributos privados que são coleções
    assert all("bytes_estimados" not in c for c in leve["caches"])         # o modo leve não mede bytes

    fundo = diag.store_report(store, deep=True, sample=32)
    assert fundo["caches"][0]["nome"] == "_asn_map"
    por_data = fundo["caches"][0]["por_data"]
    assert por_data["2026-10-11"]["entradas"] == 2000 and por_data["2026-10-04"]["entradas"] == 10
    assert por_data["2026-10-11"]["bytes_estimados"] > 50 * por_data["2026-10-04"]["bytes_estimados"] / 100


def test_processo_tem_rss_e_threads():
    p = diag.process_info()
    assert p["pid"] > 0 and p["threads"] >= 1
    assert p.get("rss_bytes", p.get("rss_pico_bytes", 0)) > 0
    assert "objetos_rastreados_gc" not in p and "objetos_rastreados_gc" in diag.process_info(deep=True)


def test_collect_limita_a_amostra():
    store = SimpleNamespace(_a={"2026-10-11": _docs(100)})
    r = diag.collect(store, None, deep=True, sample=100000)
    assert r["amostra"] == 512 and r["profundo"] and r["duracao_ms"] >= 0


def test_caches_de_modulo_acham_colecoes_e_lru_cache():
    import functools
    import sys
    import types

    mod = types.ModuleType("api._modulo_de_teste")
    mod.GRANDE = {i: [i] * 20 for i in range(2000)}
    mod.PEQUENO = {"a": 1}
    mod.VAZIO = {}

    @functools.lru_cache(maxsize=8)
    def f(x):
        return x * 2

    f(1), f(2)
    mod.f = f
    sys.modules["api._modulo_de_teste"] = mod
    try:
        rows = {r["nome"]: r for r in diag.module_caches_report(deep=True, sample=32, limit=500)}
    finally:
        del sys.modules["api._modulo_de_teste"]
    assert rows["api._modulo_de_teste.GRANDE"]["bytes_estimados"] > rows["api._modulo_de_teste.PEQUENO"]["bytes_estimados"]
    assert rows["api._modulo_de_teste.f"]["tipo"] == "lru_cache" and rows["api._modulo_de_teste.f"]["entradas"] == 2
    assert "api._modulo_de_teste.VAZIO" not in rows


def test_histograma_de_tipos_tem_dict_e_list():
    nomes = {h["tipo"] for h in diag.type_histogram(limit=30)}
    assert {"dict", "list"} <= nomes


def test_pymalloc_stats_reporta_blocos_vivos_e_total():
    data = [{"k": "x" * 50} for _ in range(5000)]       # algo vivo para o alocador contar
    st = diag.pymalloc_stats()
    assert data
    if st is None:                                          # PyPy / stderr sem descritor (captura do pytest)
        return
    assert st["bytes_em_blocos_vivos"] > 0 and st["bytes_arenas_reservadas"] >= st["bytes_em_blocos_vivos"]
    assert 0 <= st["fragmentacao_pct"] < 100
