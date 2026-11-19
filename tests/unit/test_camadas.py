# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — regras de camada (primeiro degrau de um import-linter): a camada de produtos não importa `api` nem `publish`."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROIBIDOS = {"products": ("api", "publish", "mcp_server")}


def _imports(arquivo: Path) -> set[str]:
    achados: set[str] = set()
    for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
        if isinstance(no, ast.Import):
            achados |= {a.name.split(".")[0] for a in no.names}
        elif isinstance(no, ast.ImportFrom) and no.module and no.level == 0:
            achados.add(no.module.split(".")[0])
    return achados


def test_products_nao_importa_api_publish_nem_mcp():
    violacoes = []
    for camada, proibidos in PROIBIDOS.items():
        for arq in sorted((ROOT / camada).rglob("*.py")):
            ruins = _imports(arq) & set(proibidos)
            if ruins:
                violacoes.append(f"{arq.relative_to(ROOT)} importa {sorted(ruins)}")
    assert violacoes == [], "\n".join(violacoes)


def test_core_nao_importa_as_camadas_acima():
    violacoes = [f"{a.relative_to(ROOT)}: {sorted(_imports(a) & {'api', 'products', 'publish', 'sources', 'arandu'})}"
                 for a in sorted((ROOT / "core").rglob("*.py")) if _imports(a) & {"api", "products", "publish", "sources", "arandu"}]
    assert violacoes == [], "\n".join(violacoes)
