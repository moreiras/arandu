# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Carrega e valida o catálogo (catalog/sources/*.yaml e catalog/products/*.yaml)."""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from core.catalog.schema import NAO_VERIFICADO, Product, Source, Step

# Ids de etapa renomeados → id atual. Aceitos em `--only`, `arandu collect/build` e nos relatórios de retomada.
ALIASES_ETAPA = {
    "p1_bgp_parser": "bgp_ixp",
    "p2p3_metrics": "metricas_ixp_asn",
    "p6_snapshot": "snapshot_completo",
    "p6b_saude_asn": "saude_asn",
}


def id_de_etapa(nome: str) -> str:
    """Id atual de uma etapa, resolvendo os aliases de ids renomeados."""
    return ALIASES_ETAPA.get(nome, nome)

ROOT = Path(__file__).resolve().parents[2]
CATALOG_DIR = ROOT / "catalog"


@dataclass
class Catalog:
    sources: dict[str, Source] = field(default_factory=dict)
    products: dict[str, Product] = field(default_factory=dict)
    steps: dict[str, Step] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)   # erros de leitura/esquema


def _read(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_catalog(root: Path | None = None) -> Catalog:
    """Lê todos os YAML; erros de esquema vão para `errors` (não levantam)."""
    base = Path(root) if root else CATALOG_DIR
    cat = Catalog()
    for kind, model, dest in (("sources", Source, cat.sources), ("products", Product, cat.products), ("steps", Step, cat.steps)):
        for path in sorted((base / kind).glob("*.yaml")):
            rel = f"{kind}/{path.name}"
            try:
                obj = model.model_validate(_read(path))
            except (ValidationError, yaml.YAMLError, TypeError) as exc:
                cat.errors.append(f"{rel}: {str(exc).splitlines()[0] if isinstance(exc, yaml.YAMLError) else exc}")
                continue
            if obj.id != path.stem:
                cat.errors.append(f"{rel}: id '{obj.id}' difere do nome do arquivo")
            if obj.id in dest:
                cat.errors.append(f"{rel}: id duplicado '{obj.id}'")
            dest[obj.id] = obj
    _etapas_inline(cat)
    return cat


def _etapas_inline(cat: "Catalog") -> None:
    """Fontes com `etapa:` ganham uma etapa de mesmo id, que roda no início (ordem negativa, desempate por id)."""
    ordem = -100
    for sid in sorted(cat.sources):
        src = cat.sources[sid]
        if not src.etapa or sid in cat.steps:
            continue
        e = src.etapa
        ordem -= 1
        try:
            cat.steps[sid] = Step(
                id=sid, nome=src.nome, ordem=ordem, modulo=src.modulo, args=e.args, fontes=[sid],
                tentativas=e.tentativas, espera_s=e.espera_s, memoria_mb=e.memoria_mb, continua=e.continua, destinos=e.destinos,
                politica_falha=e.politica_falha or src.politica_falha, descricao=f"Etapa declarada em catalog/sources/{sid}.yaml.")
        except ValidationError as exc:
            cat.errors.append(f"sources/{sid}.yaml: etapa inline inválida: {exc}")


def _walk_strings(obj: Any):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _walk_strings(v)


def nao_verificados(item: Source | Product) -> int:
    """Quantos valores 'nao_verificado' o item declara (cada um é tarefa aberta)."""
    return sum(1 for s in _walk_strings(item.model_dump(exclude={"pendencias"})) if s == NAO_VERIFICADO)


def pattern_matches(pattern: str, path: str) -> bool:
    """Casa um caminho com padrão do catálogo: '{asn}' etc. viram '*'; '*' não cruza '/'."""
    rx = re.escape(re.sub(r"\{[^}]+\}", "\x00", pattern)).replace("\x00", "[^/]+")
    rx = rx.replace(r"\*", "[^/]*")
    return re.fullmatch(rx, path) is not None


def validate(cat: Catalog) -> list[str]:
    """Regras entre arquivos. Devolve a lista de erros (vazia = catálogo consistente)."""
    erros = list(cat.errors)
    for s in cat.sources.values():
        for e in s.entradas:
            if e not in cat.sources:
                erros.append(f"fonte {s.id}: entrada '{e}' não existe")
        if s.id in s.entradas:
            erros.append(f"fonte {s.id}: depende de si mesma")
        if s.origem is None and s.tipo == "bruta":
            erros.append(f"fonte {s.id}: sem origem")
        if s.origem and s.origem.uso_comercial == NAO_VERIFICADO and not s.pendencias:
            erros.append(f"fonte {s.id}: uso_comercial nao_verificado sem 'pendencias' explicando")
        if nao_verificados(s) and not s.pendencias:
            erros.append(f"fonte {s.id}: tem nao_verificado mas 'pendencias' está vazio")
    for p in cat.products.values():
        for e in p.entradas:
            if e.source and e.source not in cat.sources:
                erros.append(f"produto {p.id}: fonte '{e.source}' não existe")
            if e.product and e.product not in cat.products:
                erros.append(f"produto {p.id}: produto '{e.product}' não existe")
            if e.product == p.id:
                erros.append(f"produto {p.id}: depende de si mesmo")
        if nao_verificados(p) and not p.pendencias:
            erros.append(f"produto {p.id}: tem nao_verificado mas 'pendencias' está vazio")
    erros.extend(_referencias_publicado(cat))
    erros.extend(validar_etapas(cat))
    erros.extend(_ciclos(cat))
    erros.extend(_vazamento(cat))
    return erros


_GRAU = {"permitido": 0, "nao_verificado": 1, "restrito": 2}


def uso_comercial_efetivo(cat: Catalog, source_id: str, _vistos: frozenset[str] = frozenset()) -> str:
    """Pior `uso_comercial` entre a fonte e tudo de que ela depende (restrito > nao_verificado > permitido).

    Fonte derivada sem origem própria herda das entradas; sem nenhuma origem na cadeia, 'nao_verificado'.
    """
    s = cat.sources.get(source_id)
    if s is None or source_id in _vistos:
        return "nao_verificado"
    graus = []
    if s.origem is not None:
        graus.append(s.origem.uso_comercial)
    graus += [uso_comercial_efetivo(cat, e, _vistos | {source_id}) for e in s.entradas]
    if not graus:
        return "nao_verificado"
    return max(graus, key=lambda g: _GRAU[g])


def parse_publicado_em(ref: str) -> tuple[str, str, str | None] | None:
    """'asn_docs → asns/{asn}.json#pdb' → ('asn_docs', 'asns/{asn}.json', 'pdb'); rotas de API (/…) → None."""
    if "→" not in ref:
        return None
    dono, _, resto = (x.strip() for x in ref.partition("→"))
    if resto.startswith("/"):
        return None
    caminho, _, campo = resto.partition("#")
    return dono, caminho.strip(), (campo.strip() or None)


def publicados_declarados(cat: Catalog, dono: str) -> list[str]:
    if dono in cat.products:
        return cat.products[dono].saidas.publicado
    if dono in cat.sources:
        return cat.sources[dono].saidas.publicado
    return []


def _referencias_publicado(cat: Catalog) -> list[str]:
    """Todo `publicado_em` aponta para fonte/produto existente que declara aquele arquivo."""
    out: list[str] = []
    for kind, itens in (("fonte", cat.sources), ("produto", cat.products)):
        for it in itens.values():
            for c in it.campos:
                for ref in c.publicado_em:
                    r = parse_publicado_em(ref)
                    if r is None:
                        if "→" in ref and not ref.split("→", 1)[1].strip().startswith("/"):
                            out.append(f"{kind} {it.id}, campo '{c.nome}': referência malformada '{ref}'")
                        elif "→" not in ref:
                            out.append(f"{kind} {it.id}, campo '{c.nome}': publicado_em sem '→': '{ref}'")
                        continue
                    dono, caminho, _ = r
                    if dono not in cat.products and dono not in cat.sources:
                        out.append(f"{kind} {it.id}, campo '{c.nome}': '{dono}' não existe")
                    elif not any(pattern_matches(pat, caminho) or pat == caminho for pat in publicados_declarados(cat, dono)):
                        out.append(f"{kind} {it.id}, campo '{c.nome}': '{dono}' não declara o arquivo '{caminho}'")
    return out


def _ciclos(cat: Catalog) -> list[str]:
    grafo = {f"s:{s.id}": [f"s:{e}" for e in s.entradas] for s in cat.sources.values()}
    for p in cat.products.values():
        grafo[f"p:{p.id}"] = [f"s:{e.source}" if e.source else f"p:{e.product}" for e in p.entradas]
    estado: dict[str, int] = {}
    out: list[str] = []

    def visita(n: str, pilha: list[str]) -> None:
        if estado.get(n) == 2 or n not in grafo:
            return
        if estado.get(n) == 1:
            out.append("ciclo no catálogo: " + " → ".join(pilha[pilha.index(n):] + [n]))
            return
        estado[n] = 1
        for m in grafo[n]:
            visita(m, pilha + [n])
        estado[n] = 2

    for n in grafo:
        visita(n, [])
    return out


def _vazamento(cat: Catalog) -> list[str]:
    """Licença: fonte publicavel=false não pode ter saída publicada nem alimentar produto sem declarar.

    Um produto que consome uma fonte não publicável só é aceito se nenhum campo seu for
    marcado como vindo dela: a declaração é `campos[].publicado_em` da fonte vazio e a fonte
    sem `saidas.publicado`. Aqui validamos o que é verificável estaticamente.
    """
    out: list[str] = []
    for s in cat.sources.values():
        if s.publicavel:
            continue
        if s.saidas.publicado or s.saidas.fragmentos:
            out.append(f"fonte {s.id}: publicavel=false mas declara saidas.publicado/fragmentos")
        for c in s.campos:
            if c.publicado_em:
                out.append(f"fonte {s.id}: publicavel=false mas campo '{c.nome}' declara publicado_em")
    return out


# ---------------------------------------------------------------------------
# Etapas do pipeline
# ---------------------------------------------------------------------------

def dependencias_de_etapas(cat: Catalog) -> dict[str, set[str]]:
    """{etapa: {etapas de que depende}}: `depois_de` + entradas das fontes/produtos que a etapa produz."""
    produtor: dict[str, str] = {}
    for s in cat.steps.values():
        for x in s.fontes:
            produtor[f"s:{x}"] = s.id
        for x in s.produtos:
            produtor[f"p:{x}"] = s.id
    deps: dict[str, set[str]] = {}
    for s in cat.steps.values():
        d = set(s.depois_de)
        for sid in s.fontes:
            fonte = cat.sources.get(sid)
            for e in (fonte.entradas if fonte else []):
                d.add(produtor.get(f"s:{e}", ""))
        for pid in s.produtos:
            prod = cat.products.get(pid)
            for e in (prod.entradas if prod else []):
                d.add(produtor.get(f"s:{e.source}" if e.source else f"p:{e.product}", ""))
        d.discard("")
        d.discard(s.id)
        deps[s.id] = d
    return deps


def ordem_de_execucao(cat: Catalog) -> list[str]:
    """Ordenação topológica (Kahn) com desempate estável pela ordem legada. Levanta ValueError se houver ciclo."""
    import heapq

    deps = dependencias_de_etapas(cat)
    pendente = {k: set(v) & set(cat.steps) for k, v in deps.items()}
    fila: list[tuple[int, str]] = []
    na_fila: set[str] = set()
    for k, v in pendente.items():
        if not v:
            heapq.heappush(fila, (cat.steps[k].ordem, k))
            na_fila.add(k)
    saida: list[str] = []
    while fila:
        _, k = heapq.heappop(fila)
        saida.append(k)
        for o, v in pendente.items():
            v.discard(k)
            if not v and o not in na_fila:
                heapq.heappush(fila, (cat.steps[o].ordem, o))
                na_fila.add(o)
    if len(saida) != len(cat.steps):
        raise ValueError("ciclo entre etapas: " + ", ".join(sorted(set(cat.steps) - set(saida))))
    return saida


def validar_etapas(cat: Catalog) -> list[str]:
    erros: list[str] = []
    if not cat.steps:
        return erros
    ordens: dict[int, str] = {}
    for s in cat.steps.values():
        if s.ordem in ordens:
            erros.append(f"etapa {s.id}: ordem {s.ordem} repetida em {ordens[s.ordem]}")
        ordens[s.ordem] = s.id
        for x in s.fontes:
            if x not in cat.sources:
                erros.append(f"etapa {s.id}: fonte '{x}' não existe")
        for x in (*s.produtos, *s.parcial, *s.refresca):
            if x not in cat.products:
                erros.append(f"etapa {s.id}: produto '{x}' não existe")
        for x in (*s.depois_de, *s.somente_se_executou):
            if x not in cat.steps:
                erros.append(f"etapa {s.id}: etapa '{x}' não existe")
        # a política da etapa tem de ser a da fonte que ela produz
        for x in s.fontes:
            f = cat.sources.get(x)
            if f and f.politica_falha != s.politica_falha:
                erros.append(f"etapa {s.id}: politica_falha '{s.politica_falha}' difere da fonte {x} ('{f.politica_falha}')")
    donos: dict[str, str] = {}
    for s in cat.steps.values():
        for x in s.fontes:
            if x in donos:
                erros.append(f"fonte {x} produzida por duas etapas: {donos[x]} e {s.id}")
            donos[x] = s.id
    # toda fonte com módulo executável tem etapa
    for f in cat.sources.values():
        if f.modulo and f.ativa and f.id not in donos:
            erros.append(f"fonte {f.id}: nenhuma etapa a produz")
    try:
        ordem_de_execucao(cat)
    except ValueError as e:
        return erros + [str(e)]
    return erros
