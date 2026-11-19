# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Estações do SMP licenciadas por município, UF e operadora. Saída: `published/{date}/erbs/resumo.json.gz`.

Entrada: `anatel_erbs.json.gz` (uma linha por estação licenciada, core/erbs.py), o cadastro do IBGE (nome, UF, população) e as outorgas do SMP (razão social → CNPJ para
as marcas que o arquivo da Anatel traz sem CNPJ). É **cadastro de licenciamento**, não cobertura: estação licenciada pode não estar em operação, e município sem estação
pode ser atendido por estação de município vizinho. A "geração" é a das tecnologias licenciadas na estação (uma estação conta em todas as gerações que tem).
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

from core.common import normalized_path, now_iso, published_path
from core.erbs import GERACOES
from core.jsonio import carregar_json_gz, gravar_json_gz

LIMITES = (
    "Estações do SMP licenciadas na Anatel (cadastro de licenciamento): não é cobertura nem sinal, e licenciada não quer dizer em operação. Cada estação é um número do cadastro, não uma "
    "torre física (uma torre pode ter mais de uma). Município sem estação pode ser atendido pelas de municípios vizinhos. Gerações = tecnologias licenciadas (2G GSM, 3G WCDMA, 4G LTE, 5G NR)."
)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]+", " ", s).strip()


def _cnpj_por_razao(smps: list[dict]) -> dict[str, str]:
    return {_norm(s["razao_social"]): s["cnpj"] for s in smps if s.get("razao_social") and s.get("cnpj")}


def _contagem_geracoes(ests: list[dict]) -> dict[str, int]:
    return {g: sum(1 for e in ests if g in e["geracoes"]) for g in GERACOES}


def calcular(estacoes: list[dict], ibge_muns: dict[str, dict], smps: list[dict], sici_movel_muns: Optional[dict] = None) -> dict:
    por_razao = _cnpj_por_razao(smps)
    sem_cnpj_arquivo = 0
    for e in estacoes:
        if not e.get("cnpj"):
            sem_cnpj_arquivo += 1
            e["cnpj"] = por_razao.get(_norm(e.get("entidade", "")))
    pm: dict[str, list[dict]] = defaultdict(list)
    for e in estacoes:
        if e.get("ibge") in ibge_muns:
            pm[e["ibge"]].append(e)
    chave = lambda e: e.get("cnpj") or e.get("marca") or "?"            # noqa: E731
    municipios = {}
    for ibge, ests in sorted(pm.items()):
        pop = ibge_muns[ibge].get("populacao_estimada") or ibge_muns[ibge].get("populacao")
        municipios[ibge] = {"nome": ibge_muns[ibge].get("nome"), "uf": ibge_muns[ibge]["uf"], "estacoes": len(ests), "geracoes": _contagem_geracoes(ests), "operadoras": dict(Counter(chave(e) for e in ests).most_common()),
                            **({"por_10mil_hab": round(len(ests) * 10000 / pop, 2)} if pop else {})}
    ufs: dict[str, dict] = {}
    for uf in sorted({m["uf"] for m in ibge_muns.values()}):
        ests = [e for ibge, lst in pm.items() if ibge_muns[ibge]["uf"] == uf for e in lst]
        muns_uf = [i for i, m in ibge_muns.items() if m["uf"] == uf]
        ufs[uf] = {"estacoes": len(ests), "municipios": len(muns_uf), "municipios_com_estacao": sum(1 for i in muns_uf if i in pm), "geracoes": _contagem_geracoes(ests),
                   "municipios_com_5g": sum(1 for i in muns_uf if i in pm and any("5G" in e["geracoes"] for e in pm[i])), "operadoras": len({chave(e) for e in ests})}
    ops: dict[str, dict] = {}
    for e in estacoes:
        o = ops.setdefault(chave(e), {"cnpj": e.get("cnpj"), "marca": e.get("marca"), "entidade": e.get("entidade"), "estacoes": 0, "_m": set(), "_u": set(), "tipo_5g": Counter()})
        o["estacoes"] += 1
        if e.get("ibge") in ibge_muns:
            o["_m"].add(e["ibge"])
            o["_u"].add(ibge_muns[e["ibge"]]["uf"])
        for t in e.get("tipo_5g", []):
            o["tipo_5g"][t] += 1
    operadoras = []
    for k, o in ops.items():
        ests = [e for e in estacoes if chave(e) == k]
        operadoras.append({"cnpj": o["cnpj"], "marca": o["marca"], "entidade": o["entidade"], "estacoes": o["estacoes"], "municipios": len(o["_m"]), "ufs": len(o["_u"]),
                           "geracoes": _contagem_geracoes(ests), "tipo_5g": dict(o["tipo_5g"])})
    operadoras.sort(key=lambda o: -o["estacoes"])
    brasil = {"estacoes": len(estacoes), "estacoes_em_municipio_do_ibge": sum(len(v) for v in pm.values()), "municipios": len(ibge_muns), "municipios_com_estacao": len(pm),
              "municipios_com_5g": sum(1 for v in pm.values() if any("5G" in e["geracoes"] for e in v)), "geracoes": _contagem_geracoes(estacoes), "operadoras": len(operadoras)}
    casamento = {"estacoes": len(estacoes), "com_municipio_no_ibge": brasil["estacoes_em_municipio_do_ibge"], "sem_cnpj_no_arquivo": sem_cnpj_arquivo,
                 "sem_cnpj_apos_razao_social": sum(1 for e in estacoes if not e.get("cnpj")),
                 "marcas_sem_cnpj": sorted({e.get("marca") for e in estacoes if not e.get("cnpj")} - {None, ""})}
    if sici_movel_muns is not None:
        com_acesso = {i for i, m in sici_movel_muns.items() if m.get("acessos")}
        casamento["sanidade_sici_movel"] = {"municipios_com_acessos_moveis": len(com_acesso), "dos_quais_com_estacao": len(com_acesso & set(pm)),
                                            "com_estacao_sem_acessos_moveis": len(set(pm) - com_acesso)}
    return {"brasil": brasil, "ufs": ufs, "operadoras": operadoras, "municipios": municipios, "casamento": casamento}


PASSO_GRADE = 0.02                                                      # graus (~2 km): 114 mil estações viram ~32 mil células, o que cabe numa camada de mapa (12 MB em pontos)


def grade(estacoes: list[dict], passo: float = PASSO_GRADE) -> list[list]:
    """Células da grade: [lon, lat do centro, estações, com 2G, 3G, 4G, 5G]. Estação sem posição fica de fora (contada em `casamento`)."""
    cel: dict[tuple[int, int], list[int]] = {}
    for e in estacoes:
        if e.get("lat") is None or e.get("lon") is None:
            continue
        c = cel.setdefault((math.floor(e["lat"] / passo), math.floor(e["lon"] / passo)), [0, 0, 0, 0, 0])
        c[0] += 1
        for i, g in enumerate(GERACOES, 1):
            c[i] += g in e["geracoes"]
    return [[round((j + 0.5) * passo, 4), round((i + 0.5) * passo, 4), *v] for (i, j), v in sorted(cel.items())]


def publicar_erbs(base: Path, date_str: str, log) -> dict:
    norm = normalized_path(base, date_str, "summary")
    pub = published_path(base, date_str)
    doc = carregar_json_gz(norm / "anatel_erbs.json.gz")
    ibge = carregar_json_gz(norm / "ibge_municipios.json.gz")
    if not doc or not ibge:
        log.info("estações do SMP ou IBGE ausentes: erbs não geradas")
        return {}
    smp = carregar_json_gz(pub / "smp.json.gz") or {}
    sm = carregar_json_gz(pub / "sici_movel_municipios.json.gz") or {}
    r = calcular(doc["estacoes"], ibge["municipios"], smp.get("smps") or [], sm.get("municipios") if sm else None)
    destino = pub / "erbs"
    destino.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino / "resumo.json.gz", {
        "snapshot_date": date_str, "generated_at": now_iso(), "fonte": "Anatel, dados abertos (estações do SMP licenciadas) e IBGE", "data_arquivo": doc.get("data_arquivo"),
        "natureza": "cadastro_licenciamento", "limites": LIMITES, **r})
    gravar_json_gz(destino / "grade.json.gz", {"snapshot_date": date_str, "generated_at": now_iso(), "passo_graus": PASSO_GRADE, "natureza": "cadastro_licenciamento", "limites": LIMITES,
                                              "colunas": ["lon", "lat", "estacoes", "g2", "g3", "g4", "g5"], "celulas": grade(doc["estacoes"])})
    log.info("erbs written", estacoes=r["brasil"]["estacoes"], municipios_com_estacao=r["brasil"]["municipios_com_estacao"])
    return {"estacoes": r["brasil"]["estacoes"], "municipios_com_estacao": r["brasil"]["municipios_com_estacao"], "sem_cnpj": r["casamento"]["sem_cnpj_apos_razao_social"]}
