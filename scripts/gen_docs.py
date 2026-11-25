#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Gera a documentação a partir do catálogo (o mesmo que `arandu docs`).

Saídas (todas determinísticas, sem data/hora; o catálogo é a única fonte):
  docs/fontes/<id>.md   docs/produtos/<id>.md   docs/dicionario.md   docs/licencas.md   docs/etapas.md   docs/fontes.json

Uso: python3 scripts/gen_docs.py [--check]
  --check   não grava: sai com 1 se algum arquivo gerado difere do que está no repositório.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.catalog.loader import Catalog, load_catalog, nao_verificados, uso_comercial_efetivo, validate  # noqa: E402
from core.catalog.schema import NAO_VERIFICADO, Campo, Product, Source  # noqa: E402

AVISO = "<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->\n"


def _cel(s: object) -> str:
    return str(s if s not in (None, "") else "—").replace("|", "\\|").replace("\n", " ")


def _lista(xs: list[str], vazio: str = "—") -> str:
    return ", ".join(f"`{x}`" for x in xs) if xs else vazio


def _campos(campos: list[Campo]) -> list[str]:
    if not campos:
        return ["_Sem dicionário de campos declarado._", ""]
    out = ["| Campo | Tipo | Significado | Tratamento | Publicado em |", "|---|---|---|---|---|"]
    for c in campos:
        nome = f"`{c.nome}`" + (" ⚠️ dado pessoal/contato" if c.sensivel else "")
        out.append(f"| {nome} | {_cel(c.tipo)} | {_cel(c.significado)} | {_cel(c.tratamento)} | "
                   f"{_cel('; '.join(c.publicado_em))} |")
    return out + [""]


def doc_fonte(s: Source, cat: Catalog) -> str:
    L = [AVISO, f"# {s.nome}", "", f"`{s.id}` · tipo **{s.tipo}** · {'ativa' if s.ativa else 'inativa'}", "", s.descricao, ""]
    L += ["## Resumo", "", "| | |", "|---|---|"]
    L.append(f"| Módulo / arquivo | `{s.modulo or s.arquivo}` |")
    L.append(f"| Publicável | {'sim' if s.publicavel else 'não'} (exposição: {s.exposicao}) |")
    if s.decisao_exposicao:
        L.append(f"| Decisão sobre a exposição | {_cel(s.decisao_exposicao)} |")
    if s.atribuicao:
        L.append(f"| Atribuição exigida | {_cel(s.atribuicao)} |")
    L.append(f"| Política de falha | {s.politica_falha} |")
    L.append(f"| Cadência (origem atualiza) | {s.cadencia.fonte_atualiza} |")
    L.append(f"| Coleta hoje → alvo | {s.cadencia.coleta_atual} → {s.cadencia.coleta} |")
    L.append(f"| Frescor máximo | {s.cadencia.frescor_maximo} |")
    L.append(f"| Chaves | {_lista(s.chaves)} |")
    L.append(f"| Entradas | {_lista(s.entradas)} |")
    if s.fixture:
        L.append(f"| Amostra de teste | `{s.fixture}` |")
    L.append("")
    if s.origem:
        o = s.origem
        L += ["## Origem e licença", "", f"- **URL:** {_cel(o.url)}", f"- **Formato:** {o.formato}",
              f"- **Licença:** {o.licenca}", f"- **Uso comercial:** `{o.uso_comercial}`"]
        if o.termos:
            L.append(f"- **Termos:** {o.termos}")
        if o.nota:
            L.append(f"- **Evidência / ressalvas:** {o.nota}")
        L.append("")
    L += ["## Saídas", ""]
    for rot, xs in (("Bruto (raw/)", s.saidas.bruto), ("Normalizado (normalized/)", s.saidas.normalizado),
                    ("Publicado direto (published/)", s.saidas.publicado)):
        if xs:
            L.append(f"- **{rot}:** {_lista(xs)}")
    L.append("")
    L += ["## Dicionário de campos", ""] + _campos(s.campos)
    L += ["## Limites", "", s.limites, ""]
    if s.retencao:
        r = s.retencao
        L += ["## Retenção", ""] + [f"- **{k}:** {v}" for k, v in
                                    (("bruto", r.bruto), ("normalizado", r.normalizado), ("publicado", r.publicado)) if v] + [""]
    usados = sorted(p.id for p in cat.products.values() if any(e.source == s.id for e in p.entradas))
    if usados or any(s.id in o.entradas for o in cat.sources.values()):
        deriv = sorted(o.id for o in cat.sources.values() if s.id in o.entradas)
        L += ["## Quem usa", ""]
        if deriv:
            L.append(f"- **Fontes derivadas:** {_lista(deriv)}")
        if usados:
            L.append(f"- **Produtos:** {_lista(usados)}")
        L.append("")
    if s.pendencias:
        L += ["## Pendências (nao_verificado)", ""] + [f"- {p}" for p in s.pendencias] + [""]
    return "\n".join(L)


def doc_produto(p: Product, cat: Catalog) -> str:
    L = [AVISO, f"# {p.nome}", "", f"`{p.id}` · produto", "", p.descricao, ""]
    L += ["## Resumo", "", "| | |", "|---|---|"]
    L.append(f"| Módulo (hoje) | `{p.modulo or '—'}` |")
    L.append(f"| Chaves de junção | {_lista(p.chaves_de_juncao)} |")
    L.append(f"| Cenários de teste (dataset sintético) | {_lista(p.cenarios_de_teste)} |")
    L.append("")
    L += ["## Entradas", ""]
    for e in p.entradas:
        if e.source:
            s = cat.sources.get(e.source)
            lic = f" — uso comercial: `{s.origem.uso_comercial}`" if s and s.origem else ""
            L.append(f"- fonte [{e.source}](../fontes/{e.source}.md){lic}")
        else:
            L.append(f"- produto [{e.product}]({e.product}.md)")
    L.append("")
    L += ["## Saídas", ""]
    for rot, xs in (("Normalizado", p.saidas.normalizado), ("Publicado", p.saidas.publicado), ("Fragmentos", p.saidas.fragmentos)):
        if xs:
            L.append(f"- **{rot}:** {_lista(xs)}")
    L.append("")
    L += ["## Dicionário de campos", ""] + _campos(p.campos)
    if p.limites:
        L += ["## Limites", "", p.limites, ""]
    if p.pendencias:
        L += ["## Pendências", ""] + [f"- {x}" for x in p.pendencias] + [""]
    return "\n".join(L)


def doc_dicionario(cat: Catalog) -> str:
    L = [AVISO, "# Dicionário de dados", "",
         "Todos os campos declarados no catálogo, por fonte e por produto. `⚠️` marca dado pessoal ou de contato.", ""]
    for kind, items in (("Fontes", sorted(cat.sources.values(), key=lambda x: x.id)),
                        ("Produtos", sorted(cat.products.values(), key=lambda x: x.id))):
        L += [f"## {kind}", ""]
        for it in items:
            if not it.campos:
                continue
            pasta = "fontes" if isinstance(it, Source) else "produtos"
            L += [f"### [{it.id}]({pasta}/{it.id}.md) — {it.nome}", ""] + _campos(it.campos)
    return "\n".join(L)


def doc_licencas(cat: Catalog) -> str:
    L = [AVISO, "# Licenças e uso comercial das fontes", "",
         "`permitido`: licença aberta que admite uso comercial (com atribuição, se exigida). `restrito`: há condição que limita "
         "ou exige autorização (não comercial, share-alike, AUP, EULA). `nao_verificado`: termos não localizados ou não lidos. "
         "Regra: um eventual recurso pago não pode depender de fonte `restrito` ou `nao_verificado`.", "",
         "`Efetivo` = o pior uso comercial entre a fonte e as suas entradas (restrito > nao_verificado > permitido).", "",
         "| Fonte | Tipo | Licença | Uso comercial | Efetivo | Publicável | Exposição | Termos |", "|---|---|---|---|---|---|---|---|"]
    for s in sorted(cat.sources.values(), key=lambda x: x.id):
        o = s.origem
        L.append(f"| [{s.id}](fontes/{s.id}.md) | {s.tipo} | {_cel(o.licenca if o else '—')} | "
                 f"{_cel(o.uso_comercial if o else '—')} | {uso_comercial_efetivo(cat, s.id)} | {'sim' if s.publicavel else 'não'} | {s.exposicao} | {_cel(o.termos if o else '')} |")
    cont: dict[str, int] = {}
    for s in cat.sources.values():
        k = uso_comercial_efetivo(cat, s.id)
        cont[k] = cont.get(k, 0) + 1
    L += ["", "## Totais (uso comercial efetivo)", ""] + [f"- `{k}`: {v}" for k, v in sorted(cont.items())] + [""]
    return "\n".join(L)


def doc_etapas(cat: Catalog) -> str:
    from core.catalog.loader import dependencias_de_etapas, ordem_de_execucao

    deps = dependencias_de_etapas(cat)
    L = [AVISO, "# Etapas do pipeline (ordem calculada)", "",
         "Ordem topológica a partir das `entradas` das fontes/produtos e de `depois_de`; desempate pelo campo `ordem` de cada etapa. "
         "Etapas `host` rodam no shell (`scripts/host-steps.sh`) enquanto o `arandu` roda no container worker.", "",
         "| # | Etapa | Executa | Política | Tentativas | Produz | Depende de |", "|---|---|---|---|---|---|---|"]
    for i, k in enumerate(ordem_de_execucao(cat), 1):
        s = cat.steps[k]
        exec_ = f"`python -m {s.modulo} {' '.join(s.args)}`" if s.runner == "worker" else f"`{' '.join(s.comando)}` (host)"
        prod = ", ".join([*(f"fonte {x}" for x in s.fontes), *(f"produto {x}" for x in s.produtos),
                          *(f"parcial {x}" for x in s.parcial), *(f"refresca {x}" for x in s.refresca)]) or "—"
        L.append(f"| {i} | `{s.id}` | {_cel(exec_)} | {s.politica_falha} | {s.tentativas} | {_cel(prod)} | {_cel(', '.join(sorted(deps[k])))} |")
    return "\n".join(L) + "\n"


def fontes_json(cat: Catalog) -> str:
    def src(s: Source) -> dict:
        d = s.model_dump(exclude_none=True)
        d["nao_verificado"] = nao_verificados(s)
        d["uso_comercial_efetivo"] = uso_comercial_efetivo(cat, s.id)
        return d
    obj = {
        "versao_esquema": 1,
        "fontes": [src(s) for s in sorted(cat.sources.values(), key=lambda x: x.id)],
        "produtos": [p.model_dump(exclude_none=True) for p in sorted(cat.products.values(), key=lambda x: x.id)],
        "etapas": [s.model_dump(exclude_none=True) for s in sorted(cat.steps.values(), key=lambda x: x.ordem)],
    }
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def catalogo_publico(cat: Catalog) -> str:
    """Subconjunto do catálogo servido pelo frontend (`/fontes`): o que o leitor precisa, sem caminhos internos de arquivo."""
    def campo(c) -> dict:
        return {"nome": c.nome, "tipo": c.tipo, "significado": c.significado, **({"tratamento": c.tratamento} if c.tratamento else {})}

    def src(s: Source) -> dict:
        o = s.origem
        return {
            "id": s.id, "nome": s.nome, "tipo": s.tipo, "ativa": s.ativa, "modulo": s.modulo, "descricao": s.descricao,
            "exposicao": s.exposicao, **({"decisao_exposicao": s.decisao_exposicao} if s.decisao_exposicao else {}), **({"atribuicao": s.atribuicao} if s.atribuicao else {}),
            "origem": ({k: v for k, v in o.model_dump(exclude_none=True).items() if k in ("url", "formato", "licenca", "termos", "uso_comercial", "nota")} if o else {}),
            "cadencia": s.cadencia.model_dump(exclude_none=True) if s.cadencia else {},
            "politica_falha": s.politica_falha, "nao_verificado": nao_verificados(s),
            "uso_comercial_efetivo": uso_comercial_efetivo(cat, s.id), "entradas": list(s.entradas), "campos": [campo(c) for c in s.campos if not c.sensivel],
        }

    def prod(p) -> dict:
        return {"id": p.id, "nome": p.nome, "descricao": p.descricao, "modulo": p.modulo, "limites": p.limites,
                "pendencias": list(p.pendencias or []), "campos": [campo(c) for c in p.campos if not c.sensivel]}

    obj = {"versao_esquema": 1, "fontes": [src(s) for s in sorted(cat.sources.values(), key=lambda x: x.id)],
           "produtos": [prod(p) for p in sorted(cat.products.values(), key=lambda x: x.id)]}
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"


def render(cat: Catalog) -> dict[str, str]:
    out: dict[str, str] = {}
    for s in cat.sources.values():
        out[f"docs/fontes/{s.id}.md"] = doc_fonte(s, cat)
    for p in cat.products.values():
        out[f"docs/produtos/{p.id}.md"] = doc_produto(p, cat)
    out["docs/dicionario.md"] = doc_dicionario(cat)
    out["docs/licencas.md"] = doc_licencas(cat)
    if cat.steps:
        out["docs/etapas.md"] = doc_etapas(cat)
    out["docs/fontes.json"] = fontes_json(cat)
    out["frontend/public/catalogo.json"] = catalogo_publico(cat)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--root", type=Path, default=ROOT, help="raiz do repositório (padrão: este)")
    a = ap.parse_args(argv)
    cat = load_catalog(a.root / "catalog")
    erros = validate(cat)
    if erros:
        for e in erros:
            print(f"ERRO: {e}", file=sys.stderr)
        return 1
    files = render(cat)
    if a.check:
        ruins = []
        for rel, txt in files.items():
            p = a.root / rel
            if not p.exists() or p.read_text(encoding="utf-8") != txt:
                ruins.append(rel)
        for d in ("docs/fontes", "docs/produtos"):
            pasta = a.root / d
            if pasta.is_dir():
                ruins += [f"{d}/{p.name} (órfão)" for p in pasta.glob("*.md") if f"{d}/{p.name}" not in files]
        for r in ruins:
            print(f"DESATUALIZADO: {r}", file=sys.stderr)
        return 1 if ruins else 0
    for rel, txt in files.items():
        p = a.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8")
    print(f"gerados {len(files)} arquivos em docs/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
