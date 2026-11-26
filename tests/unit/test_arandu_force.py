# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — `arandu run --force` chega aos argumentos das etapas que declaram `aceita_force`, e só a elas."""
import functools
import re
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from arandu import executor
from arandu.runner import FakeRunner
from core.catalog.loader import load_catalog
from core.catalog.schema import Step

ROOT = Path(__file__).resolve().parents[2]
CAT = load_catalog(ROOT / "catalog")
COM_FORCE = sorted(s.id for s in CAT.steps.values() if s.aceita_force)
SEM_FORCE = sorted(s.id for s in CAT.steps.values() if s.runner == "worker" and not s.aceita_force)


@functools.lru_cache(maxsize=None)
def _aceita_force(modulo: str) -> bool:
    """O parser do módulo lista `--force` no `--help` (sem rede). `--force-full` não conta: o argparse o aceitaria como abreviação
    de `--force`, com outro efeito."""
    r = subprocess.run([sys.executable, "-m", modulo, "--help"], cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, f"{modulo} --help falhou: {r.stderr[-300:]}"
    return re.search(r"--force(?![-\w])", r.stdout) is not None


def test_ha_etapas_nos_dois_grupos():
    assert COM_FORCE and SEM_FORCE


@pytest.mark.parametrize("etapa", COM_FORCE)
def test_etapa_que_declara_aceita_force_tem_modulo_que_aceita(etapa):
    """Repassar `--force` a um módulo sem a opção derrubaria a etapa no argparse (rc 2)."""
    s = CAT.steps[etapa]
    assert s.runner == "worker"
    assert _aceita_force(s.modulo), f"{etapa}: {s.modulo} não tem --force no argparse (--help); remova aceita_force ou acrescente a opção ao módulo"


def test_etapa_de_host_nunca_aceita_force():
    assert not [s.id for s in CAT.steps.values() if s.runner == "host" and s.aceita_force]
    with pytest.raises(ValidationError):
        Step(id="x", nome="x", ordem=1, runner="host", comando=["true"], aceita_force=True, politica_falha="opcional")


def _roda(tmp_path, only, **kw):
    runner = FakeRunner()
    executor.executar(CAT, "2026-10-18", tmp_path, runner, only=only, usar_lock=False, log=lambda *_: None,
                      sleep=lambda s: None, gravar_relatorio=False, **kw)
    return runner


def test_run_force_repassa_force_so_a_quem_aceita(tmp_path):
    com, sem = "saude_asn", "manifesto"
    assert CAT.steps[com].aceita_force and not CAT.steps[sem].aceita_force
    r = _roda(tmp_path, [com, sem], force=True)
    assert r.argv[com] == ["--date", "2026-10-18", "--asn-health-only", "--force"]
    assert "--force" not in r.argv[sem]


def test_run_sem_force_nao_repassa(tmp_path):
    r = _roda(tmp_path, ["saude_asn", "manifesto"])
    assert r.argv["saude_asn"] == ["--date", "2026-10-18", "--asn-health-only"]
    assert all("--force" not in a for a in r.argv.values())


def test_force_nao_duplica_e_nao_altera_o_catalogo(tmp_path):
    s = CAT.steps["saude_asn"]
    assert executor.com_force(executor.com_force(s)).args.count("--force") == 1
    assert "--force" not in s.args
