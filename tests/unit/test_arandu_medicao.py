# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — medição por etapa: pico de RSS do subprocesso (`wait4`), saída prefixada, relatório e `arandu memoria`."""
import json
from pathlib import Path

import pytest

from arandu import executor, medicao
from arandu.runner import FakeRunner, SubprocessRunner
from core.catalog.loader import load_catalog
from core.catalog.schema import Step

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def cat():
    return load_catalog(ROOT / "catalog")


def _etapa(modulo: str, args=None) -> Step:
    return Step(id="medida", nome="medida", ordem=1, modulo=modulo, args=args or [], politica_falha="opcional")


def test_subprocesso_mede_o_pico_de_rss(tmp_path):
    (tmp_path / "aloca_mem.py").write_text("x = bytearray(80 * 2**20)\nfor i in range(0, len(x), 4096):\n    x[i] = 1\n")
    r = SubprocessRunner({"PYTHONPATH": str(tmp_path)}).run(_etapa("aloca_mem"), "2026-11-22")
    assert r.rc == 0
    assert r.pico_mem_mb is not None and r.pico_mem_mb >= 80


def test_saida_do_filho_e_codigo_de_retorno(tmp_path, capfd):
    (tmp_path / "fala.py").write_text("import sys\nprint('linha um')\nprint('linha dois', file=sys.stderr)\nsys.exit(3)\n")
    r = SubprocessRunner({"PYTHONPATH": str(tmp_path)}, prefixar=True).run(_etapa("fala"), "2026-11-22")
    assert r.rc == 3 and r.motivo == "saída 3"
    saida = capfd.readouterr().out
    assert "[medida] linha um" in saida and "[medida] linha dois" in saida


def test_relatorio_guarda_o_maior_pico_entre_as_tentativas(cat, tmp_path):
    rel = executor.executar(cat, "2026-10-18", tmp_path, FakeRunner(picos={"ixbr_alice": 250}), only=["ixbr_alice"],
                            usar_lock=False, log=lambda *_: None, versao="t", sleep=lambda s: None)
    e = {x.id: x for x in rel.etapas}["ixbr_alice"]
    assert e.pico_mem_mb == 250
    gravado = json.loads(executor.caminho_relatorio(tmp_path, "2026-10-18").read_text())
    assert {x["id"]: x for x in gravado["etapas"]}["ixbr_alice"]["pico_mem_mb"] == 250


def _relatorio(base: Path, nome: str, etapas: list[dict]) -> None:
    p = base / "ops" / "runs" / nome
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"etapas": etapas}))


def test_resumo_da_memoria(cat, tmp_path):
    a = {"id": "ixbr_alice", "inicio": "2026-11-21T04:00:00Z", "pico_mem_mb": 200, "duracao_s": 170}
    _relatorio(tmp_path, "2026-11-21.json", [a, {"id": "anatel_scm", "inicio": "2026-11-21T05:00:00Z", "pico_mem_mb": 90}])
    _relatorio(tmp_path, "history/2026-11-21T040000.json", [a])          # a mesma execução: não conta duas vezes
    _relatorio(tmp_path, "continuo/2026-11-22.json", [{"id": "ixbr_alice", "inicio": "2026-11-22T06:00:00Z", "pico_mem_mb": 400}])
    linhas = {r["etapa"]: r for r in medicao.resumo(cat, tmp_path)}
    assert linhas["ixbr_alice"]["execucoes"] == 2 and linhas["ixbr_alice"]["pico_mb"] == 400
    assert linhas["ixbr_alice"]["situacao"] == "ACIMA do declarado"          # o catálogo declara 320
    assert linhas["anatel_scm"]["situacao"] == "sem declaração"
    assert "ixbr_alice" in medicao.texto(list(linhas.values()))
