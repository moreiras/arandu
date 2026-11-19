# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Execução de uma etapa: subprocesso (produção) ou no próprio processo (compare/testes)."""
from __future__ import annotations

import importlib
import os
import signal
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Optional

from core.catalog.schema import Step


@dataclass
class Resultado:
    rc: int
    motivo: Optional[str] = None


def argv_da_etapa(step: Step, date: str) -> list[str]:
    return [a.replace("{date}", date) for a in step.args]


class SubprocessRunner:
    """Cada etapa é um `python -m <modulo> <args>` filho: isolação de memória por etapa."""

    def __init__(self, env: Optional[dict[str, str]] = None, python: Optional[str] = None):
        self.env = {**os.environ, **(env or {})}
        self.python = python or sys.executable

    def run(self, step: Step, date: str) -> Resultado:
        cmd = [self.python, "-m", step.modulo, *argv_da_etapa(step, date)]
        try:
            rc = subprocess.run(cmd, env=self.env, check=False).returncode
        except OSError as exc:
            return Resultado(127, f"não executou: {exc}")
        return Resultado(rc, None if rc == 0 else _motivo_da_saida(rc))


def _motivo_da_saida(rc: int) -> str:
    """Saída negativa = morte por sinal; o nome do sinal (SIGPIPE, SIGKILL…) é a primeira pista da causa."""
    if rc < 0:
        try:
            return f"saída {rc} (sinal {signal.Signals(-rc).name})"
        except ValueError:
            return f"saída {rc} (sinal {-rc})"
    return f"saída {rc}"


@contextmanager
def _ambiente(env: dict[str, str]):
    antigo = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        yield
    finally:
        for k, v in antigo.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class InProcessRunner:
    """Chama `<modulo>.main(argv)` no processo atual (permite aplicar mocks de configuração, como o replay)."""

    def __init__(self, env: Optional[dict[str, str]] = None):
        self.env = env or {}

    def run(self, step: Step, date: str) -> Resultado:
        mod = importlib.import_module(step.modulo)
        argv = argv_da_etapa(step, date)
        with _ambiente(self.env):
            try:
                rc = mod.main(argv)
            except SystemExit as exc:
                rc = exc.code if isinstance(exc.code, int) else (0 if exc.code in (None, 0) else 1)
            except Exception as exc:  # noqa: BLE001 — a etapa falhou; o executor decide pela política
                return Resultado(1, f"exceção: {type(exc).__name__}: {exc}")
        rc = 0 if rc is None else int(rc)
        return Resultado(rc, None if rc == 0 else f"saída {rc}")


class FakeRunner:
    """Para testes: `respostas` mapeia id da etapa → rc (padrão 0); registra as chamadas."""

    def __init__(self, respostas: Optional[dict[str, int]] = None, antes: Optional[Callable[[Step, str], None]] = None):
        self.respostas = respostas or {}
        self.chamadas: list[str] = []
        self.antes = antes

    def run(self, step: Step, date: str) -> Resultado:
        self.chamadas.append(step.id)
        if self.antes:
            self.antes(step, date)
        rc = self.respostas.get(step.id, 0)
        return Resultado(rc, None if rc == 0 else f"saída {rc}")
