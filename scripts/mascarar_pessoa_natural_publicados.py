# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Aplica a regra de pessoa natural (D1, PT-11) aos snapshots **já publicados**: nome fantasia ou rótulo no lugar do nome civil de EI/MEI e ponto da sede
no centróide do município (`core.pessoa_natural`).

A publicação passou a fazer isso no fechamento de cada snapshot (`core.cpf.mascarar_snapshot` com o índice de pessoa natural). A API e o MCP já trocam o nome
e o ponto na saída de qualquer snapshot, mas os arquivos antigos ainda os trazem (e as camadas de mapa estáticas são servidas como estão). Para cada data este
script regrava os arquivos que mudam, guarda os originais em `--copias/<data>/`, atualiza os checksums do manifesto, grava `privacidade.pessoa_natural` e acrescenta
uma entrada em `correcoes`. O índice vem de `normalized/<data>/summary/`; data sem `normalized/` (retenção) usa o da data mais recente que o tenha.
Idempotente. Sem `--aplicar` só simula. Reinicie a API depois: ela guarda em memória o que já leu.

    python3 scripts/mascarar_pessoa_natural_publicados.py DATA_DIR [--data AAAA-MM-DD ...] [--copias DIR] [--aplicar]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import pessoa_natural  # noqa: E402
from core.cpf import mascarar_snapshot  # noqa: E402


def _atualizar_manifesto(pub: Path, alterados: dict[str, str], titulares: int) -> None:
    caminho = pub / "manifest.json"
    man = json.loads(caminho.read_text(encoding="utf-8"))
    sums = man.get("checksums")
    if isinstance(sums, dict):
        for rel, sha in alterados.items():
            if rel in sums:
                sums[rel] = sha
    man["privacidade"] = {"pessoa_natural": pessoa_natural.VERSAO, "criterio": "natureza jurídica 213-5 (empresário individual) ou MEI",
                          "titulares": titulares, "posicao": pessoa_natural.POSICAO_REDUZIDA_A}
    man.setdefault("correcoes", []).append({
        "aplicado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "arquivos": len(alterados),
        "descricao": ("Nome de empresário individual e de MEI trocado pelo nome fantasia (ou por \"Empresário individual\", com ASN e CNPJ mascarado) e ponto da "
                      "sede reduzido ao centróide do município, como a publicação passou a fazer. Nenhum outro campo foi alterado."),
    })
    tmp = caminho.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(tmp, caminho.stat().st_mode & 0o777)
    tmp.replace(caminho)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("data_dir", type=Path)
    ap.add_argument("--data", action="append", help="só estas datas (padrão: todas as publicadas)")
    ap.add_argument("--copias", type=Path, help="onde guardar os originais (padrão: DATA_DIR/../correcao-pessoa-natural-originais)")
    ap.add_argument("--aplicar", action="store_true", help="grava; sem isto, só simula")
    a = ap.parse_args(argv)
    publicados = a.data_dir / "published"
    todas = sorted(d.name for d in publicados.iterdir() if d.is_dir() and (d / "manifest.json").exists())
    datas = a.data or todas
    copias = a.copias or a.data_dir.resolve().parent / "correcao-pessoa-natural-originais"
    indices: dict[str, pessoa_natural.Indice] = {}
    total = 0
    for data in datas:
        idx = pessoa_natural.indice_do_snapshot(a.data_dir, data)
        for outra in reversed(todas):
            if idx:
                break
            idx = indices.get(outra) or pessoa_natural.indice_do_snapshot(a.data_dir, outra)
            indices[outra] = idx
        if not idx:
            print(f"{data}: sem cadastro em normalized/ (nada a fazer)", flush=True)
            continue
        pub = publicados / data
        alterados = mascarar_snapshot(pub, gravar=a.aplicar, copia_em=(copias / data) if a.aplicar else None, indice=idx)
        if a.aplicar and (alterados or "privacidade" not in json.loads((pub / "manifest.json").read_text(encoding="utf-8"))):
            _atualizar_manifesto(pub, alterados, len(idx.raizes))
        total += len(alterados)
        exemplos = ", ".join(sorted(alterados)[:4]) + (" …" if len(alterados) > 4 else "")
        print(f"{data}: {len(alterados)} arquivo(s) {'regravado(s)' if a.aplicar else 'a regravar'}{': ' + exemplos if alterados else ''}", flush=True)
    print(f"total: {total} {'(aplicado; originais em ' + str(copias) + ')' if a.aplicar else '(simulação: nada gravado)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
