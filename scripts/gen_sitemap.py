#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Gera `config/paginas_publicas.json`: a lista de páginas que a API usa para montar
`/sitemap.xml` (índice), `/sitemap-paginas.xml`, `/sitemap-territorio.xml`, `robots.txt` e `llms.txt` com o domínio do `.env`
(`SITE_URL`, `core/site.py`). O arquivo não tem domínio: só caminhos.

As páginas saem do menu (`frontend/src/components/layout/menu.ts`, fonte única), mais as que o menu não lista; UFs e os ~5,5 mil
municípios (códigos do arquivo de centróides) vão no sitemap do território. ASNs, PTTs, operadoras, grupos e datacenters dependem
do snapshot e saem de `/sitemap-entidades.xml` (`api/routes/sitemap.py`). `tests/unit/test_sitemap.py` confere que o arquivo está em
dia; rode `python3 scripts/gen_sitemap.py` ao mudar o menu ou as rotas.

    python3 scripts/gen_sitemap.py          # regrava
    python3 scripts/gen_sitemap.py --check  # só confere (código 1 se diferente)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "frontend" / "public"
MENU = ROOT / "frontend" / "src" / "components" / "layout" / "menu.ts"
SAIDA = ROOT / "config" / "paginas_publicas.json"
ACESSO = ROOT / "frontend" / "src" / "auth" / "accessPolicy.ts"

# Páginas fora do menu que valem para buscadores (o menu já traz as de tema).
EXTRAS = ["/", "/sobre", "/privacidade", "/uso-aceitavel", "/acessibilidade",
          "/operadoras?servico=smp", "/operadoras?servico=stfc", "/operadoras?servico=seac"]
UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"]


def paginas_so_com_login() -> set[str]:
    """Rotas do SPA da classe `login` (`LOGIN_EXACT` em `accessPolicy.ts`, o espelho da política): um buscador não as abre, então não vão ao sitemap nem ao `llms.txt` (D9)."""
    m = re.search(r"const LOGIN_EXACT = new Set\(\[(.*?)\]\)", ACESSO.read_text(encoding="utf-8"), re.S)
    return set(re.findall(r"'([^']+)'", m.group(1))) if m else set()


def paginas_do_menu() -> list[dict]:
    """Itens do menu com rótulo e descrição (o E2E e este script leem `menu.ts` por expressão regular: um item por linha)."""
    itens = []
    for linha in MENU.read_text(encoding="utf-8").splitlines():
        m = re.search(r"rotulo: '([^']+)', to: '([^']+)'(?:, descricao: '([^']*)')?", linha)
        if m and "externo: true" not in linha:
            itens.append({"rotulo": m.group(1), "caminho": m.group(2), "descricao": m.group(3) or ""})
    return itens


def dados() -> dict:
    restritas = paginas_so_com_login()
    menu = [i for i in paginas_do_menu() if i["caminho"] not in restritas]
    vistos, paginas = set(), []
    for c in [*EXTRAS[:1], *(i["caminho"] for i in menu), *EXTRAS[1:]]:
        if c not in vistos:
            vistos.add(c)
            paginas.append(c)
    municipios = sorted(json.loads((PUBLIC / "municipios-centroides.json").read_text(encoding="utf-8")))
    return {"gerado_por": "scripts/gen_sitemap.py", "menu": menu, "paginas": paginas,
            "territorio": [*(f"/uf/{u}" for u in UFS), *(f"/municipio/{m}" for m in municipios)]}


def texto() -> str:
    return json.dumps(dados(), ensure_ascii=False, indent=1) + "\n"


def main(argv: list[str]) -> int:
    t = texto()
    if "--check" in argv:
        return 0 if SAIDA.exists() and SAIDA.read_text(encoding="utf-8") == t else 1
    SAIDA.write_text(t, encoding="utf-8")
    print(f"gravado {SAIDA.relative_to(ROOT)} ({len(t) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
