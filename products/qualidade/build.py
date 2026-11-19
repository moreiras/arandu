# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Qualidade (RQUAL) e reclamações da Anatel. Saídas em `published/{date}/qualidade/`.

  * `rqual.json.gz` — indicadores por prestadora (série nacional mensal e por UF e ano), com a ligação prestadora → CNPJ.
  * `rqual_municipios/{UF}.json.gz` — o último resultado de cada município × serviço × prestadora × indicador.
  * `reclamacoes.json.gz` — reclamações por marca, serviço, UF e assunto, a ligação marca → CNPJ e as reclamações por mil acessos (só onde a conta é defensável).
  * `reclamacoes_municipios/{UF}.json.gz` — reclamações por município (últimos anos), marca e serviço.

Sem ranking e sem veredito: são fatos medidos ou declarados, com fonte, período e limites. A tabela marca → CNPJ é curada (`config/curada_marcas_operadoras.yaml`) mais uma
regra automática rotulada; o que não casa fica sem CNPJ.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from core import marcas as m
from core.common import normalized_path, now_iso, published_path
from core.jsonio import carregar_json_gz, gravar_json_gz

LIMITES_RQUAL = (
    "Indicadores do RQUAL (Regulamento de Qualidade) medidos ou apurados pela Anatel, por município, prestadora e serviço, desde 2022. Cobre só as grandes prestadoras de cada serviço: a ausência de uma "
    "empresa aqui não diz nada sobre a qualidade dela. Cada indicador tem a unidade e os valores de referência da própria Anatel, sem juízo do Arandurapé; o sentido de 'melhor' depende do indicador "
    "(consulte a descrição). O resultado de um município pode vir de poucas medidas (veja medidas, erro amostral e intervalo); resultado sem valor (NA, NO, NI) não é somado. A média nacional é "
    "dos municípios medidos (ponderada pelas medidas quando a Anatel as informa) e não é o desempenho da empresa para um cliente."
)
LIMITES_RECLAMACOES = (
    "Solicitações de consumidores registradas na Anatel (reclamações, por mês, município, serviço, marca e assunto), em agregados da própria Anatel; não há texto livre nem dado de quem reclamou. "
    "A marca é o nome que o consumidor escolheu: 'NÃO LOCALIZEI A MINHA EMPRESA' e 'Outros' não identificam ninguém, e a ligação marca → CNPJ é curada ou automática por nome fantasia, nunca "
    "um palpite (marca sem CNPJ aparece como tal). Número de reclamações depende do tamanho da base de clientes: a taxa por mil acessos usa os acessos do SICI de outro período e só aparece para "
    "serviços com acessos declarados no SICI (SCM e SMP). Reclamação não é prova de falha da empresa."
)
SERVICOS_TAXA = {"SCM": ("SCM",), "SMP": ("SMP_Pós", "SMP_Pré")}       # grupo da taxa → serviços da fonte
MIN_RECLAMACOES_TAXA = 30                                               # abaixo disso a taxa por mil acessos oscila demais e não é calculada
MIN_ACESSOS_TAXA = 1000
MAX_POR_MIL = 100                                                       # acima disso (mais de 10% dos acessos reclamando em um ano) o denominador quase certamente está incompleto (marca com mais de um CNPJ)


def _outorgas(norm: Path) -> list[dict]:
    linhas: list[dict] = []
    for nome, chave in (("anatel_scm", "scms"), ("anatel_smp", "smps"), ("anatel_stfc", "stfcs"), ("anatel_seac", "seacs")):
        doc = carregar_json_gz(norm / f"{nome}.json.gz")
        if doc:
            linhas.extend(doc[chave])
    return linhas


def _matrizes(outorgas: list[dict]) -> dict[str, str]:
    """Raiz → CNPJ da matriz (final 0001) ou, sem ele, o primeiro CNPJ visto: só para a interface ligar a marca à página da operadora."""
    r: dict[str, str] = {}
    for o in outorgas:
        c = o.get("cnpj") or ""
        if len(c) == 14 and (c[:8] not in r or c[8:12] == "0001"):
            r[c[:8]] = c
    return r


def _ufs_por_raiz(outorgas: list[dict]) -> dict[str, set[str]]:
    r: dict[str, set[str]] = defaultdict(set)
    for o in outorgas:
        if o.get("uf") and o.get("cnpj"):
            r[o["cnpj"][:8]].add(o["uf"])
    return r


MIN_CONCENTRACAO_UF = 0.8       # parcela das reclamações da marca (últimos 3 anos) que tem de cair nas UFs onde a raiz tem outorga para o casamento automático valer


def _meses_12(ultimo_completo: str) -> tuple[str, str]:
    ano, mes = int(ultimo_completo[:4]), int(ultimo_completo[5:7])
    i = ano * 12 + mes - 1 - 11
    return f"{i // 12:04d}-{i % 12 + 1:02d}", ultimo_completo


def _ultimo_mes_completo(rec: dict) -> str | None:
    """Último mês da fonte antes do mês da extração (o mês da extração pode estar incompleto)."""
    leit = rec["resumo"]["arquivos"].get("reclamacoes_contexto.csv") or {}
    fim, ext = leit.get("mes_final"), (leit.get("data_extracao") or "")[:7]
    if not fim:
        return None
    if ext and fim >= ext:
        i = int(ext[:4]) * 12 + int(ext[5:7]) - 2
        return f"{i // 12:04d}-{i % 12 + 1:02d}"
    return fim


def calcular_rqual(rq: dict, curada: dict, fantasia: dict, matrizes: dict[str, str]) -> dict:
    prest = []
    for p in rq["prestadoras"]:
        c = m.casar(p["prestadora"], curada, fantasia, automatico=False)
        prest.append({**p, "raizes": c["raizes"] if c else [], "cnpjs_matriz": [matrizes[r] for r in c["raizes"] if r in matrizes] if c else [], "casamento": c["metodo"] if c else None, "base_casamento": c["base"] if c else None})
    casadas = sum(1 for p in prest if p["raizes"])
    com = {(p["servico"], p["prestadora"]) for p in prest if p["raizes"]}
    total_res = sum(x["resultados"] for x in rq["nacional"])
    com_res = sum(x["resultados"] for x in rq["nacional"] if (x["servico"], x["prestadora"]) in com)
    return {"municipios_uf": {i: d["uf"] for i, d in rq["municipios"].items()}, "resumo": rq["resumo"], "indicadores": rq["indicadores"], "prestadoras": prest, "nacional": rq["nacional"], "uf": rq["uf"],
            "casamento": {"prestadoras": len(prest), "com_cnpj": casadas, "pct_resultados_com_cnpj": round(100 * com_res / total_res, 2) if total_res else None, "sem_cnpj": [f"{p['prestadora']} ({p['servico']})" for p in prest if not p["raizes"]],
                          "tabela_curada": {"versao": curada["versao"], "curada_em": curada["curada_em"], "fonte": curada["fonte_da_curadoria"]}}}


def _acessos_por_raiz(base: Path, date_str: str) -> tuple[dict, dict]:
    """`({raiz: acessos fixos}, {raiz: acessos móveis})` e o mês de referência de cada base, do SICI publicado."""
    pub = published_path(base, date_str)
    fixo = carregar_json_gz(pub / "sici.json.gz") or {}
    movel = carregar_json_gz(pub / "sici_movel.json.gz") or {}
    def soma(doc):
        r: dict[str, int] = defaultdict(int)
        for cnpj, v in (doc.get("cnpjs") or {}).items():
            r[cnpj[:8]] += v.get("acessos") or 0
        return dict(r)
    return {"SCM": soma(fixo), "SMP": soma(movel)}, {"SCM": fixo.get("mes_referencia"), "SMP": movel.get("mes_referencia")}


def calcular_reclamacoes(rec: dict, curada: dict, fantasia: dict, acessos: dict, mes_sici: dict, ibge: dict | None, matrizes: dict[str, str] | None = None, ufs_raiz: dict[str, set[str]] | None = None) -> tuple[dict, dict]:
    """Devolve `(documento nacional, municípios por UF)`."""
    cache: dict[str, dict | None] = {}
    marca_uf: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for x in rec.get("marca_uf", []):
        marca_uf[x["marca"]][x["uf"]] += x["reclamacoes"]
    descartadas: list[str] = []

    def casa(marca: str):
        if marca not in cache:
            c = m.casar(marca, curada, fantasia)
            if c and c["metodo"] == "automatico":
                total = sum(marca_uf[marca].values())
                ufs = (ufs_raiz or {}).get(c["raizes"][0], set())
                dentro = sum(q for u, q in marca_uf[marca].items() if u in ufs)
                if not total or dentro / total < MIN_CONCENTRACAO_UF:
                    descartadas.append(marca)
                    c = None
            cache[marca] = c
        return cache[marca]
    marcas = []
    for r in rec["marcas"]:
        c = casa(r["marca"])
        marcas.append({**r, "raizes": c["raizes"] if c else [], "cnpjs_matriz": [(matrizes or {})[x] for x in c["raizes"] if x in (matrizes or {})] if c else [], "casamento": c["metodo"] if c else None})
    total = sum(r["reclamacoes"] for r in marcas)
    cob = defaultdict(int)
    for r in marcas:
        cob["curada" if r["casamento"] == "curada" else "automatico" if r["casamento"] == "automatico" else "sem_marca" if r["marca"] in ("NÃO LOCALIZEI A MINHA EMPRESA", "OUTROS") else "sem_cnpj"] += r["reclamacoes"]
    fim = _ultimo_mes_completo(rec)
    taxas: list[dict] = []
    janela = None
    if fim:
        de, ate = janela = _meses_12(fim)
        recl_12: dict[tuple, int] = defaultdict(int)
        for r in rec["marca_mensal"]:
            if de <= r["mes"] <= ate:
                recl_12[(r["marca"], r["servico"])] += r["reclamacoes"]
        for grupo, servs in SERVICOS_TAXA.items():
            for marca in sorted({k[0] for k in recl_12}):
                q = sum(recl_12.get((marca, s), 0) for s in servs)
                c = casa(marca)
                if not q or not c:
                    continue
                ac = sum(acessos.get(grupo, {}).get(r, 0) for r in c["raizes"])
                motivo = None
                if c["metodo"] != "curada":
                    motivo = "a taxa só é calculada para marcas da tabela curada (o denominador do casamento automático não é confirmado)"
                elif q < MIN_RECLAMACOES_TAXA:
                    motivo = f"menos de {MIN_RECLAMACOES_TAXA} reclamações na janela"
                elif ac < MIN_ACESSOS_TAXA:
                    motivo = "sem acessos declarados no SICI (ou menos de 1.000) para as raízes de CNPJ da marca"
                elif q * 1000 / ac > MAX_POR_MIL:
                    motivo = f"razão acima de {MAX_POR_MIL} por mil acessos: o denominador (acessos do SICI nas raízes de CNPJ ligadas) provavelmente não cobre a marca toda"
                taxas.append({"marca": marca, "grupo": grupo, "raizes": c["raizes"], "casamento": c["metodo"], "reclamacoes": q, "acessos": ac or None,
                              "por_mil_acessos": round(q * 1000 / ac, 4) if motivo is None else None, "motivo_sem_taxa": motivo})
    doc = {"municipios_uf": {i: d["uf"] for i, d in rec["municipios"].items()}, "leitura": rec["resumo"], "anos": rec["resumo"]["anos"], "por_mes": rec["por_mes"], "marcas": marcas, "uf": rec["uf"], "assuntos": rec["assuntos"], "marca_assuntos": rec["marca_assuntos"],
           "taxas": {"janela": {"de": janela[0], "ate": janela[1]} if janela else None, "sici_mes_referencia": mes_sici, "itens": taxas,
                     "regra": f"reclamações da janela ÷ acessos do SICI × 1.000; só para marcas da tabela curada, com ≥ {MIN_RECLAMACOES_TAXA} reclamações e ≥ {MIN_ACESSOS_TAXA} acessos e razão de até {MAX_POR_MIL} por mil; SCM usa o SICI fixo e SMP (pós e pré) o SICI móvel"},
           "casamento": {"reclamacoes_total": total, "por_metodo": dict(cob), "pct_com_cnpj": round(100 * (cob["curada"] + cob["automatico"]) / total, 2) if total else None,
                         "automaticas_descartadas_por_uf": sorted(descartadas),
                         "marcas": len({r["marca"] for r in marcas}), "marcas_com_cnpj": len({r["marca"] for r in marcas if r["raizes"]}),
                         "tabela_curada": {"versao": curada["versao"], "curada_em": curada["curada_em"], "fonte": curada["fonte_da_curadoria"], "marcas": len(curada["marcas"])}}}
    pop = {k: (v.get("populacao_estimada") or v.get("populacao")) for k, v in (ibge or {}).get("municipios", {}).items()}
    por_uf: dict[str, dict] = defaultdict(dict)
    for ibge_cod, mun in rec["municipios"].items():
        itens = [{**i, "raizes": (casa(i["marca"]) or {}).get("raizes", [])} for i in mun["itens"]]
        por_uf[mun["uf"]][ibge_cod] = {"nome": mun["nome"], "uf": mun["uf"], "populacao": pop.get(ibge_cod), "itens": itens}
    return doc, por_uf


def _gravar(caminho: Path, doc: dict) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(caminho, doc)


def publicar_qualidade(base: Path, date_str: str, log) -> dict:
    norm = normalized_path(base, date_str, "summary")
    destino = published_path(base, date_str) / "qualidade"
    curada = m.carregar_curada()
    outorgas = _outorgas(norm)
    fantasia = m.indice_fantasia(outorgas)
    matrizes = _matrizes(outorgas)
    saida: dict = {}
    meta = lambda doc: {"snapshot_date": date_str, "generated_at": now_iso(), "data_arquivo": doc.get("data_arquivo"), "url_fonte": doc.get("url")}      # noqa: E731
    rq = carregar_json_gz(norm / "anatel_rqual.json.gz")
    if rq:
        r = calcular_rqual(rq, curada, fantasia, matrizes)
        mun = r["resumo"]["municipios_com_resultado"]
        por_uf: dict[str, dict] = defaultdict(dict)
        for ibge_cod, d in rq["municipios"].items():
            por_uf[d["uf"]][ibge_cod] = d
        for uf, doc in por_uf.items():
            _gravar(destino / "rqual_municipios" / f"{uf}.json.gz", {**meta(rq), "uf": uf, "fonte": "Anatel, dados abertos (RQUAL)", "natureza": "medido_ou_apurado", "municipios": doc})
        _gravar(destino / "rqual.json.gz", {**meta(rq), "fonte": "Anatel, dados abertos (RQUAL)", "natureza": "medido_ou_apurado", "limites": LIMITES_RQUAL, **r})
        saida["rqual"] = {"municipios": mun, "itens_municipais": r["resumo"]["itens_municipais"], "prestadoras": r["casamento"]["prestadoras"], "prestadoras_com_cnpj": r["casamento"]["com_cnpj"]}
        log.info("qualidade/rqual written", **saida["rqual"])
    rc = carregar_json_gz(norm / "anatel_reclamacoes.json.gz")
    if rc:
        acessos, mes_sici = _acessos_por_raiz(base, date_str)
        ibge = carregar_json_gz(norm / "ibge_municipios.json.gz")
        doc, por_uf = calcular_reclamacoes(rc, curada, fantasia, acessos, mes_sici, ibge, matrizes, _ufs_por_raiz(outorgas))
        for uf, mun in por_uf.items():
            _gravar(destino / "reclamacoes_municipios" / f"{uf}.json.gz", {**meta(rc), "uf": uf, "fonte": "Anatel, dados abertos (reclamações)", "natureza": "declarado_por_consumidores",
                                                                                   "anos_municipio": rc["resumo"]["anos_municipio"], "municipios": mun})
        _gravar(destino / "reclamacoes.json.gz", {**meta(rc), "fonte": "Anatel, dados abertos (reclamações)", "natureza": "declarado_por_consumidores", "limites": LIMITES_RECLAMACOES, **doc})
        saida["reclamacoes"] = {"marcas": doc["casamento"]["marcas"], "pct_com_cnpj": doc["casamento"]["pct_com_cnpj"], "taxas": sum(1 for t in doc["taxas"]["itens"] if t["por_mil_acessos"] is not None)}
        log.info("qualidade/reclamacoes written", **saida["reclamacoes"])
    if not saida:
        log.info("RQUAL e reclamações ausentes: qualidade não gerada")
    return saida
