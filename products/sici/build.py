# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Acessos SICI da Anatel: `sici.json.gz`, `sici_municipios.json.gz`, os móveis e o cruzamento
com ASN (documentos de ASN e SCM). Com `ARANDU_COMPOSE` ligado (padrão), o SICI entra como fragmento."""
from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

from core import compose
from core.common import normalized_path, now_iso, published_path
from core.jsonio import carregar_json_gz, gravar_json_gz
from core.outorgas import SERVICOS
from products.outorgas.build import (aplicar_sici_feature, aplicar_sici_registro, gravar_fragmento_sici,
                                     publicar_outorgas)


# Limiares da divergência APNIC × SICI, calibrados sobre 3.520 ASNs
# comparáveis (mediana 3,97 usuários por acesso; p05 1,08; p95 37,56).
DIVERGENCIA_BAIXA = 1.0    # menos usuários observados que contratos: impossível em
                           # operação normal (3,8% dos ASes)
DIVERGENCIA_ALTA = 20.0    # >20 usuários por contrato não é domicílio: trânsito,
                           # atacado ou CNPJ mal atribuído (10,3% dos ASes)
DIVERGENCIA_MIN_ACESSOS = 100   # amostras menores dão razões instáveis
DIVERGENCIA_MIN_USERS = 100

# Meses de série publicados no snapshot. O cache em disco guarda todo o histórico
# (2007 em diante, ~230 meses), mas o snapshot é carregado INTEIRO na memória da API,
# e a série custa ~0,28 MB não comprimido por mês. Publicar tudo levaria o
# sici.json.gz a ~80 MB (centenas de MB já desserializados em Python). Cinco anos
# cobrem qualquer leitura de tendência da UI; o resto fica no cache, disponível para
# análises offline e para republicar com outro limite se algum dia for preciso.
SERIE_MAX_MESES = 60


def _cnpj_to_asns_map(norm_dir: Path) -> tuple[dict[str, list[int]], dict[int, str]]:
    """CNPJ (14 dígitos) → ASNs, e o inverso, a partir de geo_orgs.json.gz.

    Medido: ASN→CNPJ é 1:1 (nenhum ASN tem mais de um CNPJ), mas 73 CNPJs
    têm mais de um ASN e concentram 48,6% dos acessos do país.
    """
    cnpj_to_asns: dict[str, list[int]] = {}
    asn_to_cnpj: dict[int, str] = {}
    geo_orgs = carregar_json_gz(norm_dir / "geo_orgs.json.gz")
    if not geo_orgs:
        return cnpj_to_asns, asn_to_cnpj
    for asn_str, org in geo_orgs.get("orgs", {}).items():
        cnpj = re.sub(r"\D", "", org.get("cnpj") or "")
        if len(cnpj) == 14:
            asn = int(asn_str)
            cnpj_to_asns.setdefault(cnpj, []).append(asn)
            asn_to_cnpj[asn] = cnpj
    for asns in cnpj_to_asns.values():
        asns.sort()
    return cnpj_to_asns, asn_to_cnpj


def _classify_divergencia(users: Optional[int], acessos: int,
                          compartilhado: bool) -> Optional[dict]:
    """Compara usuários estimados (APNIC) com acessos declarados (Anatel).

    São medições de naturezas diferentes — o APNIC *observa* usuários e atribui a ASN,
    a operadora *declara* contratos por CNPJ. A razão deveria orbitar o número de
    pessoas por domicílio. Divergência é hipótese a investigar, nunca "erro" de uma
    das fontes: a UI e o glossário precisam dizer isso.
    """
    if compartilhado:
        # O CNPJ tem vários ASNs e cada um recebe o total integral — comparar produziria
        # um ranking de operadoras multi-ASN, que é artefato e não achado.
        return {"classificacao": "nao_comparavel", "motivo": "acessos_compartilhados"}
    if not users or users < DIVERGENCIA_MIN_USERS or acessos < DIVERGENCIA_MIN_ACESSOS:
        return {"classificacao": "sem_dados"}
    razao = users / acessos
    if razao < DIVERGENCIA_BAIXA:
        classificacao = "apnic_baixo"
    elif razao > DIVERGENCIA_ALTA:
        classificacao = "apnic_alto"
    else:
        classificacao = "normal"
    return {
        "classificacao": classificacao,
        "razao": round(razao, 2),
        "apnic_users": users,
        "acessos_sici": acessos,
        "faixa_normal": [DIVERGENCIA_BAIXA, DIVERGENCIA_ALTA],
    }


def publicar_sici(base: Path, date_str: str, log, republicar_scm: bool = False) -> dict:
    """
    Publica os acessos declarados ao SICI, cruzados com ASN por CNPJ.

    Lê sici_acessos.json.gz (`anatel_sici`) e geo_orgs.json.gz (enrich/cnpj_geo). Saídas:
      published/{date}/sici.json.gz             — agregado por CNPJ + séries
      published/{date}/sici_municipios.json.gz  — índice invertido IBGE → operadores
    E injeta o bloco `sici` nos documentos de ASN (o índice de ASNs NÃO recebe escalares:
    o SICI é por CNPJ),
    scm.json.gz e maps/scms.geojson — é o que faz a UI existente ganhar os números
    sem precisar de uma segunda requisição.
    """
    norm_dir = normalized_path(base, date_str, "summary")
    sici_path = norm_dir / "sici_acessos.json.gz"
    if not sici_path.exists():
        log.info("sici_acessos not found, skipping SICI build")
        return {}

    data = carregar_json_gz(sici_path)
    if not data:
        return {}

    cnpjs: dict = data.get("cnpjs", {})
    mes_ref = data.get("mes_referencia", "")
    cnpj_to_asns, asn_to_cnpj = _cnpj_to_asns_map(norm_dir)

    # --- cruzamento CNPJ → ASN ---------------------------------------------
    matched = matched_acessos = 0
    for cnpj, agg in cnpjs.items():
        asns = cnpj_to_asns.get(cnpj, [])
        agg["asns"] = asns
        # Um CNPJ com N ASNs tem o total atribuído integralmente a CADA ASN: dividir
        # inventaria número. A flag proíbe somar ASes do mesmo CNPJ.
        agg["acessos_compartilhados"] = len(asns) > 1
        if asns:
            matched += 1
            matched_acessos += agg["acessos"]

    # --- índice invertido por município ------------------------------------
    municipios: dict[str, dict] = {}
    for cnpj, agg in cnpjs.items():
        for ibge, mun in agg.get("por_municipio", {}).items():
            entry = municipios.get(ibge)
            if entry is None:
                entry = municipios[ibge] = {
                    "ibge": ibge, "nome": mun.get("nome", ""), "uf": mun.get("uf", ""),
                    "acessos": 0, "pf": 0, "pj": 0, "capacidade_mbps": 0.0,
                    "operadores": [],
                }
            entry["acessos"] += mun["acessos"]
            # `fibra` falta em meses antigos do SICI: sem o campo em nenhum operador, o % fica ausente.
            if "fibra" in mun:
                entry["fibra"] = entry.get("fibra", 0) + mun["fibra"]
            entry["pf"] += mun["pf"]
            entry["pj"] += mun["pj"]
            entry["capacidade_mbps"] += mun["capacidade_mbps"]
            entry["operadores"].append({
                "cnpj": cnpj,
                "empresa": agg.get("empresa", ""),
                "acessos": mun["acessos"],
                "asns": agg["asns"],
            })

    # Share e concentração (HHI) por município — um município com operador único tem
    # HHI 10000; quanto menor, mais competitivo.
    for entry in municipios.values():
        total = entry["acessos"] or 1
        entry["operadores"].sort(key=lambda o: -o["acessos"])
        hhi = 0.0
        for op in entry["operadores"]:
            op["share"] = round(100 * op["acessos"] / total, 2)
            hhi += op["share"] ** 2
        entry["capacidade_mbps"] = round(entry["capacidade_mbps"], 2)
        if "fibra" in entry:
            entry["fibra_pct"] = round(100 * entry["fibra"] / total, 1)
        entry["operadores_count"] = len(entry["operadores"])
        entry["hhi"] = round(hhi)
        entry["share_maior"] = entry["operadores"][0]["share"] if entry["operadores"] else 0.0

    # --- divergência APNIC × Anatel, por ASN --------------------------------
    apnic = carregar_json_gz(norm_dir / "apnic_pop.json.gz") or {}
    apnic_asns = apnic.get("asns", {})
    divergencias: dict[str, dict] = {}
    for asn, cnpj in asn_to_cnpj.items():
        agg = cnpjs.get(cnpj)
        if not agg:
            continue
        entry = apnic_asns.get(str(asn)) or {}
        div = _classify_divergencia(entry.get("users"), agg["acessos"],
                                    agg["acessos_compartilhados"])
        if div:
            divergencias[str(asn)] = div

    dist = {}
    for d in divergencias.values():
        dist[d["classificacao"]] = dist.get(d["classificacao"], 0) + 1
    log.info("sici divergencia computed", **dist)

    pub_dir = published_path(base, date_str)
    pub_dir.mkdir(parents=True, exist_ok=True)

    output = {
        "snapshot_date":     date_str,
        "generated_at":      now_iso(),
        "fonte":             data.get("fonte", ""),
        "mes_referencia":    mes_ref,
        "meses_disponiveis": data.get("meses_disponiveis", []),
        "total_acessos":     data.get("total_acessos", 0),
        "total_cnpjs":       data.get("total_cnpjs", 0),
        "distrib_velocidade": data.get("distrib_velocidade", {}),
        "matched_cnpjs":     matched,
        "matched_acessos":   matched_acessos,
        "cnpjs":             cnpjs,
        "serie_por_cnpj":    {c: v[-SERIE_MAX_MESES:]
                              for c, v in data.get("serie_por_cnpj", {}).items()},
        "serie_total":       data.get("serie_total", []),
        "cnpj_to_asns":      {c: a for c, a in cnpj_to_asns.items() if c in cnpjs},
        "asn_to_cnpj":       {str(a): c for a, c in asn_to_cnpj.items() if c in cnpjs},
        "divergencia":       divergencias,
    }
    gravar_json_gz(pub_dir / "sici.json.gz", output)
    log.info("sici.json.gz written", cnpjs=len(cnpjs), matched=matched,
             mes_referencia=mes_ref)

    gravar_json_gz(pub_dir / "sici_municipios.json.gz", {
        "snapshot_date": date_str, "mes_referencia": mes_ref,
        "total": len(municipios), "municipios": municipios,
    })
    log.info("sici_municipios.json.gz written", municipios=len(municipios))

    # --- injeção nos artefatos existentes -----------------------------------
    injected_docs = _inject_sici_into_asn_docs(base, date_str, cnpjs, asn_to_cnpj,
                                               divergencias, data, mes_ref, log, recompor=republicar_scm)
    injected_scm = _inject_sici_into_scm(base, date_str, cnpjs, mes_ref, log, republicar_scm)

    return {
        "sici_mes_referencia": mes_ref,
        "sici_cnpjs": len(cnpjs),
        "sici_acessos": output["total_acessos"],
        "sici_matched_cnpjs": matched,
        "sici_municipios": len(municipios),
        "sici_asn_docs": injected_docs,
        "sici_scm_rows": injected_scm,
    }


def _sici_summary(agg: dict, mes_ref: str) -> dict:
    """Resumo servido nas páginas — sem o detalhe municipal, que é grande."""
    return {
        "mes_referencia":         mes_ref,
        "empresa":                agg.get("empresa", ""),
        "grupo":                  agg.get("grupo", ""),
        "porte":                  agg.get("porte", ""),
        "acessos":                agg.get("acessos", 0),
        "pf":                     agg.get("pf", 0),
        "pj":                     agg.get("pj", 0),
        "acessos_internet":       agg.get("acessos_internet", 0),
        "capacidade_mbps":        agg.get("capacidade_mbps", 0.0),
        "capacidade_internet_mbps": agg.get("capacidade_internet_mbps", 0.0),
        "velocidade_media_mbps":  agg.get("velocidade_media_mbps", 0.0),
        "velocidade_mediana_mbps": agg.get("velocidade_mediana_mbps", 0.0),
        "municipios":             agg.get("municipios", 0),
        "tecnologia_predominante": agg.get("tecnologia_predominante", ""),
        "meio_predominante":      agg.get("meio_predominante", ""),
        "por_tecnologia":         agg.get("por_tecnologia", {}),
        "por_meio":               agg.get("por_meio", {}),
        "por_faixa":              agg.get("por_faixa", {}),
        "por_produto":            agg.get("por_produto", {}),
        "acessos_compartilhados": agg.get("acessos_compartilhados", False),
        "asns":                   agg.get("asns", []),
    }


def _inject_sici_into_asn_docs(base: Path, date_str: str, cnpjs: dict,
                               asn_to_cnpj: dict, divergencias: dict,
                               data: dict, mes_ref: str, log, recompor: bool = False) -> int:
    """Grava o bloco `sici` em published/{date}/asns/{asn}.json (ou, com ARANDU_COMPOSE=on, no fragmento `sici`)."""
    asns_dir = published_path(base, date_str, "asns")
    por_fragmento = compose.fluxo_novo(base, date_str)
    if not por_fragmento and not asns_dir.exists():
        return 0
    serie = data.get("serie_por_cnpj", {})
    written = 0
    itens = sorted(asn_to_cnpj.items(), key=lambda kv: int(kv[0])) if por_fragmento else asn_to_cnpj.items()
    frag_ctx = compose.gravar_fragmento(base, date_str, "sici") if por_fragmento else None
    fragmento = frag_ctx.__enter__() if frag_ctx else None
    for asn, cnpj in itens:
        agg = cnpjs.get(cnpj)
        if not agg:
            continue
        path = asns_dir / f"{asn}.json"
        if not por_fragmento and not path.exists():          # no fluxo novo o compose ignora quem não tem `base`
            continue
        block = _sici_summary(agg, mes_ref)
        block["cnpj"] = cnpj
        block["serie"] = serie.get(cnpj, [])
        block["divergencia_apnic_anatel"] = divergencias.get(str(asn))
        if fragmento is not None:
            fragmento.escrever(int(asn), {"sici": block})
            written += 1
            continue
        try:
            doc = json.loads(path.read_bytes())
        except (json.JSONDecodeError, OSError):
            continue
        doc["sici"] = block
        path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        written += 1
    if frag_ctx is not None:
        frag_ctx.__exit__(None, None, None)
        if recompor:                       # só no --sici-only: no run() o compose final é o do `saude_asn`
            compose.recompor(base, date_str, log)
    log.info("sici injected into asn docs", docs=written)
    return written


def _inject_sici_into_scm(base: Path, date_str: str, cnpjs: dict, mes_ref: str,
                          log, republicar_scm: bool = False) -> int:
    """Escalares nas outorgas SCM — distingue licenciado de efetivamente em operação.

    Metade dos CNPJs com outorga não declara nenhum acesso (medido: 20.166 licenciados
    contra 9.776 operando). Sem esse campo a lista sugere que toda outorga é um provedor.

    Com ARANDU_COMPOSE=on esta reescrita some: o SICI vira o fragmento `scm/sici` e o `publicar_outorgas` do SCM o aplica na única escrita.
    """
    if compose.ativo():
        n = gravar_fragmento_sici(base, date_str, cnpjs, mes_ref)
        scm_path = published_path(base, date_str) / "scm.json.gz"
        if republicar_scm and scm_path.exists():    # --sici-only: o SCM já publicado é refeito com o SICI
            from core.outorgas import SERVICOS
            publicar_outorgas(SERVICOS["scm"], base, date_str, log)
        log.info("sici fragment for scm written", cnpjs=n)
        return sum(1 for c in cnpjs)
    scm_path = published_path(base, date_str) / "scm.json.gz"
    if not scm_path.exists():
        return 0
    scm = carregar_json_gz(scm_path)
    if not scm:
        return 0
    touched = 0

    # `by_cnpj` reaponta os mesmos registros de `scms` quando lido em memória, mas são
    # objetos distintos ao vir do JSON — os dois precisam da injeção; só o primeiro conta.
    for rec in scm.get("scms", []):
        if aplicar_sici_registro(rec, cnpjs.get(rec.get("cnpj", "")), mes_ref):
            touched += 1
    for recs in scm.get("by_cnpj", {}).values():
        for rec in recs:
            aplicar_sici_registro(rec, cnpjs.get(rec.get("cnpj", "")), mes_ref)
    gravar_json_gz(scm_path, scm)

    # O GeoJSON do mapa de SCMs também ganha os acessos, para dimensionar as bolhas.
    geo_path = published_path(base, date_str) / "maps" / "scms.geojson"
    if geo_path.exists():
        try:
            geo = json.loads(geo_path.read_bytes())
            for feat in geo.get("features", []):
                aplicar_sici_feature(feat["properties"], cnpjs.get(feat["properties"].get("cnpj", "")), mes_ref)
            geo_path.write_text(json.dumps(geo, ensure_ascii=False), encoding="utf-8")
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("failed to inject sici into scms.geojson", error=str(exc))

    log.info("sici injected into scm", records=touched)
    return touched


def publicar_sici_movel(base: Path, date_str: str, log) -> dict:
    """
    Publica os acessos móveis (SMP) declarados ao SICI, cruzados com ASN por CNPJ.

    Lê sici_movel_acessos.json.gz (`anatel_sici_movel`) e geo_orgs.json.gz (enrich/cnpj_geo). Saídas:
      published/{date}/sici_movel.json.gz             — agregado por CNPJ + séries
      published/{date}/sici_movel_municipios.json.gz  — índice invertido IBGE → operadores

    Escopo desta primeira versão: NÃO injeta em asns/{asn}.json, asns/index.json nem
    smp.json.gz (ao contrário de build_sici_data, que injeta em scm/asn) — e não calcula
    divergência APNIC×Anatel, que não faz sentido do mesmo jeito para o universo móvel
    (poucas operadoras, ASNs compartilhados entre grupo fixo+móvel). Fica para uma
    iteração futura, se a página SMP mostrar que vale a pena.
    """
    norm_dir = normalized_path(base, date_str, "summary")
    sici_path = norm_dir / "sici_movel_acessos.json.gz"
    if not sici_path.exists():
        log.info("sici_movel_acessos not found, skipping SICI móvel build")
        return {}

    data = carregar_json_gz(sici_path)
    if not data:
        return {}

    cnpjs: dict = data.get("cnpjs", {})
    mes_ref = data.get("mes_referencia", "")
    cnpj_to_asns, asn_to_cnpj = _cnpj_to_asns_map(norm_dir)

    matched = matched_acessos = 0
    for cnpj, agg in cnpjs.items():
        asns = cnpj_to_asns.get(cnpj, [])
        agg["asns"] = asns
        agg["acessos_compartilhados"] = len(asns) > 1
        if asns:
            matched += 1
            matched_acessos += agg["acessos"]

    municipios: dict[str, dict] = {}
    for cnpj, agg in cnpjs.items():
        for ibge, mun in agg.get("por_municipio", {}).items():
            entry = municipios.get(ibge)
            if entry is None:
                entry = municipios[ibge] = {
                    "ibge": ibge, "nome": mun.get("nome", ""), "uf": mun.get("uf", ""),
                    "acessos": 0, "pf": 0, "pj": 0, "operadores": [],
                }
            entry["acessos"] += mun["acessos"]
            entry["pf"] += mun["pf"]
            entry["pj"] += mun["pj"]
            entry["operadores"].append({
                "cnpj": cnpj,
                "empresa": agg.get("empresa", ""),
                "acessos": mun["acessos"],
                "asns": agg["asns"],
            })

    for entry in municipios.values():
        total = entry["acessos"] or 1
        entry["operadores"].sort(key=lambda o: -o["acessos"])
        hhi = 0.0
        for op in entry["operadores"]:
            op["share"] = round(100 * op["acessos"] / total, 2)
            hhi += op["share"] ** 2
        entry["operadores_count"] = len(entry["operadores"])
        entry["hhi"] = round(hhi)
        entry["share_maior"] = entry["operadores"][0]["share"] if entry["operadores"] else 0.0

    pub_dir = published_path(base, date_str)
    pub_dir.mkdir(parents=True, exist_ok=True)

    output = {
        "snapshot_date":     date_str,
        "generated_at":      now_iso(),
        "fonte":             data.get("fonte", ""),
        "mes_referencia":    mes_ref,
        "meses_disponiveis": data.get("meses_disponiveis", []),
        "total_acessos":     data.get("total_acessos", 0),
        "total_cnpjs":       data.get("total_cnpjs", 0),
        "distrib_modalidade": data.get("distrib_modalidade", {}),
        "matched_cnpjs":     matched,
        "matched_acessos":   matched_acessos,
        "cnpjs":             cnpjs,
        "serie_por_cnpj":    {c: v[-SERIE_MAX_MESES:]
                              for c, v in data.get("serie_por_cnpj", {}).items()},
        "serie_total":       data.get("serie_total", []),
        "cnpj_to_asns":      {c: a for c, a in cnpj_to_asns.items() if c in cnpjs},
        "asn_to_cnpj":       {str(a): c for a, c in asn_to_cnpj.items() if c in cnpjs},
    }
    gravar_json_gz(pub_dir / "sici_movel.json.gz", output)
    log.info("sici_movel.json.gz written", cnpjs=len(cnpjs), matched=matched,
             mes_referencia=mes_ref)

    gravar_json_gz(pub_dir / "sici_movel_municipios.json.gz", {
        "snapshot_date": date_str, "mes_referencia": mes_ref,
        "total": len(municipios), "municipios": municipios,
    })
    log.info("sici_movel_municipios.json.gz written", municipios=len(municipios))

    return {
        "sici_movel_mes_referencia": mes_ref,
        "sici_movel_cnpjs": len(cnpjs),
        "sici_movel_acessos": output["total_acessos"],
        "sici_movel_matched_cnpjs": matched,
        "sici_movel_municipios": len(municipios),
    }
