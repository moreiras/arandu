# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — o OpenAPI versionado no frontend (entrada dos tipos gerados) acompanha as rotas da API."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_openapi_do_frontend_esta_atualizado():
    spec = importlib.util.spec_from_file_location("gen_openapi", ROOT / "scripts" / "gen_openapi.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    guardado = json.loads(mod.DESTINO.read_text(encoding="utf-8"))
    atual = json.loads(mod.gerar())
    # compara o contrato (operações e schemas), não o texto: o FastAPI do venv local e o da imagem de produção redigem detalhes diferentes
    assert _contrato(guardado) == _contrato(atual), "rotas mudaram: rode `python3 scripts/gen_openapi.py` e `bash scripts/front-test.sh --gen-tipos`"


def _contrato(o: dict) -> dict:
    return {
        "operacoes": {f"{m.upper()} {p}": (op.get("operationId"), sorted(x["name"] for x in op.get("parameters", [])))
                      for p, item in o["paths"].items() for m, op in item.items() if isinstance(op, dict)},
        "schemas": sorted(o.get("components", {}).get("schemas", {})),
    }
