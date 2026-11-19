# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — nada no repositório usa os atalhos `collector/`, `enrich/` e `analysis/`.

Pré-condição para apagar as três pastas: se este teste passa, a remoção só tira os próprios atalhos
(e o `test_shims_renomeacao.py`, que os exercita). Vale para código Python, scripts, Docker, compose e catálogo."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PASTAS = ("collector", "enrich", "analysis")
USO = re.compile(rf"(?:^\s*(?:from|import)\s+|-m\s+|python3?\s+)(?:{'|'.join(PASTAS)})(?:\.|\s|$)", re.M)
EXTENSOES = {".py", ".sh", ".yaml", ".yml", ".toml", ".cfg", ".ini"}
IGNORAR = {".git", ".venv-mcp", ".venv", "node_modules", "__pycache__", "data", "frontend"}
LIVRES = {"tests/unit/test_shims_renomeacao.py", "tests/unit/test_sem_uso_dos_atalhos.py", "scripts/codemod_1_2_2.py"}


def _arquivos():
    for p in ROOT.rglob("*"):
        rel = p.relative_to(ROOT)
        if rel.parts[0] in IGNORAR or rel.parts[0] in PASTAS or str(rel) in LIVRES:
            continue
        if p.is_file() and (p.suffix in EXTENSOES or p.name.startswith("Dockerfile")):
            yield rel, p


def test_nenhum_arquivo_usa_collector_enrich_analysis():
    achados = []
    for rel, p in _arquivos():
        try:
            texto = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        achados += [f"{rel}: {m.group(0).strip()}" for m in USO.finditer(texto)]
    assert not achados, "use o nome novo (sources.<id>.collect / .enrich, products.*):\n" + "\n".join(achados)
