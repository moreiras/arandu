# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Entrada e saída das tools do MCP: tolerante na forma, cuidadoso no conteúdo, nunca silencioso.

Medido com modelos locais: modelos menores escolhem a tool certa e erram a forma dos argumentos ("null" em texto,
"False", números entre aspas, `{"type": "string", "value": "asns"}`, filtro como texto, datas de snapshot inventadas). Aqui, antes da
validação do FastMCP:

1. normalização de forma, guiada pelo schema da tool, sem ambiguidade;
2. valores com sentido único (nome de cidade → código de PTT, nome de UF → sigla, CNPJ/IBGE sem pontuação) com aviso;
3. recusa com instrução de conserto quando o valor não tem leitura única (CNPJ com dígito errado, IBGE fora do formato, snapshot que
   não existe, código de PTT desconhecido).

Todo ajuste volta na resposta em `ajustes` ([{campo, recebido, usado, motivo}]), para o modelo (e quem lê a resposta) saber o que foi
interpretado. Nada de memória entre chamadas. Na saída, o JSON vai compacto (o indentado gastava ~30% de tokens à toa).
"""
from __future__ import annotations

import difflib
import json
import re
import unicodedata
from functools import lru_cache
from typing import Any, Callable, Optional

import yaml

_NULOS = {"null", "none", "nil", "undefined", ""}
_VERDADE = {"true": True, "false": False, "sim": True, "nao": False, "yes": True, "no": False, "1": True, "0": False}

UFS = {
    "AC": "acre", "AL": "alagoas", "AP": "amapa", "AM": "amazonas", "BA": "bahia", "CE": "ceara", "DF": "distrito federal",
    "ES": "espirito santo", "GO": "goias", "MA": "maranhao", "MT": "mato grosso", "MS": "mato grosso do sul", "MG": "minas gerais",
    "PA": "para", "PB": "paraiba", "PR": "parana", "PE": "pernambuco", "PI": "piaui", "RJ": "rio de janeiro", "RN": "rio grande do norte",
    "RS": "rio grande do sul", "RO": "rondonia", "RR": "roraima", "SC": "santa catarina", "SP": "sao paulo", "SE": "sergipe", "TO": "tocantins",
}
_UF_POR_NOME = {v: k for k, v in UFS.items()}

# Parâmetros que recebem código de PTT do IX.br, por tool (os de PTT externo, como `ixp_externo(code=)`, só vão para minúsculas)
_PARAM_PTT = {
    "ixp_detalhe": "code", "ixp_participantes": "code", "ixp_potencial": "code", "ixp_proximos": "code", "ixp_usuarios": "code",
    "ixp_assinantes": "code", "ixp_rejeicoes": "code", "asn_politica": "ixp", "ixp_communities": "ixp", "geo_localizar": "ixp",
}
_PARAM_PTT_EXTERNO = {"ixp_externo": "code", "ixp_portas": "code"}
# campos do `query` cujos valores são códigos de PTT do IX.br
_CAMPOS_PTT = {"ixps_direct", "ixps_membro", "ixps_sessao_rs", "ixps_origin", "ixp", "code", "ptt_proximo"}


class EntradaInvalida(ValueError):
    """Valor sem leitura única: vira erro de tool com a instrução de conserto."""


def _sem_acento(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


@lru_cache(maxsize=1)
def ptts_config() -> dict[str, str]:
    """{código: cidade} do IX.br, de `config/ixps.yaml` (fonte da coleta): usado nas instruções e quando a Store não tem índice."""
    from core.common import load_ixps
    return {i["code"]: i["name"] for i in load_ixps()}


# fonte dos PTTs válidos na entrada: o servidor registra a do snapshot em uso (contexto.py); sem registro, a configuração
_FONTE_PTTS: Optional[Callable[[], Optional[dict[str, str]]]] = None


def registrar_fonte_ptts(fn: Callable[[], Optional[dict[str, str]]]) -> None:
    global _FONTE_PTTS
    _FONTE_PTTS = fn


def ptts() -> dict[str, str]:
    if _FONTE_PTTS is not None:
        tab = _FONTE_PTTS()
        if tab:
            return tab
    return ptts_config()


def codigo_ptt(valor: str) -> tuple[Optional[str], Optional[str]]:
    """(código, motivo do ajuste) para um código ou nome de cidade; (None, None) se não houver leitura única."""
    v = _sem_acento(str(valor))
    tab = ptts()
    if v in tab:
        return v, None
    por_cidade = {_sem_acento(c): k for k, c in tab.items()}
    if v in por_cidade:
        return por_cidade[v], "nome da cidade convertido no código do PTT"
    v2 = re.sub(r"^(ix\.?br|ptt|ixp)[\s\-_]*(de\s+|do\s+|da\s+)?", "", v).strip()
    if v2 in tab:
        return v2, "prefixo removido do código do PTT"
    if v2 in por_cidade:
        return por_cidade[v2], "nome da cidade convertido no código do PTT"
    return None, None


def erro_ptt(valor) -> str:
    tab = ptts()
    perto = difflib.get_close_matches(_sem_acento(str(valor)), list(tab) + [_sem_acento(c) for c in tab.values()], n=3, cutoff=0.6)
    dica = f" Parecidos: {', '.join(perto)}." if perto else ""
    lista = " ".join(f"{k}={c}" for k, c in tab.items())
    return f"Código de PTT desconhecido: {valor!r}.{dica} Códigos do IX.br (minúsculos): {lista}."


def sigla_uf(valor: str) -> tuple[Optional[str], Optional[str]]:
    v = str(valor).strip()
    if v.upper() in UFS:
        return v.upper(), (None if v.isupper() else "sigla da UF em maiúsculas")
    nome = _sem_acento(v)
    if nome in _UF_POR_NOME:
        return _UF_POR_NOME[nome], "nome da UF convertido na sigla"
    return None, None


def separa_uf(nome: str) -> tuple[str, Optional[str]]:
    """"Mossoró, RN" / "Mossoró - RN" / "Mossoró (RN)" / "Mossoró/RN" / "Boa Vista, Roraima" → (nome, UF). Sem UF reconhecível: (nome, None)."""
    m = re.fullmatch(r"\s*(.+?)\s*(?:[,/\-–]\s*|\(\s*)([A-Za-zÀ-ú ]{2,25}?)\s*\)?\s*", nome or "")
    if m:
        sig, _ = sigla_uf(m.group(2))
        if sig:
            return m.group(1).strip(), sig
    return (nome or "").strip(), None


def casa_municipio(nome: str, candidatos: list[dict], uf: Optional[str] = None) -> tuple[list[dict], list[str]]:
    """Municípios (dicts com `nome` e `uf`) que casam o nome sem acento e sem caixa: igualdade primeiro, depois trecho. Devolve
    (casados, sugestões para o erro)."""
    alvo, uf_nome = separa_uf(nome)
    uf = (uf or uf_nome or "").upper() or None
    a = _sem_acento(alvo)
    base = [c for c in candidatos if not uf or (c.get("uf") or "").upper() == uf]
    iguais = [c for c in base if _sem_acento(c.get("nome") or "") == a]
    if iguais:
        return iguais, []
    trecho = [c for c in base if a and a in _sem_acento(c.get("nome") or "")]
    if trecho:
        return trecho, []
    nomes = {f"{c.get('nome')} ({c.get('uf')})": _sem_acento(c.get("nome") or "") for c in base}
    perto = difflib.get_close_matches(a, list(set(nomes.values())), n=5, cutoff=0.75)
    return [], [k for k, v in nomes.items() if v in perto][:5]


def cnpj_digitos(valor) -> str:
    d = re.sub(r"\D", "", str(valor))
    if len(d) not in (8, 14):
        raise EntradaInvalida(f"CNPJ inválido: {valor!r} tem {len(d)} dígitos; use os 14 dígitos (ou a raiz de 8 nas tools que a aceitam).")
    if len(d) == 14 and not _dv_cnpj_ok(d):
        raise EntradaInvalida(f"CNPJ inválido: {valor!r} não confere no dígito verificador. Confira o número (ou busque pelo nome em outorga_lista(q=...)).")
    return d


def _dv_cnpj_ok(d: str) -> bool:
    if len(set(d)) == 1:
        return False
    def dv(base: str, pesos: list[int]) -> int:
        r = sum(int(a) * b for a, b in zip(base, pesos)) % 11
        return 0 if r < 2 else 11 - r
    p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    return dv(d[:12], p1) == int(d[12]) and dv(d[:13], [6] + p1) == int(d[13])


def ibge_digitos(valor) -> str:
    d = re.sub(r"\D", "", str(valor))
    if len(d) != 7:
        raise EntradaInvalida(f"Código IBGE inválido: {valor!r}. O código de município tem 7 dígitos (ex.: 3550308 = São Paulo); "
                              "para buscar pelo nome use municipio= (e uf=).")
    return d


# ── normalização genérica pelo schema ─────────────────────────────────────────────────────────────────────────────────────────────────
def _tipos(prop: dict) -> set[str]:
    if "type" in prop:
        t = prop["type"]
        return set(t) if isinstance(t, list) else {t}
    out: set[str] = set()
    for alt in prop.get("anyOf", []) + prop.get("oneOf", []):
        out |= _tipos(alt)
    return out or {"any"}


def _item_tipo(prop: dict) -> Optional[str]:
    for alt in [prop] + prop.get("anyOf", []):
        if alt.get("type") == "array":
            it = (alt.get("items") or {}).get("type")
            return it if isinstance(it, str) else None
    return None


def _desembrulha(v: Any) -> tuple[Any, bool]:
    """{"type": "...", "value": X} (o modelo copiou o formato do schema) → X; {"type": "null"} → None."""
    if isinstance(v, dict) and "type" in v and set(v) <= {"type", "value", "description", "title"}:
        return (v.get("value") if "value" in v else None), True
    return v, False


def _texto_estruturado(v: str) -> Any:
    """Texto que parece objeto ou lista → valor (JSON, ou YAML de fluxo, que aceita chaves sem aspas: `{and: [{field: "uf"}]}`)."""
    s = v.strip()
    for leitor in (json.loads, yaml.safe_load):
        try:
            return leitor(s)
        except Exception:
            continue
    raise ValueError


def _num(v: Any, tipo: str) -> Any:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip()
        s2 = re.sub(r"^as\s*", "", s, flags=re.I) if tipo == "integer" else s
        if re.fullmatch(r"-?\d+", s2):
            return int(s2)
        if tipo == "number" and re.fullmatch(r"-?\d+([.,]\d+)?", s2):
            return float(s2.replace(",", "."))
    if isinstance(v, float) and tipo == "integer" and v.is_integer():
        return int(v)
    return v


def _coagir(v: Any, prop: dict, opcional: bool) -> Any:
    tipos = _tipos(prop)
    # "null" em texto num parâmetro opcional é ausência (o llama3.3 preenche todos os opcionais assim); num obrigatório, deixa a validação falar
    if isinstance(v, str) and v.strip().lower() in _NULOS and (opcional or "string" not in tipos):
        return None
    if "integer" in tipos or "number" in tipos:
        v2 = _num(v, "integer" if "integer" in tipos else "number")
        if v2 is not v:
            return v2
    if "boolean" in tipos and isinstance(v, str) and _sem_acento(v) in _VERDADE:
        return _VERDADE[_sem_acento(v)]
    if "array" in tipos and not isinstance(v, list):
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("["):
                try:
                    v = _texto_estruturado(s)
                except ValueError:
                    pass
            if isinstance(v, str):
                v = [p.strip() for p in s.split(",") if p.strip()]
        elif v is not None and not isinstance(v, dict):
            v = [v]
    if "array" in tipos and isinstance(v, list):
        it = _item_tipo(prop)
        if it in ("integer", "number"):
            v = [_num(x, it) for x in v]
    if "object" in tipos and isinstance(v, str):
        try:
            v = _texto_estruturado(v)
        except ValueError:
            pass
    return v


def normalizar(tool: str, args: Optional[dict], schema: dict, snapshots: Callable[[], Optional[list[str]]]) -> tuple[dict, list[dict]]:
    """Devolve (argumentos normalizados, ajustes). Levanta EntradaInvalida quando o valor não tem leitura única."""
    props: dict = (schema or {}).get("properties", {}) or {}
    obrigatorios = set((schema or {}).get("required", []) or [])
    ajustes: list[dict] = []
    out: dict = {}

    def anota(campo, recebido, usado, motivo):
        ajustes.append({"campo": campo, "recebido": recebido, "usado": usado, "motivo": motivo})

    for k, v in (args or {}).items():
        if k not in props:
            perto = difflib.get_close_matches(k, list(props), n=1, cutoff=0.75)
            if perto and perto[0] not in (args or {}):
                anota(k, v, perto[0], f"argumento '{k}' não existe; lido como '{perto[0]}'")
                k = perto[0]
            else:
                anota(k, v, None, f"argumento '{k}' não existe nesta tool e foi ignorado (aceitos: {', '.join(props)})")
                continue
        original = v
        v, emb = _desembrulha(v)
        v = _coagir(v, props[k], k not in obrigatorios)
        if v is None:
            if isinstance(original, str) and original.strip():
                anota(k, original, None, "valor nulo escrito como texto: argumento tratado como ausente")
            continue
        if v != original:
            anota(k, original, v, "valor desembrulhado de {type, value}" if emb else "formato convertido para o tipo do parâmetro")
        out[k] = v

    # valores com regra própria
    if "date" in out:
        d = str(out["date"]).strip()
        disp = snapshots()
        if disp is not None and d not in disp:
            raise EntradaInvalida(f"Snapshot {d!r} não existe. Disponíveis: {', '.join(disp)} (mais recente: {disp[-1] if disp else '—'}). "
                                  "Omita `date` para usar o mais recente.")
    for k in ("cnpj",):
        if k in out:
            novo = cnpj_digitos(out[k])
            if novo != out[k]:
                anota(k, out[k], novo, "CNPJ só com dígitos")
            out[k] = novo
    if "ibge" in out:
        novo = ibge_digitos(out["ibge"])
        if novo != str(out["ibge"]):
            anota("ibge", out["ibge"], novo, "IBGE só com dígitos")
        out["ibge"] = novo
    if "uf" in out and isinstance(out["uf"], str):
        sig, motivo = sigla_uf(out["uf"])
        if sig is None:
            raise EntradaInvalida(f"UF desconhecida: {out['uf']!r}. Use a sigla de 2 letras: {', '.join(UFS)}.")
        if motivo:
            anota("uf", out["uf"], sig, motivo)
        out["uf"] = sig
    p = _PARAM_PTT.get(tool)
    if p and isinstance(out.get(p), str):
        cod, motivo = codigo_ptt(out[p])
        if cod is None:
            raise EntradaInvalida(erro_ptt(out[p]))
        if cod != out[p]:
            anota(p, out[p], cod, motivo or "código do PTT em minúsculas")
        out[p] = cod
    p = _PARAM_PTT_EXTERNO.get(tool)
    if p and isinstance(out.get(p), str) and out[p] != out[p].strip().lower():
        anota(p, out[p], out[p].strip().lower(), "código do PTT em minúsculas")
        out[p] = out[p].strip().lower()
    if tool == "query":
        _normalizar_query(out, anota)
    return out, ajustes


# ── query ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
_OPS = {"eq", "ne", "gt", "gte", "lt", "lte", "in", "nin", "contains", "ncontains", "exists", "within_radius"}
_OP_SINONIMOS = {"=": "eq", "==": "eq", "!=": "ne", ">": "gt", ">=": "gte", "<": "lt", "<=": "lte", "not_in": "nin",
                 "not_contains": "ncontains", "notcontains": "ncontains", "equals": "eq", "has": "contains", "includes": "contains"}


def _predicado(p: Any, anota) -> Any:
    """Formas abreviadas de predicado → {field, op, value}."""
    if not isinstance(p, dict):
        return p
    for lig in ("and", "or"):
        if lig in p and isinstance(p[lig], list):
            return {lig: [_predicado(x, anota) for x in p[lig]]}
    if "not" in p:
        return {"not": _predicado(p["not"], anota)}
    if "field" in p:
        op = p.get("op") or p.get("operator")
        op2 = _OP_SINONIMOS.get(str(op).lower(), str(op).lower()) if op is not None else op
        q = {k: v for k, v in p.items() if k != "operator"}
        if op2 != op or "operator" in p:
            q["op"] = op2
            anota("filter", p, q, "operador normalizado")
        return q
    # {"contains": ["ixps_direct", "mao"]}
    if len(p) == 1:
        (k, v), = p.items()
        kop = _OP_SINONIMOS.get(str(k).lower(), str(k).lower())
        if kop in _OPS and isinstance(v, list) and len(v) == 2 and isinstance(v[0], str):
            q = {"field": v[0], "op": kop, "value": v[1]}
            anota("filter", p, q, "predicado reescrito na forma {field, op, value}")
            return q
        # {"ixps_direct": {"contains": "ce"}} ou {"uf": "SC"}
        if isinstance(v, dict) and len(v) == 1:
            (o, val), = v.items()
            o2 = _OP_SINONIMOS.get(str(o).lower(), str(o).lower())
            if o2 in _OPS:
                q = {"field": k, "op": o2, "value": val}
                anota("filter", p, q, "predicado reescrito na forma {field, op, value}")
                return q
        if not isinstance(v, (dict, list)) and k not in _OPS:
            q = {"field": k, "op": "eq", "value": v}
            anota("filter", p, q, "predicado reescrito na forma {field, op, value}")
            return q
    # vários campos soltos: {"uf": "SC", "has_ipv6": true} → and
    if p and all(isinstance(k, str) and k not in _OPS and not isinstance(v, (dict, list)) for k, v in p.items()):
        q = {"and": [{"field": k, "op": "eq", "value": v} for k, v in p.items()]}
        anota("filter", p, q, "campos soltos reescritos como and de igualdades")
        return q
    return p


def _ptt_em_predicados(f: Any, anota) -> Any:
    if isinstance(f, dict):
        if any(k in f for k in ("and", "or")):
            lig = "and" if "and" in f else "or"
            return {lig: [_ptt_em_predicados(x, anota) for x in f[lig]]}
        if "not" in f:
            return {"not": _ptt_em_predicados(f["not"], anota)}
        if f.get("field") in _CAMPOS_PTT and f.get("op") in ("contains", "ncontains", "eq", "ne", "in", "nin"):
            def conv(x):
                if not isinstance(x, str):
                    return x
                cod, motivo = codigo_ptt(x)
                if cod is None:
                    raise EntradaInvalida(erro_ptt(x))
                if cod != x:
                    anota(f"filter.{f['field']}", x, cod, motivo or "código do PTT em minúsculas")
                return cod
            v = f.get("value")
            return {**f, "value": [conv(x) for x in v] if isinstance(v, list) else conv(v)}
    return f


def _ordenacao(s: Any, anota) -> Any:
    """Formas de `sort` → [{"field": f, "dir": "asc"|"desc"}]."""
    if s is None:
        return None
    itens = s if isinstance(s, list) else [s]
    out = []
    for it in itens:
        orig = it
        if isinstance(it, str):
            t = it.strip()
            if t.startswith("-"):
                it = {"field": t[1:], "dir": "desc"}
            else:
                partes = t.split()
                it = {"field": partes[0], "dir": partes[1].lower() if len(partes) > 1 else "asc"}
        elif isinstance(it, dict):
            it = dict(it)
            if "desc" in it and "dir" not in it:
                it["dir"] = "desc" if it.pop("desc") in (True, "true", 1) else "asc"
            for alt in ("order", "direction", "ordem"):
                if alt in it and "dir" not in it:
                    it["dir"] = str(it.pop(alt)).lower()
            if "ascending" in it and "dir" not in it:
                it["dir"] = "asc" if it.pop("ascending") in (True, "true", 1) else "desc"
            if "dir" in it:
                it["dir"] = {"descending": "desc", "ascending": "asc", "decrescente": "desc", "crescente": "asc"}.get(str(it["dir"]).lower(),
                                                                                                                       str(it["dir"]).lower())
        if it != orig:
            anota("sort", orig, it, "ordenação reescrita na forma {field, dir}")
        out.append(it)
    return out


def _agregacao(a: Any, anota) -> Any:
    """Formas de `aggregate` → [{"fn": f, "field": c}]."""
    if a is None:
        return None
    itens = a if isinstance(a, list) else [a]
    out = []
    for it in itens:
        orig = it
        if isinstance(it, str):
            m = re.fullmatch(r"\s*(\w+)\s*(?:[:(]\s*([\w.]+)\s*\)?)?\s*", it)
            if m:
                it = {"fn": m.group(1).lower(), **({"field": m.group(2)} if m.group(2) else {})}
        elif isinstance(it, dict) and "fn" not in it:
            if "function" in it:
                it = {**{k: v for k, v in it.items() if k != "function"}, "fn": it["function"]}
            elif len(it) == 1:
                (f, c), = it.items()
                it = {"fn": f, **({"field": c} if c not in (None, "*", True) else {})}
        if it != orig:
            anota("aggregate", orig, it, "agregação reescrita na forma {fn, field}")
        out.append(it)
    return out


def _normalizar_query(out: dict, anota) -> None:
    if "collection" in out and isinstance(out["collection"], str):
        out["collection"] = out["collection"].strip().lower()
    f = out.get("filter")
    if isinstance(f, dict) and not f:
        anota("filter", {}, None, "filtro vazio: consulta sem filtro")
        out.pop("filter")
    elif f is not None:
        out["filter"] = _ptt_em_predicados(_predicado(f, anota), anota)
    if "sort" in out:
        out["sort"] = _ordenacao(out["sort"], anota)
    if "aggregate" in out:
        out["aggregate"] = _agregacao(out["aggregate"], anota)
    if isinstance(out.get("group_by"), str):
        anota("group_by", out["group_by"], [out["group_by"]], "group_by vira lista")
        out["group_by"] = [out["group_by"]]
    near = out.get("near")
    if isinstance(near, dict) and isinstance(near.get("ixp"), str):
        cod, motivo = codigo_ptt(near["ixp"])
        if cod is None:
            raise EntradaInvalida(erro_ptt(near["ixp"]))
        if cod != near["ixp"]:
            anota("near.ixp", near["ixp"], cod, motivo or "código do PTT em minúsculas")
            out["near"] = {**near, "ixp": cod}


# ── saída ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def compactar(conteudo: Any, ajustes: list[dict]) -> Any:
    """JSON compacto em cada bloco de texto; `ajustes` acrescentado ao documento quando houver."""
    if not isinstance(conteudo, (list, tuple)):
        return conteudo
    out = []
    for bloco in conteudo:
        txt = getattr(bloco, "text", None)
        if isinstance(txt, str) and txt[:1] in "{[":
            try:
                doc = json.loads(txt)
            except ValueError:
                out.append(bloco)
                continue
            if ajustes and isinstance(doc, dict):
                doc["ajustes"] = ajustes
            bloco = bloco.model_copy(update={"text": json.dumps(doc, ensure_ascii=False, separators=(",", ":"))})
        out.append(bloco)
    return out


def tool_desconhecida(nome: str, existentes: list[str]) -> str:
    perto = difflib.get_close_matches(nome, existentes, n=3, cutoff=0.5)
    return f"Ferramenta desconhecida: {nome!r}." + (f" Parecidas: {', '.join(perto)}." if perto else "") + " Veja a lista em tools/list."
