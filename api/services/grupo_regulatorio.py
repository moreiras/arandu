# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Regulatório do grupo econômico: outorgas, multas, qualidade (RQUAL) e reclamações das empresas do grupo.

Soma-se só o que é aditivo e **sem dupla contagem**: multas por raiz de CNPJ (cada raiz entra uma vez); reclamações por (marca, ano, serviço) únicos, porque
uma marca pode estar ligada a mais de uma raiz do grupo; RQUAL sem somar (o valor de uma prestadora é uma média nacional, não aditiva) e sim a lista das
prestadoras ligadas. O grupo é inferido do quadro societário e a ligação marca → CNPJ é curada ou por nome fantasia único: tudo sai com a contagem de quantas
empresas têm o dado e **sem ordenação por multa ou reclamação** (alfabética).
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from api.services import qualidade as q
from api.services import regulatorio as r

SERVICOS = (("has_scm", "SCM"), ("has_smp", "SMP"), ("has_stfc", "STFC"), ("has_seac", "SeAC"))


def _raizes(g: dict) -> dict[str, str]:
    """Raiz do CNPJ → um CNPJ do grupo com essa raiz (matriz e filiais compartilham a raiz)."""
    out: dict[str, str] = {}
    for c in g["cnpjs"]:
        out.setdefault(c["cnpj"][:8], c["cnpj"])
    return out


def regulatorio_do_grupo(g: dict, multas: Optional[dict], rqual: Optional[dict], reclamacoes: Optional[dict], consumidor: Optional[dict]) -> dict:
    raizes = _raizes(g)
    outorgas = {rot: sum(1 for c in g["cnpjs"] if c.get(chave)) for chave, rot in SERVICOS}

    por_raiz = []
    for raiz, cnpj in sorted(raizes.items()):
        m = r.bloco_operadora(multas, cnpj)
        if m:
            por_raiz.append({"raiz": raiz, "empresa": (m["por_grupo"][0].get("entidade") if m["por_grupo"] else None), "multas": m["multas"], "original": m["original"], "pago": m["pago"], "saldo": m["saldo"]})
    por_raiz.sort(key=lambda x: (x["empresa"] or x["raiz"]).lower())          # alfabética: não se ordena por multa
    soma = lambda k: round(sum(x[k] for x in por_raiz), 2)                     # noqa: E731

    prest: dict[tuple, dict] = {}
    for raiz, cnpj in raizes.items():
        b = q.bloco_operadora(rqual, cnpj)
        for p in (b or {}).get("prestadoras", []):
            prest.setdefault((p["servico"], p["prestadora"]), {"servico": p["servico"], "prestadora": p["prestadora"], "municipios": p["municipios"], "casamento": p.get("casamento")})

    linhas: dict[tuple, dict] = {}
    if reclamacoes:
        for x in reclamacoes["marcas"]:
            if raizes.keys() & set(x["raizes"]):
                linhas[(x["marca"], x["ano"], x["servico"])] = x
    por_ano: dict[int, dict] = {}
    for x in linhas.values():
        a = por_ano.setdefault(x["ano"], {"ano": x["ano"], "reclamacoes": 0, "por_servico": defaultdict(int)})
        a["reclamacoes"] += x["reclamacoes"]
        a["por_servico"][x["servico"]] += x["reclamacoes"]
    marcas_anatel = sorted({x["marca"] for x in linhas.values()})

    cons: dict[str, dict] = {}
    if consumidor:
        for x in consumidor["marcas"]:
            if raizes.keys() & set(x["raizes"]):
                cons[x["marca"]] = x
    janela = consumidor["janela"] if consumidor else None
    cons_lista = [{"marca": m, "casamento": x["casamento"], "n": (x.get("janela") or {}).get("n"), "pct_respondidas": (x.get("janela") or {}).get("pct_respondidas"),
                   "indice_solucao": (x.get("janela") or {}).get("indice_solucao"), "nota_media": (x.get("janela") or {}).get("nota_media")} for m, x in sorted(cons.items(), key=lambda kv: kv[0].lower())]
    return {
        "grupo_id": g["grupo_id"], "empresas": len(raizes),
        "outorgas": outorgas,
        "multas": {"empresas_com_registro": len(por_raiz), "multas": sum(x["multas"] for x in por_raiz), "original": soma("original"), "pago": soma("pago"), "saldo": soma("saldo"),
                   "por_empresa": por_raiz, "fonte": (multas or {}).get("fonte"), "limites": (multas or {}).get("limites")},
        "qualidade": {"prestadoras": sorted(prest.values(), key=lambda p: (p["servico"], p["prestadora"])), "limites": (rqual or {}).get("limites")},
        "reclamacoes_anatel": {"marcas": marcas_anatel, "anos": [{**a, "por_servico": dict(a["por_servico"])} for _, a in sorted(por_ano.items())][-8:], "limites": (reclamacoes or {}).get("limites")},
        "consumidor": {"janela": janela, "marcas": cons_lista, "reclamacoes_finalizadas": sum(x["n"] or 0 for x in cons_lista), "limites": (consumidor or {}).get("limites")},
        "natureza": "fato declarado ou registrado por órgãos, somado por agrupamento inferido",
        "limites": "A composição do grupo é inferida do quadro societário e cada soma diz em quantas empresas o dado existe. Tudo em ordem alfabética: sem ordenação por multa nem por reclamação.",
    }
