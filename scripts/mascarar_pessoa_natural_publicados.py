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

O `asns.zip` do formato compactado (`core/layout.py`) também é regravado: cada membro JSON recebe a mesma regra, o ZIP novo mantém nomes, ordem e compressão
dos membros, entra por arquivo temporário e `replace`, e o original fica em `--copias/<data>/asns.zip`.

`--corrigir-manifesto` reconcilia `checksums` com o disco (a compactação foi feita depois do manifesto, sem atualizá-lo): remove as entradas `asns/<n>.json`
que não existem em disco **e estão dentro do `asns.zip`**, acrescenta `asns.zip` com o checksum atual (`sha256:...`) e confere todos os checksums contra o
disco. O que sumiu e não está no ZIP, e o que diverge, é só relatado (código de saída 2), nunca corrigido às cegas. Grava `manifesto_reconciliado` e uma
entrada em `correcoes`; sem mudança, nada é gravado. Sem `--aplicar`, mostra o que removeria e não confere os checksums (os arquivos ainda vão mudar).

    python3 scripts/mascarar_pessoa_natural_publicados.py DATA_DIR [--data AAAA-MM-DD ...] [--copias DIR] [--aplicar] [--corrigir-manifesto]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import pessoa_natural  # noqa: E402
from core.cpf import mascarar_snapshot  # noqa: E402
from core.integridade import sha256_arquivo  # noqa: E402


def _gravar_manifesto(caminho: Path, man: dict) -> None:
    tmp = caminho.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(tmp, caminho.stat().st_mode & 0o777)
    tmp.replace(caminho)


def _agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atualizar_manifesto(pub: Path, alterados: dict[str, str], titulares: int, zip_regravado: bool = False) -> None:
    caminho = pub / "manifest.json"
    man = json.loads(caminho.read_text(encoding="utf-8"))
    sums = man.get("checksums")
    if isinstance(sums, dict):
        for rel, sha in alterados.items():
            if rel in sums:
                sums[rel] = sha
        if zip_regravado and "asns.zip" in sums:         # o ZIP regravado por esta correção; divergência anterior não é "corrigida" aqui
            sums["asns.zip"] = sha256_arquivo(pub / "asns.zip")
    man["privacidade"] = {"pessoa_natural": pessoa_natural.VERSAO, "criterio": "natureza jurídica 213-5 (empresário individual) ou MEI",
                          "titulares": titulares, "posicao": pessoa_natural.POSICAO_REDUZIDA_A}
    man.setdefault("correcoes", []).append({
        "aplicado_em": _agora(),
        "arquivos": len(alterados),
        "descricao": ("Nome de empresário individual e de MEI trocado pelo nome fantasia (ou por \"Empresário individual\", com ASN e CNPJ mascarado) e ponto da "
                      "sede reduzido ao centróide do município, como a publicação passou a fazer. Nenhum outro campo foi alterado."),
    })
    _gravar_manifesto(caminho, man)


def reconciliar_manifesto(pub: Path, aplicar: bool) -> dict:
    """Reconcilia `checksums` do manifesto com o disco. Devolve {removidos, zip_adicionado, fora_do_zip, divergentes, ausentes, gravado}.

    Só remove `asns/<n>.json` ausente que esteja dentro do `asns.zip`; o resto é relatado. Os checksums são conferidos ao fim (só com `aplicar`)."""
    caminho = pub / "manifest.json"
    man = json.loads(caminho.read_text(encoding="utf-8"))
    sums = man.get("checksums")
    rel: dict = {"removidos": [], "zip_adicionado": False, "fora_do_zip": [], "divergentes": [], "ausentes": [], "gravado": False}
    if not isinstance(sums, dict):
        return rel
    zip_path = pub / "asns.zip"
    membros: set[str] = set()
    if zip_path.is_file():
        try:
            with zipfile.ZipFile(zip_path) as z:
                membros = set(z.namelist())
        except zipfile.BadZipFile:
            print(f"{pub.name}: asns.zip ilegível; nada removido do manifesto", flush=True)
    for chave in list(sums):
        if (pub / chave).exists():
            continue
        if chave.startswith("asns/") and chave[len("asns/"):] in membros:
            rel["removidos"].append(chave)
        else:
            rel["fora_do_zip"].append(chave)
    if membros and "asns.zip" not in sums and rel["removidos"]:
        rel["zip_adicionado"] = True
    if not aplicar:
        return rel
    if rel["removidos"] or rel["zip_adicionado"]:
        for chave in rel["removidos"]:
            del sums[chave]
        if rel["zip_adicionado"]:
            sums["asns.zip"] = sha256_arquivo(zip_path)
        man["manifesto_reconciliado"] = {"em": _agora(), "removidos": len(rel["removidos"]), "arquivo_compactado": "asns.zip",
                                         "descricao": "Lista de checksums reconciliada com o disco: entradas de asns/<n>.json absorvidas pelo asns.zip saíram e asns.zip entrou."}
        man.setdefault("correcoes", []).append({
            "aplicado_em": man["manifesto_reconciliado"]["em"], "arquivos": len(rel["removidos"]),
            "descricao": ("Manifesto reconciliado com o disco: o snapshot foi compactado em asns.zip depois do manifesto; saíram dos checksums as entradas dos "
                          "asns/<n>.json que estão dentro do ZIP e entrou o checksum de asns.zip. Nenhum documento foi alterado."),
        })
        _gravar_manifesto(caminho, man)
        rel["gravado"] = True
    for chave, sha in sums.items():
        alvo = pub / chave
        if not alvo.is_file():
            rel["ausentes"].append(chave)
        elif sha256_arquivo(alvo) != sha:
            rel["divergentes"].append(chave)
    return rel


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("data_dir", type=Path)
    ap.add_argument("--data", action="append", help="só estas datas (padrão: todas as publicadas)")
    ap.add_argument("--copias", type=Path, help="onde guardar os originais (padrão: DATA_DIR/../correcao-pessoa-natural-originais)")
    ap.add_argument("--aplicar", action="store_true", help="grava; sem isto, só simula")
    ap.add_argument("--corrigir-manifesto", action="store_true", help="reconcilia os checksums do manifesto com o disco (asns.zip no lugar dos asns/<n>.json ausentes)")
    a = ap.parse_args(argv)
    publicados = a.data_dir / "published"
    todas = sorted(d.name for d in publicados.iterdir() if d.is_dir() and (d / "manifest.json").exists())
    datas = a.data or todas
    copias = a.copias or a.data_dir.resolve().parent / "correcao-pessoa-natural-originais"
    indices: dict[str, pessoa_natural.Indice] = {}
    total, problemas = 0, 0
    for data in datas:
        idx = pessoa_natural.indice_do_snapshot(a.data_dir, data)
        for outra in reversed(todas):
            if idx:
                break
            idx = indices.get(outra) or pessoa_natural.indice_do_snapshot(a.data_dir, outra)
            indices[outra] = idx
        pub = publicados / data
        if not idx:
            print(f"{data}: sem cadastro em normalized/ (nada a mascarar)", flush=True)
        else:
            zip_path = pub / "asns.zip"
            antes = sha256_arquivo(zip_path) if zip_path.is_file() else None
            alterados = mascarar_snapshot(pub, gravar=a.aplicar, copia_em=(copias / data) if a.aplicar else None, indice=idx)
            zip_regravado = a.aplicar and antes is not None and sha256_arquivo(zip_path) != antes
            if a.aplicar and (alterados or "privacidade" not in json.loads((pub / "manifest.json").read_text(encoding="utf-8"))):
                _atualizar_manifesto(pub, alterados, len(idx.raizes), zip_regravado)
            total += len(alterados)
            exemplos = ", ".join(sorted(alterados)[:4]) + (" …" if len(alterados) > 4 else "")
            print(f"{data}: {len(alterados)} arquivo(s) {'regravado(s)' if a.aplicar else 'a regravar'}{': ' + exemplos if alterados else ''}", flush=True)
        if a.corrigir_manifesto:
            r = reconciliar_manifesto(pub, a.aplicar)
            ruins = len(r["fora_do_zip"]) + len(r["divergentes"]) + len(r["ausentes"])
            problemas += ruins
            print(f"{data}: manifesto: {len(r['removidos'])} entrada(s) {'removida(s)' if a.aplicar else 'a remover'} (dentro do asns.zip), "
                  f"asns.zip {'acrescentado' if r['zip_adicionado'] else 'sem mudança'}, {len(r['fora_do_zip'])} ausente(s) fora do zip, "
                  f"{len(r['divergentes'])} divergente(s), {len(r['ausentes'])} ausente(s) ao conferir", flush=True)
            for rotulo, itens in (("fora do zip", r["fora_do_zip"]), ("divergente", r["divergentes"]), ("ausente", r["ausentes"])):
                for chave in itens[:10]:
                    print(f"  {rotulo}: {chave}", flush=True)
    print(f"total: {total} {'(aplicado; originais em ' + str(copias) + ')' if a.aplicar else '(simulação: nada gravado)'}")
    if problemas:
        print(f"atenção: {problemas} entrada(s) do manifesto fora do zip, divergentes ou ausentes (não corrigidas)", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
