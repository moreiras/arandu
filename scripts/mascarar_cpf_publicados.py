# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Mascara o CPF embutido na razão social de EI/MEI nos snapshots **já publicados** (correção no lugar, por decisão do mantenedor).

A partir da 2.0.31 a máscara é feita na publicação (`core.cpf.mascarar_snapshot`, no fechamento do snapshot) e a API deixou de mascarar na
leitura; os snapshots publicados antes disso precisam passar por este script uma vez. Para cada data: mascara os arquivos (e as entradas
do `asns.zip` no formato compactado), guarda os originais em `--copias/<data>/`, atualiza no manifesto os checksums dos caminhos
alterados e acrescenta uma entrada em `correcoes`. Nada mais do snapshot muda. Idempotente: rodar de novo não altera nada.

Sem `--aplicar` só simula (conta o que mudaria). Rode com a API parada ou reinicie-a depois: ela guarda em memória o que já leu.

    python3 scripts/mascarar_cpf_publicados.py DATA_DIR [--data AAAA-MM-DD ...] [--copias DIR] [--aplicar]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.cpf import mascarar_snapshot  # noqa: E402


def _atualizar_manifesto(pub: Path, alterados: dict[str, str]) -> None:
    caminho = pub / "manifest.json"
    man = json.loads(caminho.read_text(encoding="utf-8"))
    sums = man.get("checksums")
    if isinstance(sums, dict):
        for rel, sha in alterados.items():
            if rel in sums:
                sums[rel] = sha
    man.setdefault("correcoes", []).append({
        "aplicado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "arquivos": len(alterados),
        "descricao": ("CPF embutido na razão social de empresário individual e MEI mascarado (***XXXXXX**) nos campos de nome, como a "
                      "publicação passou a fazer na versão 2.0.31. Nenhum outro campo foi alterado."),
    })
    tmp = caminho.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")       # o formato que publish/coleta_checks grava
    os.chmod(tmp, caminho.stat().st_mode & 0o777)
    tmp.replace(caminho)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("data_dir", type=Path)
    ap.add_argument("--data", action="append", help="só estas datas (padrão: todas as publicadas)")
    ap.add_argument("--copias", type=Path, help="onde guardar os originais (padrão: DATA_DIR/../correcao-cpf-originais)")
    ap.add_argument("--aplicar", action="store_true", help="grava; sem isto, só simula")
    a = ap.parse_args(argv)
    publicados = a.data_dir / "published"
    datas = a.data or sorted(d.name for d in publicados.iterdir() if d.is_dir() and (d / "manifest.json").exists())
    copias = a.copias or a.data_dir.resolve().parent / "correcao-cpf-originais"
    total = 0
    for data in datas:
        pub = publicados / data
        alterados = mascarar_snapshot(pub, gravar=a.aplicar, copia_em=(copias / data) if a.aplicar else None)
        if alterados and a.aplicar:
            _atualizar_manifesto(pub, alterados)
        total += len(alterados)
        exemplos = ", ".join(sorted(alterados)[:4]) + (" …" if len(alterados) > 4 else "")
        print(f"{data}: {len(alterados)} arquivo(s) {'mascarado(s)' if a.aplicar else 'a mascarar'}{': ' + exemplos if alterados else ''}",
              flush=True)
    print(f"total: {total} {'(aplicado; originais em ' + str(copias) + ')' if a.aplicar else '(simulação: nada gravado)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
