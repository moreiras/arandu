# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Qualidade (RQUAL) e reclamações da Anatel a partir de `qualidade/*.json.gz`.

Fatos medidos ou declarados, com fonte, período e limites; **sem ranking nem veredito**: as listas saem em ordem alfabética e nenhuma rota ordena por "pior" ou "melhor".
Reclamações só agregadas (marca, serviço, município, UF, assunto, período).
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional
from core.site import SITE

_META = ("natureza", "fonte", "data_arquivo", "url_fonte", "limites", "snapshot_date")
SERVICOS_RQUAL = ("Banda Larga Fixa", "Telefonia Fixa", "Telefonia Móvel")


def uf_do_municipio(doc: Optional[dict], ibge: str) -> Optional[str]:
    """UF do município pelo índice `municipios_uf` do documento nacional; `None` se o município não está nele."""
    return (doc or {}).get("municipios_uf", {}).get(ibge)


class QualidadeErro(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status, self.mensagem = status, mensagem


def _meta(doc: dict) -> dict:
    return {k: doc.get(k) for k in _META}


def _indicador(doc: dict, servico: str, codigo: str) -> dict:
    for i in doc["indicadores"]:
        if i["servico"] == servico and i["codigo"] == codigo:
            return i
    raise QualidadeErro(400, f"indicador inválido para {servico}: use {', '.join(i['codigo'] for i in doc['indicadores'] if i['servico'] == servico)}.")


def _servico(servico: str) -> str:
    if servico not in SERVICOS_RQUAL:
        raise QualidadeErro(400, f"serviço inválido: use {', '.join(SERVICOS_RQUAL)}.")
    return servico


# ── RQUAL ───────────────────────────────────────────────────────────────────

def resumo(doc: dict) -> dict:
    return {**_meta(doc), "leitura": doc["resumo"], "indicadores": doc["indicadores"], "prestadoras": doc["prestadoras"], "casamento": doc["casamento"]}


def prestadoras(doc: dict, servico: str, indicador: str, uf: Optional[str]) -> dict:
    """Último valor de cada prestadora num indicador: nacional (último mês) ou da UF (último ano). Ordem alfabética: não há ranking."""
    ind = _indicador(doc, _servico(servico), indicador)
    if uf:
        linhas = [x for x in doc["uf"] if x["servico"] == servico and x["indicador"] == indicador and x["uf"] == uf.upper()]
        ref = max((x["ano"] for x in linhas), default=None)
        itens = [x for x in linhas if x["ano"] == ref]
        periodo = {"ano": ref}
    else:
        linhas = [x for x in doc["nacional"] if x["servico"] == servico and x["indicador"] == indicador]
        ref = max((x["mes"] for x in linhas), default=None)
        itens = [x for x in linhas if x["mes"] == ref]
        periodo = {"mes": ref}
    itens.sort(key=lambda x: x["prestadora"])
    cas = {(p["servico"], p["prestadora"]): p for p in doc["prestadoras"]}
    return {**_meta(doc), "indicador": ind, "uf": uf.upper() if uf else None, "periodo": periodo, "ordem": "prestadora (alfabética; sem ranking)",
            "total": len(itens), "items": [{**x, "raizes_cnpj": cas.get((servico, x["prestadora"]), {}).get("raizes", [])} for x in itens]}


def serie(doc: dict, servico: str, indicador: str, prestadora: Optional[str], uf: Optional[str]) -> dict:
    """Série do indicador: mensal nacional ou anual da UF; `prestadora` restringe a uma."""
    ind = _indicador(doc, _servico(servico), indicador)
    if uf:
        linhas = [x for x in doc["uf"] if x["servico"] == servico and x["indicador"] == indicador and x["uf"] == uf.upper()]
        eixo = "ano"
    else:
        linhas = [x for x in doc["nacional"] if x["servico"] == servico and x["indicador"] == indicador]
        eixo = "mes"
    if prestadora:
        n = prestadora.strip().upper()
        linhas = [x for x in linhas if x["prestadora"].upper() == n]
    linhas.sort(key=lambda x: (x["prestadora"], x[eixo]))
    return {**_meta(doc), "indicador": ind, "uf": uf.upper() if uf else None, "granularidade": "anual por UF" if uf else "mensal nacional", "total": len(linhas), "items": linhas}


def municipio(doc_uf: Optional[dict], ibge: str, meta_doc: Optional[dict]) -> Optional[dict]:
    """Último resultado de cada indicador do município, agrupado por serviço e prestadora. `None` se o município não tem RQUAL."""
    if not doc_uf or ibge not in doc_uf["municipios"]:
        return None
    mun = doc_uf["municipios"][ibge]
    grupos: dict[tuple, list] = defaultdict(list)
    for i in mun["itens"]:
        grupos[(i["servico"], i["prestadora"])].append({k: v for k, v in i.items() if k not in ("servico", "prestadora")})
    return {**_meta(doc_uf), "limites": (meta_doc or {}).get("limites"), "ibge": ibge, "nome": mun["nome"], "uf": mun["uf"], "indicadores": (meta_doc or {}).get("indicadores"),
            "prestadoras": [{"servico": s, "prestadora": p, "itens": itens} for (s, p), itens in sorted(grupos.items())]}


def bloco_municipio(doc: Optional[dict], doc_uf: Optional[dict], ibge: str) -> Optional[dict]:
    if not doc:
        return None
    return municipio(doc_uf, ibge, doc)


def bloco_uf(doc: Optional[dict], uf: str) -> Optional[dict]:
    """Por UF: o último ano de cada prestadora × indicador (médias dos municípios medidos)."""
    if not doc:
        return None
    linhas = [x for x in doc["uf"] if x["uf"] == uf]
    if not linhas:
        return None
    ult: dict[tuple, dict] = {}
    for x in linhas:
        k = (x["servico"], x["prestadora"], x["indicador"])
        if k not in ult or x["ano"] > ult[k]["ano"]:
            ult[k] = x
    return {**_meta(doc), "uf": uf, "itens": [ult[k] for k in sorted(ult)], "indicadores": doc["indicadores"]}


def bloco_operadora(doc: Optional[dict], cnpj: str) -> Optional[dict]:
    """RQUAL da operadora pelas raízes de CNPJ ligadas às prestadoras (tabela curada ou nome fantasia único); `None` se nenhuma prestadora do RQUAL casa com o CNPJ."""
    if not doc:
        return None
    raiz = cnpj[:8]
    mine = [p for p in doc["prestadoras"] if raiz in p["raizes"]]
    if not mine:
        return None
    ult: dict[tuple, dict] = {}
    for x in doc["nacional"]:
        k = (x["servico"], x["prestadora"], x["indicador"])
        if k[:2] in {(p["servico"], p["prestadora"]) for p in mine} and (k not in ult or x["mes"] > ult[k]["mes"]):
            ult[k] = x
    return {**_meta(doc), "raiz": raiz, "prestadoras": mine, "itens": [ult[k] for k in sorted(ult)], "indicadores": doc["indicadores"]}


def linhas_uf(doc: Optional[dict]) -> list[dict]:
    """Uma linha por UF × serviço × prestadora × indicador × ano (coleção `qualidade_uf` do `/query`)."""
    if not doc:
        return []
    desc = {(i["servico"], i["codigo"]): i for i in doc["indicadores"]}
    return [{**x, "descricao": desc[(x["servico"], x["indicador"])]["descricao"], "unidade": desc[(x["servico"], x["indicador"])]["unidade"]} for x in doc["uf"]]


# ── reclamações ─────────────────────────────────────────────────────────────

def reclamacoes_resumo(doc: dict) -> dict:
    por_ano: dict[tuple, int] = defaultdict(int)
    for r in doc["por_mes"]:
        if r["tipo"] == "Reclamação":
            por_ano[(int(r["mes"][:4]), r["servico"])] += r["total"]
    ultimo = max(doc["anos"]) if doc["anos"] else None
    assuntos = sorted(((x["servico"], x["assunto"], x["reclamacoes"]) for x in doc["assuntos"] if x["ano"] == ultimo), key=lambda t: (t[0], t[1]))
    return {**_meta(doc), "leitura": doc["leitura"], "casamento": doc["casamento"], "taxas": {k: v for k, v in doc["taxas"].items() if k != "itens"},
            "por_ano_servico": [{"ano": a, "servico": s, "reclamacoes": q} for (a, s), q in sorted(por_ano.items())],
            "assuntos_ano": {"ano": ultimo, "itens": [{"servico": s, "assunto": a, "reclamacoes": q} for s, a, q in assuntos]},
            "uf": doc["uf"]}


def _taxas_por_marca(doc: dict) -> dict[str, list[dict]]:
    r: dict[str, list[dict]] = defaultdict(list)
    for t in doc["taxas"]["itens"]:
        r[t["marca"]].append(t)
    return r


def marcas(doc: dict, servico: Optional[str], ano: Optional[int], q: Optional[str], com_cnpj: Optional[bool], limit: int, offset: int) -> dict:
    """Reclamações por marca no ano (padrão: o último com dado). Ordem alfabética: a ordenação por volume ou por taxa não é oferecida (sem metodologia aprovada)."""
    anos = doc["anos"]
    if ano is not None and ano not in anos:
        raise QualidadeErro(400, f"ano inválido: use {anos[0]} a {anos[-1]}.")
    ref = ano if ano is not None else max(anos)
    linhas = [x for x in doc["marcas"] if x["ano"] == ref and (not servico or x["servico"] == servico)]
    if servico and not any(x["servico"] == servico for x in doc["marcas"]):
        raise QualidadeErro(400, "serviço inválido: use SCM, SMP_Pós, SMP_Pré, STFC, SeAC ou Outros.")
    agr: dict[str, dict] = {}
    for x in linhas:
        a = agr.setdefault(x["marca"], {"marca": x["marca"], "ano": ref, "reclamacoes": 0, "por_servico": {}, "raizes": x["raizes"], "cnpjs_matriz": x.get("cnpjs_matriz", []), "casamento": x["casamento"]})
        a["reclamacoes"] += x["reclamacoes"]
        a["por_servico"][x["servico"]] = x["reclamacoes"]
    taxas = _taxas_por_marca(doc)
    itens = [{**a, "taxas": taxas.get(a["marca"], [])} for a in agr.values()]
    if q:
        n = q.strip().lower()
        itens = [x for x in itens if n in x["marca"].lower()]
    if com_cnpj is not None:
        itens = [x for x in itens if bool(x["raizes"]) == com_cnpj]
    itens.sort(key=lambda x: x["marca"])
    return {**_meta(doc), "ano": ref, "servico": servico, "ordem": "marca (alfabética; sem ranking)", "total": len(itens), "limit": limit, "offset": offset, "items": itens[offset:offset + limit]}


def linhas_marcas(doc: Optional[dict]) -> list[dict]:
    """Uma linha por marca × serviço × ano (coleção `reclamacoes_marca` do `/query`)."""
    return [dict(x) for x in doc["marcas"]] if doc else []


def reclamacoes_municipio(doc_uf: Optional[dict], ibge: str, meta_doc: Optional[dict]) -> Optional[dict]:
    if not doc_uf or ibge not in doc_uf["municipios"]:
        return None
    mun = doc_uf["municipios"][ibge]
    por_ano: dict[int, dict] = {}
    for i in mun["itens"]:
        a = por_ano.setdefault(i["ano"], {"ano": i["ano"], "reclamacoes": 0, "por_servico": defaultdict(int), "marcas": defaultdict(int), "marcas_com_cnpj": {}})
        a["reclamacoes"] += i["reclamacoes"]
        a["por_servico"][i["servico"]] += i["reclamacoes"]
        a["marcas"][(i["marca"], i["servico"])] += i["reclamacoes"]
        if i["raizes"]:
            a["marcas_com_cnpj"][i["marca"]] = i["raizes"]
    anos = []
    pop = mun.get("populacao")
    for ano in sorted(por_ano):
        a = por_ano[ano]
        anos.append({"ano": ano, "reclamacoes": a["reclamacoes"], "por_100mil_hab": round(a["reclamacoes"] * 100000 / pop, 2) if pop else None, "por_servico": dict(a["por_servico"]),
                     "marcas": [{"marca": m, "servico": s, "reclamacoes": q, "raizes": a["marcas_com_cnpj"].get(m, [])} for (m, s), q in sorted(a["marcas"].items())]})
    return {**_meta(doc_uf), "limites": (meta_doc or {}).get("limites"), "ibge": ibge, "nome": mun["nome"], "uf": mun["uf"], "populacao": pop, "anos": anos}


def bloco_reclamacoes_municipio(doc: Optional[dict], doc_uf: Optional[dict], ibge: str) -> Optional[dict]:
    return reclamacoes_municipio(doc_uf, ibge, doc) if doc else None


def bloco_reclamacoes_uf(doc: Optional[dict], uf: str) -> Optional[dict]:
    if not doc:
        return None
    linhas = [x for x in doc["uf"] if x["uf"] == uf]
    if not linhas:
        return None
    por_ano: dict[int, dict] = {}
    for x in linhas:
        a = por_ano.setdefault(x["ano"], {"ano": x["ano"], "reclamacoes": 0, "por_servico": {}})
        a["reclamacoes"] += x["reclamacoes"]
        a["por_servico"][x["servico"]] = x["reclamacoes"]
    return {**_meta(doc), "uf": uf, "anos": [por_ano[a] for a in sorted(por_ano)]}


def bloco_reclamacoes_operadora(doc: Optional[dict], cnpj: str) -> Optional[dict]:
    """Reclamações das marcas ligadas à raiz do CNPJ (tabela curada ou nome fantasia único), por ano e serviço, com a taxa por mil acessos onde defensável. `None` se nenhuma marca casa."""
    if not doc:
        return None
    raiz = cnpj[:8]
    linhas = [x for x in doc["marcas"] if raiz in x["raizes"]]
    if not linhas:
        return None
    marcas_ = sorted({x["marca"] for x in linhas})
    por_ano: dict[int, dict] = {}
    for x in linhas:
        a = por_ano.setdefault(x["ano"], {"ano": x["ano"], "reclamacoes": 0, "por_servico": defaultdict(int)})
        a["reclamacoes"] += x["reclamacoes"]
        a["por_servico"][x["servico"]] += x["reclamacoes"]
    ass = defaultdict(int)
    ultimo = max(doc["anos"])
    for x in doc["marca_assuntos"]:
        if x["marca"] in marcas_ and x["ano"] == ultimo:
            ass[(x["servico"], x["assunto"])] += x["reclamacoes"]
    return {**_meta(doc), "raiz": raiz, "marcas": [{"marca": x, "casamento": next(y["casamento"] for y in linhas if y["marca"] == x)} for x in marcas_],
            "anos": [{**por_ano[a], "por_servico": dict(por_ano[a]["por_servico"])} for a in sorted(por_ano)],
            "assuntos_ano": {"ano": ultimo, "itens": [{"servico": s, "assunto": a, "reclamacoes": q} for (s, a), q in sorted(ass.items())]},
            "taxas": {"janela": doc["taxas"]["janela"], "sici_mes_referencia": doc["taxas"]["sici_mes_referencia"], "regra": doc["taxas"]["regra"],
                      "itens": [t for t in doc["taxas"]["itens"] if raiz in t["raizes"]]},
            "aviso": f"A ligação marca → CNPJ é da tabela curada do {SITE.nome} ou por nome fantasia único; a marca pode agrupar mais de um CNPJ."}


# Mapa municipal de um indicador. A média mistura as prestadoras medidas no município e a faixa só compara com as referências da própria Anatel;
# nenhuma das duas diz "melhor" ou "pior" (o sentido depende do indicador) e nenhuma nomeia empresa.
FAIXAS = {0: "abaixo da referência inferior", 1: "entre as referências", 2: "acima da referência superior"}


def _num(ref: Optional[str]) -> Optional[float]:
    """"90%" → 90.0; `None` se a referência não é um número simples."""
    if not ref:
        return None
    t = str(ref).strip().replace("%", "").replace(" ", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def mapa_municipios(doc: dict, docs_uf: dict[str, dict], servico: str, indicador: str) -> dict:
    """`{ibge: valor}` do último resultado do indicador, média das prestadoras medidas no município (ponderada pelas medidas quando todas as informam),
    e `faixas` ({ibge: 0|1|2}) quando o indicador tem as duas referências numéricas da Anatel."""
    ind = _indicador(doc, _servico(servico), indicador)
    hi_ref, lo_ref = _num(ind.get("referencia_superior")), _num(ind.get("referencia_inferior"))
    valores: dict[str, float] = {}
    n_prest: dict[str, int] = {}
    for uf_doc in docs_uf.values():
        for ibge, mun in (uf_doc or {}).get("municipios", {}).items():
            itens = [i for i in mun["itens"] if i["servico"] == servico and i["indicador"] == indicador and isinstance(i.get("resultado"), (int, float))]
            if not itens:
                continue
            pesos = [i.get("medidas") for i in itens]
            if all(isinstance(p, (int, float)) and p > 0 for p in pesos):
                v = sum(i["resultado"] * p for i, p in zip(itens, pesos)) / sum(pesos)
            else:
                v = sum(i["resultado"] for i in itens) / len(itens)
            valores[ibge] = round(v, 2)
            n_prest[ibge] = len({i["prestadora"] for i in itens})
    faixas = None
    if hi_ref is not None and lo_ref is not None:
        lo, hi = sorted((lo_ref, hi_ref))
        faixas = {ibge: (2 if v > hi else 0 if v < lo else 1) for ibge, v in valores.items()}
    return {**_meta(doc), "servico": servico, "indicador": ind, "unidade": ind.get("unidade"), "total": len(valores), "valores": valores, "prestadoras": n_prest, "faixas": faixas,
            "faixas_rotulos": {str(k): v for k, v in FAIXAS.items()} if faixas is not None else None,
            "referencias": {"superior": ind.get("referencia_superior"), "inferior": ind.get("referencia_inferior")},
            "normalizacao": "média do último resultado das prestadoras medidas no município (ponderada pelas medidas quando todas as informam); não é o desempenho de uma empresa para um cliente"}
