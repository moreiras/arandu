# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — coletas em paralelo: uma por destino, dentro do orçamento de memória, dependências antes, o resto sozinho e em ordem."""
import copy
import fcntl
import threading
import time
from pathlib import Path

import pytest

from arandu import executor
from arandu.runner import Resultado
from core.catalog.loader import load_catalog

ROOT = Path(__file__).resolve().parents[2]
# Destinos (catálogo): peeringdb_* → www.peeringdb.com; shodan → api.shodan.io; decix → lg.de-cix.net; manrs → manrs.org;
# siasg → dadosabertos.compras.gov.br. Memória declarada: siasg 544, shodan 256, decix 160, manrs 128, peeringdb 160.
COLETAS = ["peeringdb_ixps", "peeringdb_networks", "shodan_exposicao", "decix_alice", "manrs_participantes", "siasg_contratos"]


@pytest.fixture(autouse=True)
def _sem_bloqueio_por_disco(monkeypatch):
    monkeypatch.setenv("ARANDU_BLOQUEIO_DISCO_PCT", "101")


@pytest.fixture(scope="module")
def cat():
    return load_catalog(ROOT / "catalog")


class Relogio:
    """Runner que só dorme e anota quando cada etapa começou e terminou (threads)."""

    def __init__(self, dur=0.15, respostas=None):
        self.dur, self.respostas, self.intervalos, self.trava = dur, respostas or {}, {}, threading.Lock()

    def run(self, step, date):
        t0 = time.monotonic()
        time.sleep(self.dur)
        with self.trava:
            self.intervalos[step.id] = (t0, time.monotonic())
        rc = self.respostas.get(step.id, 0)
        return Resultado(rc, None if rc == 0 else f"saída {rc}")


def _juntas(r: Relogio, a: str, b: str) -> bool:
    (a0, a1), (b0, b1) = r.intervalos[a], r.intervalos[b]
    return a0 < b1 and b0 < a1


def _roda(cat, base, runner, only, **kw):
    return executor.executar(cat, "2026-11-22", base, runner, only=only, log=kw.pop("log", lambda *_: None), versao="t",
                             sleep=lambda s: None, **kw)


def test_em_serie_por_padrao(cat, tmp_path):
    r = Relogio(dur=0.02)
    rel = _roda(cat, tmp_path, r, COLETAS)
    ids = [e.id for e in rel.etapas]
    assert all(not _juntas(r, a, b) for i, a in enumerate(ids) for b in ids[i + 1:])
    assert sorted(r.intervalos, key=lambda k: r.intervalos[k][0]) == ids


def test_destinos_diferentes_juntos_e_o_mesmo_destino_nunca(cat, tmp_path):
    r = Relogio()
    rel = _roda(cat, tmp_path, r, COLETAS, paralelo=4, orcamento_mem_mb=10_000)
    assert [e.id for e in rel.etapas] == [s.id for s in executor.planejar(cat, COLETAS)]      # o relatório segue o plano
    assert all(e.status == executor.OK for e in rel.etapas)
    assert not _juntas(r, "peeringdb_ixps", "peeringdb_networks")                            # o mesmo host: uma de cada vez
    assert any(_juntas(r, a, b) for a in COLETAS for b in COLETAS if a < b)                  # hosts diferentes: ao mesmo tempo
    for t in sorted({t for v in r.intervalos.values() for t in v}):                          # no máximo 4 de uma vez
        assert sum(1 for a0, a1 in r.intervalos.values() if a0 <= t < a1) <= 4


def test_orcamento_de_memoria(cat, tmp_path):
    r = Relogio()
    _roda(cat, tmp_path, r, COLETAS, paralelo=6, orcamento_mem_mb=600)
    assert not _juntas(r, "siasg_contratos", "shodan_exposicao")             # 544 + 256 > 600
    mem = {s.id: s.memoria_mb for s in executor.planejar(cat, COLETAS)}
    for t in sorted({t for v in r.intervalos.values() for t in v}):          # em nenhum instante mais de 600 MB em curso
        assert sum(mem[k] for k, (a0, a1) in r.intervalos.items() if a0 <= t < a1) <= 600
    assert any(_juntas(r, a, b) for a in COLETAS for b in COLETAS if a < b)  # e ainda assim houve paralelismo


def test_etapa_sem_medicao_roda_sozinha_e_dependencia_espera(cat, tmp_path):
    c = copy.deepcopy(cat)
    c.steps["decix_alice"].depois_de = ["shodan_exposicao"]
    only = COLETAS + ["anatel_scm"]                                           # anatel_scm: sem memoria_mb declarada
    r = Relogio()
    _roda(c, tmp_path, r, only, paralelo=4, orcamento_mem_mb=10_000)
    assert all(not _juntas(r, "anatel_scm", b) for b in COLETAS)
    assert r.intervalos["decix_alice"][0] >= r.intervalos["shodan_exposicao"][1]


def test_falha_critica_nao_comeca_nada_novo(cat, tmp_path):
    c = copy.deepcopy(cat)
    c.steps["peeringdb_ixps"].politica_falha = "critica"
    r = Relogio(respostas={"peeringdb_ixps": 1})
    rel = _roda(c, tmp_path, r, COLETAS, paralelo=2, orcamento_mem_mb=10_000)
    st = {e.id: e for e in rel.etapas}
    assert rel.abortada_em == "peeringdb_ixps" and st["peeringdb_ixps"].status == executor.FALHA
    fim_falha = r.intervalos["peeringdb_ixps"][1]
    for e in rel.etapas:                     # o que estava rodando termina; o que não tinha começado não começa
        if e.id in r.intervalos:
            assert r.intervalos[e.id][0] < fim_falha
        else:
            assert e.status == executor.NAO_EXECUTADA


def test_lock_por_destino_vale_entre_processos(cat, tmp_path):
    """Outra execução (a trilha contínua, por exemplo) segura o host: a etapa espera, avisa e só começa depois."""
    arq = tmp_path / "ops" / "destinos" / "www.peeringdb.com.lock"
    arq.parent.mkdir(parents=True)
    f = open(arq, "a+")
    fcntl.flock(f, fcntl.LOCK_EX)
    msgs, r = [], Relogio(dur=0.01)
    th = threading.Thread(target=_roda, args=(cat, tmp_path, r, ["peeringdb_ixps"]), kwargs={"log": msgs.append})
    th.start()
    time.sleep(0.3)
    assert "peeringdb_ixps" not in r.intervalos
    solto = time.monotonic()
    fcntl.flock(f, fcntl.LOCK_UN)
    f.close()
    th.join(5)
    assert r.intervalos["peeringdb_ixps"][0] >= solto
    assert any("aguardando o destino www.peeringdb.com" in m for m in msgs)


def test_sem_orcamento_conhecido_roda_em_serie(cat, tmp_path, monkeypatch):
    monkeypatch.setattr(executor, "orcamento_memoria_mb", lambda env=None: None)
    msgs, r = [], Relogio(dur=0.02)
    _roda(cat, tmp_path, r, COLETAS, paralelo=4, log=msgs.append)
    ids = list(r.intervalos)
    assert all(not _juntas(r, a, b) for i, a in enumerate(ids) for b in ids[i + 1:])
    assert any("roda em série" in m for m in msgs)


def test_destinos_da_etapa(cat):
    d = lambda sid: executor.destinos_da_etapa(cat, cat.steps[sid])          # noqa: E731
    assert d("fulltable_routeviews") == {"archive.routeviews.org", "data.ris.ripe.net"}
    assert d("decix_alice") == {"lg.de-cix.net"}                             # URL seguida de texto no catálogo
    assert d("lg_ixbr") == {"lg.{ixp}.ix.br"}                                # molde: um destino só
    assert d("snapshot_completo") == set()


def test_orcamento_e_paralelo_do_ambiente():
    assert executor.orcamento_memoria_mb({"ARANDU_MEM_ORCAMENTO_MB": "2400"}) == 2400
    assert executor.paralelo_do_ambiente({"ARANDU_PARALELO": "4"}) == 4
    assert executor.paralelo_do_ambiente({"ARANDU_PARALELO": ""}) == 1
    assert executor.paralelo_do_ambiente({}) == 1
