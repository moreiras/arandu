# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Lock da execução do `arandu` por `flock` (kernel), não por pid.

Um lock por pid (`os.kill(pid, 0)`) não serve: cada execução roda num contêiner novo em que o próprio processo é o pid 1, e um lock
deixado por um contêiner morto com `pid 1` pareceria vivo para sempre, e toda rodada seguinte do cron falharia com
"já há uma execução em andamento". O `flock` é liberado pelo kernel quando o processo morre, em qualquer contêiner que compartilhe o diretório.
O arquivo nunca é apagado (apagar abre corrida entre quem já o abriu e quem recria); o conteúdo é só diagnóstico de quem o tem.
"""
from __future__ import annotations

import fcntl
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Optional


class LockOcupado(RuntimeError):
    pass


def _info(fd: int) -> dict:
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        return json.loads(os.read(fd, 4096).decode("utf-8") or "{}")
    except (OSError, ValueError):
        return {}


@contextmanager
def lock(path: Path, quem: str = "arandu"):
    """Impede duas execuções simultâneas; lança `LockOcupado` se outra tem o lock."""
    from datetime import datetime, timezone

    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            info = _info(fd)
            raise LockOcupado(f"já há uma execução em andamento (pid {info.get('pid', '?')}, início {info.get('inicio', '?')}, lock {path})") from None
        os.ftruncate(fd, 0)
        os.write(fd, json.dumps({"pid": os.getpid(), "inicio": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "quem": quem}).encode())
        try:
            yield
        finally:
            os.ftruncate(fd, 0)
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def ocupado(path: Path) -> Optional[dict]:
    """Se uma execução viva tem o lock, devolve o que ela gravou (`{}` se vazio); None se livre ou se o arquivo não existe."""
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return None
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            return _info(fd)
        fcntl.flock(fd, fcntl.LOCK_UN)
        return None
    finally:
        os.close(fd)
