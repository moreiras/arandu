#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Codemod da renomeação de pastas: move com `git mv`, reescreve referências e cria os shims.

    python3 scripts/codemod_1_2_2.py core|sources|products [--dry-run]

Mapeamento (a fonte da verdade do passo):
  core      collector/_common.py, _telnet.py          → core/common.py, core/telnet.py
  sources   collector/<id>.py                         → sources/<id>/collect.py
            enrich/<id>.py                            → sources/<id>/enrich.py
  products  analysis/bgp_parser.py                    → products/bgp_routes/build.py
            analysis/metrics.py                       → products/ixp_metrics/build.py
            analysis/routing_analysis.py              → products/routing_analysis/build.py
            analysis/bgp_stability.py                 → products/bgp_stability/build.py
            analysis/bgp_stability_deep.py            → products/bgp_stability/deep.py

Nada é apagado: no lugar de cada módulo movido fica um shim (alias do módulo novo + DeprecationWarning) por 4 semanas.
Arquivos históricos (CHANGELOG, decisões, planos, relatórios) não são reescritos.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HDR = """# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""

CORE = {"collector/_common.py": "core/common.py", "collector/_telnet.py": "core/telnet.py"}
PRODUCTS = {
    "analysis/bgp_parser.py": "products/bgp_routes/build.py",
    "analysis/metrics.py": "products/ixp_metrics/build.py",
    "analysis/routing_analysis.py": "products/routing_analysis/build.py",
    "analysis/bgp_stability.py": "products/bgp_stability/build.py",
    "analysis/bgp_stability_deep.py": "products/bgp_stability/deep.py",
}


def sources_map() -> dict[str, str]:
    m = {}
    for pasta, arq in (("collector", "collect"), ("enrich", "enrich")):
        for f in sorted((ROOT / pasta).glob("*.py")):
            if f.stem.startswith("_") or f.stem == "__init__":
                continue
            m[f"{pasta}/{f.name}"] = f"sources/{f.stem}/{arq}.py"
    return m


def mapa(fase: str) -> dict[str, str]:
    return {"core": CORE, "sources": sources_map(), "products": PRODUCTS}[fase]


def modulo(path: str) -> str:
    return path[:-3].replace("/", ".")


def pacote_e_nome(novo: str) -> tuple[str, str]:
    """'sources/x/collect.py' → ('sources.x', 'collect');  'core/common.py' → ('core', 'common')."""
    mod = modulo(novo)
    pai, _, nome = mod.rpartition(".")
    return pai, nome


# arquivos reescritos: código, scripts, configuração e documentação viva (não o histórico)
EXT = {".py", ".sh", ".yaml", ".yml", ".md", ".json", ".txt", ".ini", ".toml"}
NOMES = {"Dockerfile.api", "Dockerfile.frontend", ".dockerignore"}
EXCLUIR_PREFIXOS = ("data/", "frontend/node_modules/", ".git/", "docs/decisoes/", "CHANGELOG.md", "pendencias.md",
                    "relatorio-", "estudo-", "plano-", "scripts/codemod_1_2_2.py")
EXCLUIR_SUFIXOS = ("fontes.json",)           # gerado: `arandu docs` refaz


def arquivos_alvo() -> list[Path]:
    saida = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    out = []
    for rel in saida:
        if rel.startswith(EXCLUIR_PREFIXOS) or rel.endswith(EXCLUIR_SUFIXOS):
            continue
        p = ROOT / rel
        if p.suffix in EXT or p.name in NOMES or p.name.startswith("docker-compose"):
            if p.is_file():
                out.append(p)
    return out


def reescrever(texto: str, mv: dict[str, str]) -> str:
    # 1. `from <pasta> import a, b as c` → um import por nome
    def _from_import(m: re.Match) -> str:
        ind, pasta, corpo = m.group(1), m.group(2), m.group(3)
        corpo = corpo.strip().strip("()")
        corpo = re.sub(r"#.*", "", corpo)
        linhas, resto = [], []
        for item in [x.strip() for x in corpo.replace("\n", " ").split(",") if x.strip()]:
            nome, _, alias = item.partition(" as ")
            nome, alias = nome.strip(), alias.strip() or nome.strip()
            velho = f"{pasta}/{nome}.py"
            if velho in mv:
                pai, mod = pacote_e_nome(mv[velho])
                linhas.append(f"{ind}from {pai} import {mod} as {alias}" if alias != mod else f"{ind}from {pai} import {mod}")
            else:
                resto.append(item)
        if resto:
            linhas.append(f"{ind}from {pasta} import {', '.join(resto)}")
        return "\n".join(linhas) if linhas else m.group(0)

    texto = re.sub(r"^([ \t]*)from (collector|enrich|analysis) import (\([^)]*\)|[^\n(]+)$", _from_import, texto, flags=re.M)
    # 2. nomes pontuados (módulo.atributo, `python -m módulo`, strings de mock, YAML)
    pares = sorted(((modulo(v_), modulo(n_)) for v_, n_ in mv.items()), key=lambda x: -len(x[0]))
    for velho, novo in pares:
        texto = re.sub(rf"(?<![\w.]){re.escape(velho)}(?![\w])", novo, texto)
    # 3. caminhos de arquivo citados em documentação: collector/x.py → sources/x/collect.py
    for velho, novo in sorted(mv.items(), key=lambda x: -len(x[0])):
        texto = re.sub(rf"(?<![\w/]){re.escape(velho)}\b", novo, texto)
    return texto


SHIM = '''{hdr}"""Atalho de compatibilidade: este módulo foi movido para `{novo}`.

Use o nome novo.
"""
import importlib
import sys
import warnings

warnings.warn("{antigo} foi movido para {novo}; use o nome novo",
              DeprecationWarning, stacklevel=2)

if __name__ == "__main__":
    import runpy

    runpy.run_module("{novo}", run_name="__main__")
else:
    sys.modules[__name__] = importlib.import_module("{novo}")
'''

INIT = HDR + '"""{doc}"""\n'


def aplicar(fase: str, dry: bool) -> int:
    mv = mapa(fase)
    print(f"fase {fase}: {len(mv)} módulo(s) a mover")
    if dry:
        for a, b in mv.items():
            print(f"  {a} → {b}")
    if not dry:
        for velho, novo in mv.items():
            dest = ROOT / novo
            dest.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "mv", velho, novo], cwd=ROOT, check=True)
            # __init__ dos pacotes novos
            pai = dest.parent
            while pai != ROOT:
                ini = pai / "__init__.py"
                if not ini.exists():
                    ini.write_text(INIT.format(doc=f"Pacote `{pai.relative_to(ROOT).as_posix().replace('/', '.')}`."), encoding="utf-8")
                    subprocess.run(["git", "add", str(ini)], cwd=ROOT, check=True)
                pai = pai.parent
    # reescreve referências (antes de criar os shims, para não reescrevê-los)
    alterados = 0
    for p in arquivos_alvo():
        try:
            t = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        n = reescrever(t, mv)
        if n != t:
            alterados += 1
            if not dry:
                p.write_text(n, encoding="utf-8")
    print(f"  {alterados} arquivo(s) com referências reescritas")
    if not dry:
        for velho, novo in mv.items():
            p = ROOT / velho
            p.write_text(SHIM.format(hdr=HDR, antigo=modulo(velho), novo=modulo(novo)), encoding="utf-8")
            subprocess.run(["git", "add", str(p)], cwd=ROOT, check=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("fase", choices=["core", "sources", "products"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    return aplicar(a.fase, a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
