# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — os locks Python (requirements*.lock) acompanham os requirements*.txt e têm hash em toda entrada.

Se falhar depois de mudar um requirements*.txt (inclusive num PR do Dependabot): `bash scripts/travar-dependencias.sh`."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_PIN = re.compile(r"^([A-Za-z0-9_.-]+)(?:\[[^\]]*\])?==([^\s\\;]+)", re.M)


def _nome(n: str) -> str:
    return re.sub(r"[-_.]+", "-", n).lower()


def _pins(arquivo: str) -> dict[str, str]:
    return {_nome(m.group(1)): m.group(2) for m in _PIN.finditer((ROOT / arquivo).read_text())}


def _entradas(arquivo: str) -> list[str]:
    """Cada requisito do lock, com as linhas de continuação (hashes) juntas."""
    texto = (ROOT / arquivo).read_text().replace("\\\n", " ")
    return [linha for linha in texto.splitlines() if _PIN.match(linha)]


def test_diretas_estao_nos_locks_com_a_mesma_versao():
    prod, dev = _pins("requirements.lock"), _pins("requirements-dev.lock")
    for nome, versao in _pins("requirements.txt").items():
        assert prod.get(nome) == versao, f"{nome}=={versao} (requirements.txt) ≠ requirements.lock: regrave os locks"
        assert dev.get(nome) == versao, f"{nome}=={versao} (requirements.txt) ≠ requirements-dev.lock: regrave os locks"
    for nome, versao in _pins("requirements-dev.txt").items():
        assert dev.get(nome) == versao, f"{nome}=={versao} (requirements-dev.txt) ≠ requirements-dev.lock: regrave os locks"


def test_dev_instala_as_mesmas_versoes_de_producao():
    prod, dev = _pins("requirements.lock"), _pins("requirements-dev.lock")
    assert {n: (v, dev.get(n)) for n, v in prod.items() if dev.get(n) != v} == {}


def test_toda_entrada_tem_hash():
    for arquivo in ("requirements.lock", "requirements-dev.lock"):
        sem = [e.split()[0] for e in _entradas(arquivo) if "--hash=sha256:" not in e]
        assert sem == [], f"{arquivo}: sem hash: {sem}"


def test_imagem_e_ci_instalam_pelo_lock_com_hashes():
    assert "pip install --no-cache-dir --require-hashes -r requirements.lock" in (ROOT / "Dockerfile.api").read_text()
    assert "--require-hashes -r requirements-dev.lock" in (ROOT / "scripts" / "ci.sh").read_text()
