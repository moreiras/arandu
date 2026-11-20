# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Teto de memória da API (api/memoria.py): datas residentes, expurgo por data e modo crítico perto do teto do contêiner."""
import threading

import pytest

from api import memoria
from api.memoria import GuardaMemoria, caches_do_store, data_da_chave, expurgar

L, A, B, C = "2026-11-13", "2026-11-06", "2026-10-30", "2026-10-23"


@pytest.mark.parametrize("chave, data", [
    (L, L), ((L, "qualidade/x.json.gz"), L), (f"{L}/scm_asn_set", L), (f"{L}/sp", L), ((140706638193792, L), L),
    (f"/data/published/{L}", L), ("sp", None), (13335, None), ((24, 16777216), None), ("20261113", None),
])
def test_data_da_chave(chave, data):
    assert data_da_chave(chave) == data


class _LRUcomTrava:                       # como o _SafeLRU do Store: __slots__ e RLock
    __slots__ = ("_cache", "_lock")

    def __init__(self):
        self._cache, self._lock = {}, threading.RLock()


class _Servico:
    def __init__(self):
        self._cache = {(L, "a.json"): 1, (A, "a.json"): 2, (B, "a.json"): 3}
        self._lru = _LRUcomTrava()
        self._lru._cache.update({f"{L}/sp/v4": 1, f"{B}/sp/v4": 2})


class _Store:
    def __init__(self):
        self._asn_detail_cache = {L: {1: {}}, A: {1: {}}, B: {1: {}}, C: {1: {}}}
        self._servico = _Servico()
        self._outorgas = {"scm": _Servico(), "smp": _Servico()}            # dicionário de serviços, não de dados
        self._bgp_horaria_cache = {L: 1, A: 2, B: 3, C: 4}
        self._sem_data = {"sp": 1, 13335: 2}

    def list_snapshots(self):
        return [C, B, A, L]


_Servico.__module__ = _LRUcomTrava.__module__ = _Store.__module__ = "api.teste"


def _nomes(caches):
    return sorted(c.nome for c in caches)


def test_descobre_caches_em_servicos_slots_e_dicionarios_de_servicos():
    nomes = _nomes(caches_do_store(_Store()))
    assert "store._asn_detail_cache" in nomes
    assert "store._servico._cache" in nomes and "store._servico._lru._cache" in nomes
    assert "store._outorgas['scm']._cache" in nomes and "store._outorgas['smp']._lru._cache" in nomes
    assert "store._outorgas" not in nomes                                   # o contêiner de serviços não é cache


def test_expurgo_mantem_residentes_protegidas_e_chaves_sem_data():
    s = _Store()
    removidas = expurgar(caches_do_store(s), {L, A}, {"_bgp_horaria_cache": {B}})
    assert set(s._asn_detail_cache) == {L, A}
    assert set(s._servico._cache) == {(L, "a.json"), (A, "a.json")}
    assert set(s._servico._lru._cache) == {f"{L}/sp/v4"}
    assert set(s._outorgas["scm"]._cache) == {(L, "a.json"), (A, "a.json")}
    assert set(s._bgp_horaria_cache) == {L, A, B}                          # semana protegida fica; C sai
    assert s._sem_data == {"sp": 1, 13335: 2}
    assert removidas[B] >= 4 and removidas[C] == 2


def _guarda(store, uso=None, teto=None, **env):
    leitura = {"uso": uso, "teto": teto}
    g = GuardaMemoria(store, lambda: L, leitor=lambda: (leitura["uso"], leitura["teto"]))
    g.protegidas = lambda residentes: {}
    return g, leitura


def test_residentes_mais_recente_e_a_ultima_data_consultada(monkeypatch):
    monkeypatch.setenv("API_DATAS_EXTRAS", "1")
    s = _Store()
    g, _ = _guarda(s)
    assert g.residentes() == {L, A}                                         # começa com a anterior
    g.registrar(C)
    assert g.residentes() == {L, C}
    g.registrar(L)                                                          # a mais recente não ocupa vaga
    assert g.residentes() == {L, C}
    g.passada()
    assert set(s._asn_detail_cache) == {L, C}


def test_alivio_expurga_tudo_que_nao_e_a_mais_recente(monkeypatch):
    s = _Store()
    g, leitura = _guarda(s, uso=82, teto=100)
    g.passada()
    assert set(s._asn_detail_cache) == {L}
    assert not g.critico


def test_critico_expurga_tudo_e_nao_recusa():
    s = _Store()
    g, leitura = _guarda(s, uso=91, teto=100)
    g.passada()
    assert s._asn_detail_cache == {} and g.critico and g.expurgos_totais == 1   # inclusive a mais recente: relida sob demanda
    assert s._sem_data == {"sp": 1, 13335: 2}
    assert not hasattr(g, "recusa")
    leitura["uso"] = 85                                                      # entre alívio e crítico: a mais recente volta a ficar
    s._asn_detail_cache.update({L: {1: {}}, A: {1: {}}})
    g.passada()
    assert set(s._asn_detail_cache) == {L} and not g.critico


def test_data_em_uso_nao_e_expurgada_no_meio_da_consulta(monkeypatch):
    monkeypatch.setenv("API_DATAS_EXTRAS", "0")
    s = _Store()
    g, _ = _guarda(s)
    with g.usando(C):
        g.passada()
        assert C in s._asn_detail_cache and g.estado()["em_uso"] == [C]
    g.passada()                                                              # terminou: só a mais recente
    assert set(s._asn_detail_cache) == {L}
    with g.usando(L), g.usando(None):                                        # a mais recente e sem data: nada a proteger
        assert g.estado()["em_uso"] == []


def test_snapshot_novo_mantem_o_antigo_mais_recente_residente():
    s = _Store()
    atual = {"v": A}
    g = GuardaMemoria(s, lambda: atual["v"], leitor=lambda: (None, None))
    g.protegidas = lambda residentes: {}
    atual["v"] = L
    g.passada()
    assert g.residentes() == {L, A}
    assert set(s._asn_detail_cache) == {L, A}


def test_store_real_tem_os_caches_por_data_conhecidos(tmp_path):
    from api.store import Store
    nomes = _nomes(caches_do_store(Store(tmp_path)))
    for esperado in ("store._asn_detail_cache", "store._docs._cache", "store._bgp._bgp_horaria_cache", "store._rpki._vrp_cache",
                     "store._qualidade._cache", "store._outorgas['scm']._cache"):
        assert esperado in nomes, esperado


def test_middleware_serve_data_antiga_mesmo_no_critico_e_a_protege_durante_a_requisicao(app_client):
    from fastapi.testclient import TestClient
    _, app, _ = app_client
    client = TestClient(app, raise_server_exceptions=False)               # sem Store no fixture: só importa não ser 503
    s = _Store()
    g, _ = _guarda(s, uso=95, teto=100)
    g.passada()
    vistos = []
    original = g.usando

    def usando(data):
        vistos.append(data)
        return original(data)
    g.usando = usando
    antes = getattr(app.state, "guarda_memoria", None)
    app.state.guarda_memoria = g
    try:
        assert client.get(f"/api/v1/ixps?date={A}").status_code != 503
        assert client.get("/health").status_code != 503
        assert vistos == [A] and list(g._acessos)[-1] == A
    finally:
        app.state.guarda_memoria = antes


def test_desligada(monkeypatch):
    monkeypatch.setenv("API_MEMORIA", "0")
    assert not memoria.ligado()


def test_semanas_da_serie_bgp_das_residentes_ficam():
    class _Bgp:
        def bgp_stability_datas_semanais(self, d, weeks):
            return {L: [A, L], A: [B, A]}.get(d, [d])
    _Bgp.__module__ = "api.teste"
    s = _Store()
    s._bgp = _Bgp()
    g = GuardaMemoria(s, lambda: L, leitor=lambda: (None, None))
    g.passada()
    assert set(s._bgp_horaria_cache) == {L, A, B}                            # B é semana da série de A (residente)


def test_prefixo_mcp_le_as_proprias_variaveis(monkeypatch):
    monkeypatch.setenv("MCP_DATAS_EXTRAS", "0")
    monkeypatch.setenv("MCP_MEMORIA_ALIVIO_PCT", "70")
    g = GuardaMemoria(_Store(), lambda: L, leitor=lambda: (None, None), prefixo="MCP")
    assert g.extras == 0 and g.alivio == 0.70 and g.residentes() == {L}
    monkeypatch.setenv("MCP_MEMORIA", "0")
    monkeypatch.setenv("API_MEMORIA", "1")                                   # o conftest desliga as duas
    assert not memoria.ligado("MCP") and memoria.ligado("API")


def test_laco_em_thread_acorda_com_registrar(monkeypatch):
    monkeypatch.setenv("API_MEMORIA", "1")                                   # o conftest a desliga; o laço só roda ligado
    s = _Store()
    g, _ = _guarda(s)
    g.intervalo = 60                                                          # só o registrar acorda a thread a tempo
    feito = threading.Event()
    original = g.passada

    def passada():
        r = original()
        if set(s._asn_detail_cache) == {L, C}:
            feito.set()
        return r
    g.passada = passada
    g.iniciar_thread()
    g.registrar(C)
    assert feito.wait(5)


def test_mcp_tools_rodam_dentro_da_guarda():
    from mcp_server import app as mcp_app
    s = _Store()
    g, _ = _guarda(s)
    vistos = []

    class _G:
        def usando(self, data):
            vistos.append(data)
            return g.usando(data)

    class _T:
        def __init__(self, fn):
            self.fn = fn

    class _Srv:
        class _tool_manager:
            _tools = {"x": _T(lambda date=None, asn=None: (date, asn))}
    assert mcp_app._com_guarda(_Srv, _G()) == 1
    assert _Srv._tool_manager._tools["x"].fn(date=A, asn=1) == (A, 1) and vistos == [A]
    assert mcp_app._com_guarda(_Srv, _G()) == 0                             # não envolve duas vezes


