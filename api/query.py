# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Camada de consulta genérica — filtro/seleção/ordenação/agregação sobre as tabelas
em memória do snapshot (índices compactos). Sem banco de dados: opera sobre listas
de dicts já carregadas pela Store, memoizadas por snapshot.

Usado tanto pela API REST (api/routes/query.py) quanto pelo servidor MCP, via
Store.query() / Store.query_schema().

O catálogo (collections, campos, guia de operadores e receitas) está em `api/query_catalogo.py`; aqui ficam a validação e a avaliação.
"""

from __future__ import annotations

from typing import Any, Optional

from api.geo import haversine_km
from api.query_catalogo import (  # noqa: F401  (reexportados: `api.query.REGION_BY_UF`, `.COLLECTIONS`, `.SCHEMA`… seguem valendo)
    CAMPOS_ALIAS, COLECOES_ALIAS, COLLECTIONS, aviso_colecao_obsoleta, OPS_GUIDE, RECIPES, REGION_BY_UF, SCHEMA, _AGG_FNS, _OPS,
)


MAX_FILTER_DEPTH = 6  # profundidade máxima de aninhamento and/or/not (anti-abuso)
# Tetos de largura: sem eles, um `or` de 1.000 predicados leva 75,8 s de CPU com o GIL preso (todas as rotas paradas);
# limitar só a profundidade não basta. Os valores cobrem com folga as receitas do `describe_schema` e o uso do site.
MAX_PREDICADOS = 50          # predicados folha no filtro inteiro
MAX_VALORES_LISTA = 200      # itens de `in`/`nin`/`contains` em lista
MAX_CENTROS = 20             # centros de `within_radius`
MAX_SELECT = 60
MAX_SORT = 5
MAX_GROUP_BY = 4
MAX_AGREGACOES = 10
MAX_GRUPOS = 5000            # grupos no resultado de uma agregação
MAX_PAGINA = 100_000


def limitar(body: dict) -> None:
    """Recusa (QueryError, 400) consulta mais larga que os tetos acima ou com `limit`/`page` que não sejam inteiros (em vez de 500)."""
    if not isinstance(body, dict):
        raise QueryError("corpo da consulta deve ser um objeto JSON")
    preds = list(_iter_predicates(body.get("filter")))
    if len(preds) > MAX_PREDICADOS:
        raise QueryError(f"filtro com {len(preds)} predicados (máx {MAX_PREDICADOS}): use `in` com uma lista em vez de muitos `eq` em `or`.")
    for pr in preds:
        if not isinstance(pr, dict):
            raise QueryError(f"predicado inválido: {pr!r}")
        v = pr.get("value")
        if isinstance(v, (list, tuple)) and len(v) > MAX_VALORES_LISTA:
            raise QueryError(f"lista de valores com {len(v)} itens no campo {pr.get('field')!r} (máx {MAX_VALORES_LISTA}).")
        c = pr.get("centers")
        if isinstance(c, (list, tuple)) and len(c) > MAX_CENTROS:
            raise QueryError(f"within_radius com {len(c)} centros (máx {MAX_CENTROS}).")
    for chave, teto in (("select", MAX_SELECT), ("sort", MAX_SORT), ("group_by", MAX_GROUP_BY), ("aggregate", MAX_AGREGACOES)):
        val = body.get(chave)
        if val is not None and not isinstance(val, list):
            raise QueryError(f"{chave} deve ser uma lista")
        if val and len(val) > teto:
            raise QueryError(f"{chave} com {len(val)} itens (máx {teto}).")
    for chave, padrao, teto in (("limit", 100, 1000), ("page", 1, MAX_PAGINA)):
        val = body.get(chave, padrao)
        if isinstance(val, bool) or not isinstance(val, int):
            raise QueryError(f"{chave} deve ser um número inteiro (recebido {val!r}).")
        if val < 1 or val > teto:
            raise QueryError(f"{chave} fora do intervalo 1–{teto}.")


def _filter_depth(flt: Any, _depth: int = 1) -> int:
    """Profundidade de aninhamento de grupos and/or/not em um filtro."""
    if not isinstance(flt, dict):
        return _depth
    best = _depth
    for conn in ("and", "or"):
        if conn in flt and isinstance(flt[conn], list):
            for sub in flt[conn]:
                best = max(best, _filter_depth(sub, _depth + 1))
    if "not" in flt:
        best = max(best, _filter_depth(flt["not"], _depth + 1))
    return best


def _iter_predicates(flt: Any):
    """Percorre recursivamente os predicados folha de um filtro (and/or/not)."""
    if not isinstance(flt, dict):
        return
    for conn in ("and", "or"):
        if conn in flt:
            for sub in flt[conn]:
                yield from _iter_predicates(sub)
            return
    if "not" in flt:
        yield from _iter_predicates(flt["not"])
        return
    yield flt


def _field_refs(body: dict):
    """Todos os nomes de campo referenciados no corpo da consulta (para validação)."""
    refs: list[str] = []
    for pred in _iter_predicates(body.get("filter")):
        if pred.get("op") != "within_radius" and isinstance(pred.get("field"), str):
            refs.append(pred["field"])
    for s in body.get("sort") or []:
        if isinstance(s, dict) and isinstance(s.get("field"), str):
            refs.append(s["field"])
    for g in body.get("group_by") or []:
        if isinstance(g, str):
            refs.append(g)
    for f in body.get("select") or []:
        if isinstance(f, str):
            refs.append(f)
    for a in body.get("aggregate") or []:
        if isinstance(a, dict) and isinstance(a.get("field"), str):
            refs.append(a["field"])
    return refs


def avisos_campos_obsoletos(collection: str, body: Any) -> Optional[str]:
    """Aviso de depreciação quando a consulta cita o nome antigo de um campo (`CAMPOS_ALIAS`); `None` se não cita nenhum."""
    antigos = CAMPOS_ALIAS.get(collection)
    if not antigos or not isinstance(body, dict):
        return None
    try:
        citados = sorted({r for r in _field_refs(body) if r in antigos})
    except (AttributeError, TypeError):
        return None
    if not citados:
        return None
    return " ".join(f"O campo `{c}` foi renomeado para `{antigos[c][0]}` e o nome antigo será removido depois de duas versões: ele é {antigos[c][1]}. Use `{antigos[c][0]}`." for c in citados)


def validate(collection: str, body: dict, sample_row: Optional[dict] = None) -> None:
    """Valida nomes de campo e valores de enum contra o schema da collection.

    Levanta QueryError com a lista de opções válidas — para que um campo digitado
    errado ou um valor fora do domínio não retorne silenciosamente vazio (a armadilha
    que mais confunde LLMs)."""
    spec = SCHEMA.get(collection)
    if spec is None:
        raise QueryError(f"collection inválida: '{collection}'. Use: {', '.join(COLLECTIONS)}")

    limitar(body)
    flt = body.get("filter")
    if flt is not None and _filter_depth(flt) > MAX_FILTER_DEPTH:
        raise QueryError(
            f"filtro aninhado demais (máx {MAX_FILTER_DEPTH} níveis de and/or/not)."
        )

    for item in body.get("sort") or []:
        # chave desconhecida era ignorada em silêncio: {"field": "x", "desc": true} ordenava em ordem crescente
        if not isinstance(item, dict) or "field" not in item or set(item) - {"field", "dir"} or item.get("dir", "asc") not in ("asc", "desc"):
            raise QueryError(f"sort inválido: {item!r}. Use uma lista de {{\"field\": <campo>, \"dir\": \"asc\"|\"desc\"}}, "
                             'ex.: [{"field": "apnic_users", "dir": "desc"}].')

    field_specs = {f["name"]: f for f in spec["fields"]}
    known = set(field_specs)
    # Prefixos top-level permitidos (ex.: 'v4' de 'v4.unique_prefixes') + chaves reais
    # da linha (campos presentes mas não catalogados não devem dar falso positivo).
    prefixes = {name.split(".")[0] for name in known}
    row_keys = set(sample_row or {})
    allowed_top = prefixes | row_keys

    agregando = bool(body.get("group_by") or body.get("aggregate"))
    refs = _field_refs({**body, "sort": []} if agregando else body)    # na agregação o sort nomeia grupos e agregados (conferido em `execute`)
    for ref in refs:
        if ref in known or ref in row_keys:
            continue
        if "." in ref and ref.split(".")[0] in allowed_top:
            continue
        raise QueryError(
            f"campo '{ref}' não existe em '{collection}'. "
            f"Campos válidos: {', '.join(sorted(known))}"
        )

    # Valores fora de um domínio fechado, em comparações de pertinência positiva.
    for pred in _iter_predicates(body.get("filter")):
        fld = pred.get("field")
        spec_f = field_specs.get(fld) if isinstance(fld, str) else None
        enum = spec_f.get("enum") if spec_f else None
        if not enum:
            continue
        op = pred.get("op")
        bad: list = []
        if op == "eq" and pred.get("value") not in enum:
            bad = [pred.get("value")]
        elif op == "in" and isinstance(pred.get("value"), (list, tuple)):
            bad = [v for v in pred["value"] if v not in enum]
        if bad:
            raise QueryError(
                f"valor {bad[0]!r} inválido para '{fld}'. Valores aceitos: {enum}"
            )


def validar_valores_de_lista(rows: list[dict], body: dict) -> None:
    """Valor de pertinência num campo-lista de texto (ex.: `ixps_direct contains "sal"`) que não aparece em nenhuma linha: erro com os valores
    existentes. Sem isso, `ncontains` com código inexistente seria sempre verdadeiro e o resultado pareceria válido."""
    preds = [p for p in _iter_predicates(body.get("filter")) if p.get("op") in ("contains", "ncontains", "in", "nin")
             and isinstance(p.get("field"), str)]
    if not preds or not rows:
        return
    for p in preds:
        campo = p["field"]
        amostra = next((_get(r, campo) for r in rows[:50] if isinstance(_get(r, campo), list) and _get(r, campo)), None)
        if not amostra or not all(isinstance(x, str) for x in amostra):
            continue
        universo = _universo(rows, campo)
        if len(universo) > 500:
            continue
        valores = p["value"] if isinstance(p.get("value"), list) else [p.get("value")]
        ruins = [v for v in valores if isinstance(v, str) and v not in universo]
        if ruins:
            raise QueryError(f"valor {ruins[0]!r} não aparece em nenhuma linha de '{campo}'. Valores existentes: {', '.join(sorted(universo))}")


_UNIVERSOS: dict = {}


def _universo(rows: list[dict], campo: str) -> set:
    chave = (id(rows), len(rows), campo)
    if chave not in _UNIVERSOS:
        if len(_UNIVERSOS) > 64:
            _UNIVERSOS.clear()
        _UNIVERSOS[chave] = {x for r in rows for x in (_get(r, campo) if isinstance(_get(r, campo), list) else []) if isinstance(x, str)}
    return _UNIVERSOS[chave]


def schema(collection: Optional[str] = None) -> dict:
    """Catálogo de schema — todas as collections, ou apenas uma.

    Inclui guia de operadores e receitas (pergunta→ferramentas) para que a LLM
    monte filtros válidos e encadeie as ferramentas sem adivinhar.
    """
    base = {
        "operators": sorted(_OPS),
        "operator_guide": OPS_GUIDE,
        "aggregate_functions": sorted(_AGG_FNS),
        "recipes": RECIPES,
    }
    if collection in COLECOES_ALIAS:                            # nome antigo (D12): descreve a collection nova e avisa
        return {**schema(COLECOES_ALIAS[collection]), "aviso_obsoleta": aviso_colecao_obsoleta(collection)}
    if collection is not None:
        if collection not in SCHEMA:
            raise QueryError(f"collection inválida: '{collection}'. Use: {', '.join(COLLECTIONS)}")
        return {**base, "collection": collection, **SCHEMA[collection]}
    return {**base, "collections": SCHEMA}


# ---------------------------------------------------------------------------
# Avaliação
# ---------------------------------------------------------------------------

class QueryError(ValueError):
    """Erro de validação/execução de consulta (vira 400 na API)."""


_MISSING = object()


def _get(row: dict, path: str) -> Any:
    """Acessa um campo, com suporte a dot-path (ex.: 'v4.br_prefix_coverage_pct')."""
    cur: Any = row
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part, _MISSING)
        else:
            return _MISSING
        if cur is _MISSING:
            return _MISSING
    return cur


def _cmp_ok(a: Any, b: Any, op: str) -> bool:
    """Comparações numéricas/ordinais; None nunca satisfaz gt/gte/lt/lte."""
    if a is _MISSING or a is None or b is None:
        return False
    try:
        if op == "gt":
            return a > b
        if op == "gte":
            return a >= b
        if op == "lt":
            return a < b
        if op == "lte":
            return a <= b
    except TypeError:
        return False
    return False


def _eval_within_radius(row: dict, pred: dict) -> bool:
    """Geo: True se o ponto da linha está dentro de radius_km de ALGUM centro."""
    lat_f = pred.get("lat", "lat")
    lon_f = pred.get("lon", "lon")
    lat, lon = _get(row, lat_f), _get(row, lon_f)
    if lat is _MISSING or lon is _MISSING or lat is None or lon is None:
        return False
    radius = pred.get("radius_km")
    centers = pred.get("centers") or []
    if radius is None or not centers:
        raise QueryError("within_radius exige 'radius_km' e 'centers' (lista de [lat,lon])")
    for c in centers:
        try:
            if haversine_km(lat, lon, c[0], c[1]) <= radius:
                return True
        except (TypeError, IndexError):
            continue
    return False


def _eval_predicate(row: dict, pred: dict) -> bool:
    op = pred.get("op")
    if op == "within_radius":
        return _eval_within_radius(row, pred)
    field = pred.get("field")
    if not isinstance(field, str) or op not in _OPS:
        raise QueryError(f"predicado inválido: {pred!r} (op deve ser um de {sorted(_OPS)})")
    val = _get(row, field)
    target = pred.get("value")

    if op == "exists":
        present = val is not _MISSING and val is not None
        return present if bool(target) else not present
    if op == "eq":
        return (None if val is _MISSING else val) == target
    if op == "ne":
        return (None if val is _MISSING else val) != target
    if op in ("gt", "gte", "lt", "lte"):
        return _cmp_ok(val, target, op)
    if op in ("in", "nin"):
        if not isinstance(target, (list, tuple, set)):
            raise QueryError(f"op '{op}' exige value como lista (campo {field})")
        hit = (val is not _MISSING) and (val in target)
        return hit if op == "in" else not hit
    if op in ("contains", "ncontains"):
        hit = _contains(val, target)
        return hit if op == "contains" else not hit
    return False


def _contains(val: Any, target: Any) -> bool:
    if val is _MISSING or val is None:
        return False
    if isinstance(val, (list, tuple, set)):
        return target in val
    if isinstance(val, str):
        return str(target).lower() in val.lower()
    return False


def _eval_filter(row: dict, flt: Any) -> bool:
    if flt is None:
        return True
    if not isinstance(flt, dict):
        raise QueryError(f"filtro inválido: {flt!r}")
    if "and" in flt:
        return all(_eval_filter(row, f) for f in flt["and"])
    if "or" in flt:
        return any(_eval_filter(row, f) for f in flt["or"])
    if "not" in flt:
        return not _eval_filter(row, flt["not"])
    return _eval_predicate(row, flt)


def _sort_key(field: str, desc: bool):
    def key(row: dict):
        v = _get(row, field)
        missing = v is _MISSING or v is None
        if isinstance(v, bool):
            v = int(v)
        # None/missing sempre por último; tupla (flag, valor) com inversão p/ desc
        if missing:
            return (1, 0)
        return (0, -v if (desc and isinstance(v, (int, float))) else v)
    return key


def _ordenar(rows: list, field: str, desc: bool, valor=None) -> list:
    """Ordena por um campo, ausentes sempre por último. `reverse` (estável) em vez de negar o valor: a negação só valia para números e
    `dir: desc` num campo de texto saía em ordem crescente."""
    valor = valor or _get
    pres, aus = [], []
    for r in rows:
        v = valor(r, field)
        (aus if v is _MISSING or v is None else pres).append(r)

    def chave(r):
        v = valor(r, field)
        return int(v) if isinstance(v, bool) else v
    try:
        pres.sort(key=chave, reverse=desc)
    except TypeError:                                   # tipos misturados na coluna: compara como texto
        pres.sort(key=lambda r: str(chave(r)), reverse=desc)
    return pres + aus


def _project(row: dict, select: Optional[list[str]]) -> dict:
    if not select:
        return row
    return {f: (None if (_get(row, f) is _MISSING) else _get(row, f)) for f in select}


def _alias_agg(agg: dict) -> str:
    """Nome do agregado na resposta: `as`, ou `count` / `<fn>_<campo>`."""
    fn = agg.get("fn")
    return agg.get("as") or (fn if fn == "count" else f"{fn}_{agg.get('field')}")


def _aliases(body: dict) -> list[str]:
    """Aliases dos agregados do corpo (os de `count` sem `aggregate` incluídos), para validar `sort` no modo agregação."""
    aggs = body.get("aggregate") or [{"fn": "count"}]
    return [_alias_agg(a) for a in aggs if isinstance(a, dict)]


def _aggregate(rows: list[dict], group_by: list[str], aggs: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    order: list[tuple] = []
    for r in rows:
        key = tuple((None if _get(r, g) is _MISSING else _get(r, g)) for g in group_by)
        if key not in groups:
            if len(order) >= MAX_GRUPOS:
                raise QueryError(f"agregação com mais de {MAX_GRUPOS} grupos: filtre mais ou agrupe por um campo com menos valores.")
            groups[key] = []
            order.append(key)
        groups[key].append(r)

    out: list[dict] = []
    for key in order:
        bucket = groups[key]
        entry: dict = {"key": {g: key[i] for i, g in enumerate(group_by)}}
        for agg in aggs:
            fn = agg.get("fn")
            if fn not in _AGG_FNS:
                raise QueryError(f"função de agregação inválida: {fn!r}")
            alias = _alias_agg(agg)
            field = agg.get("field")
            if fn == "count":
                # sem campo: linhas do grupo; com campo: só as que têm valor (não nulo) naquele campo
                entry[alias] = len(bucket) if not field else sum(1 for r in bucket if _get(r, field) not in (_MISSING, None))
                continue
            if not field:
                raise QueryError(f"agregação '{fn}' exige 'field'")
            vals = [v for v in (_get(r, field) for r in bucket) if v is not _MISSING and v is not None]
            if fn == "distinct":
                entry[alias] = len(set(vals))
            elif not vals:
                entry[alias] = None
            elif fn == "sum":
                entry[alias] = sum(vals)
            elif fn == "avg":
                entry[alias] = sum(vals) / len(vals)
            elif fn == "min":
                entry[alias] = min(vals)
            elif fn == "max":
                entry[alias] = max(vals)
        out.append(entry)
    return out


def _ordenar_grupos(grupos: list[dict], sort: list, group_by: list[str], aliases: list[str]) -> None:
    """Ordena os grupos no lugar. Cada chave de `sort` é um alias de agregado (`sum_acessos`, `count`) ou um campo de `group_by`; o alias
    vence se os nomes coincidem. Ausentes (None) sempre por último; empates mantêm a ordem de aparição."""
    for s in reversed(sort):
        if not isinstance(s, dict) or "field" not in s:
            raise QueryError(f"sort inválido: {s!r}")
        campo = s["field"]
        if campo not in aliases and campo not in group_by:
            raise QueryError(f"sort '{campo}' não vale na agregação: ordene por um agregado ({', '.join(aliases)}) ou por um campo de group_by "
                             f"({', '.join(group_by) or 'nenhum'}).")
        achatados = [{campo: (g[campo] if campo in aliases else g["key"][campo])} for g in grupos]
        ordem = _ordenar(list(range(len(grupos))), campo, s.get("dir") == "desc", lambda i, f: achatados[i][f])
        grupos[:] = [grupos[i] for i in ordem]


def execute(rows: list[dict], body: dict) -> dict:
    """Executa uma consulta sobre `rows` (a tabela já montada da collection)."""
    if not isinstance(body, dict):
        raise QueryError("corpo da consulta deve ser um objeto JSON")

    flt = body.get("filter")
    filtered = [r for r in rows if _eval_filter(r, flt)] if flt is not None else list(rows)

    group_by = body.get("group_by")
    aggs = body.get("aggregate")
    if group_by or aggs:
        group_by = group_by or []
        if not isinstance(group_by, list) or not all(isinstance(g, str) for g in group_by):
            raise QueryError("group_by deve ser uma lista de nomes de campo")
        if not aggs:
            aggs = [{"fn": "count"}]
        if not isinstance(aggs, list):
            raise QueryError("aggregate deve ser uma lista")
        grupos = _aggregate(filtered, group_by, aggs)
        _ordenar_grupos(grupos, body.get("sort") or [], group_by, [_alias_agg(a) for a in aggs])
        resp = {"mode": "aggregate", "matched": len(filtered), "total_grupos": len(grupos)}
        if "limit" in body or "page" in body:       # sem `limit`/`page` valem todos os grupos, como antes (os cartões da home dependem disso)
            limit = max(1, min(int(body.get("limit", 100)), 1000))
            page = max(1, int(body.get("page", 1)))
            resp.update(page=page, limit=limit, pages=(len(grupos) + limit - 1) // limit if grupos else 0)
            grupos = grupos[(page - 1) * limit:page * limit]
        return {**resp, "groups": grupos}

    # Modo lista
    sort = body.get("sort") or []
    for s in reversed(sort):  # estável: aplica chaves em ordem reversa
        if not isinstance(s, dict) or "field" not in s:
            raise QueryError(f"sort inválido: {s!r}")
        filtered = _ordenar(filtered, s["field"], s.get("dir") == "desc")

    total = len(filtered)
    limit = max(1, min(int(body.get("limit", 100)), 1000))
    page = max(1, int(body.get("page", 1)))
    start = (page - 1) * limit
    select = body.get("select")
    items = [_project(r, select) for r in filtered[start:start + limit]]
    return {
        "mode": "list",
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 0,
        "items": items,
    }
