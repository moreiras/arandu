# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Penetração de banda larga fixa e mercado não visto. Saída: `published/{date}/territorio/municipios.json.gz`
(município, UF e país). Fontes: IBGE (Censo 2022, estimativas de população, PNAD por UF) e o SICI fixo do snapshot.

  domicilios_projetados   = domicílios do Censo 2022 × (domicílios da UF na PNAD do ano mais recente ÷ domicílios da UF na PNAD de 2022)
  penetracao              = acessos fixos declarados ÷ domicilios_projetados
  penetracao_pf           = acessos fixos de pessoa física ÷ domicilios_projetados
  domicilios_com_internet = domicilios_projetados × taxa da UF (PNAD: "havia utilização de internet no domicílio", INCLUI quem usa só o celular)
  nao_visto               = max(0, domicilios_com_internet − acessos fixos de pessoa física)

O Censo é de 2022 e os acessos são de 2026: sem projetar, a penetração sairia inflada. A projeção supõe que o crescimento de domicílios da UF vale igual
para todos os seus municípios (aproximação). O "não visto" é uma ESTIMATIVA: conta como não visto o domicílio que usa internet só pelo móvel, e a taxa é
da UF aplicada ao município. Os limites ficam no próprio artefato (`limites`) e na página Fontes. Município do SICI sem código no IBGE fica de fora e é
contado em `casamento`; município criado depois do Censo (sem domicílios) tem só a população estimada.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from core.common import now_iso, normalized_path, published_path
from core.jsonio import carregar_json_gz, gravar_json_gz

LIMITES = (
    "Estimativa. Os domicílios do Censo 2022 são projetados para o ano mais recente da PNAD pelo crescimento de domicílios da UF, igual para todos os municípios "
    "dela. 'Utilização de internet' (PNAD) inclui quem usa só o celular, então o não visto inclui domicílios sem banda larga fixa por escolha ou por só usarem "
    "o móvel; a taxa é da UF. Acessos de pessoa física não são domicílios (um domicílio pode ter vários acessos ou nenhum). Acessos: SICI do mês de referência."
)


def _razao(a: float, b: float, casas: int = 4) -> Optional[float]:
    return round(a / b, casas) if b else None


def _nao_visto(domicilios: Optional[int], taxa: Optional[float], acessos_pf: int) -> Optional[dict]:
    if not domicilios or taxa is None:
        return None
    com_internet = domicilios * taxa
    nv = max(0, round(com_internet - acessos_pf))
    return {"domicilios_com_internet_est": round(com_internet), "nao_visto": nv, "nao_visto_pct": _razao(nv, domicilios)}


def _fator_projecao(taxa_uf: dict, censo_ano: str, pnad_ano: str) -> Optional[float]:
    serie = taxa_uf.get("domicilios_mil_por_ano") or {}
    base, atual = serie.get(censo_ano), serie.get(pnad_ano)
    return round(atual / base, 6) if base and atual else None


def calcular(ibge_muns: dict[str, dict], taxas_uf: dict[str, dict], sici_muns: dict[str, dict], censo_ano: str = "2022", pnad_ano: str = "2025") -> dict:
    """Município, UF e país. `sici_muns`: `municipios` de sici_municipios.json.gz (acessos, pf, pj por município)."""
    fatores = {uf: _fator_projecao(t, censo_ano, pnad_ano) for uf, t in taxas_uf.items()}
    muns: dict[str, dict] = {}
    for ibge, m in ibge_muns.items():
        s = sici_muns.get(ibge)
        acessos, pf = (s["acessos"], s["pf"]) if s else (0, 0)
        e = {"nome": m["nome"], "uf": m["uf"], "populacao": m.get("populacao"), "populacao_estimada": m.get("populacao_estimada"),
             "area_km2": m.get("area_km2"), "domicilios": m.get("domicilios"), "acessos": acessos, "acessos_pf": pf, "sem_declaracao_sici": s is None}
        dom = m.get("domicilios")
        fator = fatores.get(m["uf"])
        if dom:
            proj = round(dom * fator) if fator else dom                       # sem série da PNAD na UF: fica no nível do Censo, e o fator ausente avisa
            e["domicilios_projetados"] = proj
            if fator:
                e["fator_projecao_uf"] = fator
            e["penetracao"] = _razao(acessos, proj)
            e["penetracao_pf"] = _razao(pf, proj)
            e["penetracao_censo"] = _razao(acessos, dom)
            nv = _nao_visto(proj, (taxas_uf.get(m["uf"]) or {}).get("taxa"), pf)
            if nv:
                e.update(nv)
        muns[ibge] = {k: v for k, v in e.items() if v is not None}

    ufs: dict[str, dict] = {}
    for ibge, e in muns.items():
        u = ufs.setdefault(e["uf"], {"municipios": 0, "populacao": 0, "populacao_estimada": 0, "domicilios": 0, "domicilios_projetados": 0, "acessos": 0, "acessos_pf": 0})
        u["municipios"] += 1
        for k in ("populacao", "populacao_estimada", "domicilios", "domicilios_projetados", "acessos", "acessos_pf"):
            u[k] += e.get(k) or 0
    for uf, u in ufs.items():
        t = taxas_uf.get(uf) or {}
        u["penetracao"] = _razao(u["acessos"], u["domicilios_projetados"])
        u["penetracao_pf"] = _razao(u["acessos_pf"], u["domicilios_projetados"])
        u["penetracao_censo"] = _razao(u["acessos"], u["domicilios"])
        if fatores.get(uf):
            u["fator_projecao_uf"] = fatores[uf]
        if t.get("taxa") is not None:
            u["taxa_internet_pnad"] = t["taxa"]
            u["cv_domicilios_pnad_pct"] = t.get("cv_domicilios_pct")
            u.update(_nao_visto(u["domicilios_projetados"], t["taxa"], u["acessos_pf"]) or {})
        ufs[uf] = {k: v for k, v in u.items() if v is not None}
    soma = ("municipios", "populacao", "populacao_estimada", "domicilios", "domicilios_projetados", "acessos", "acessos_pf", "domicilios_com_internet_est", "nao_visto")
    brasil = {k: sum(u.get(k, 0) for u in ufs.values()) for k in soma}
    brasil["penetracao"] = _razao(brasil["acessos"], brasil["domicilios_projetados"])
    brasil["penetracao_pf"] = _razao(brasil["acessos_pf"], brasil["domicilios_projetados"])
    brasil["penetracao_censo"] = _razao(brasil["acessos"], brasil["domicilios"])
    brasil["nao_visto_pct"] = _razao(brasil["nao_visto"], brasil["domicilios_projetados"])
    return {"municipios": muns, "ufs": dict(sorted(ufs.items())), "brasil": brasil}


def publicar_penetracao(base: Path, date_str: str, log) -> dict:
    pub = published_path(base, date_str)
    norm = normalized_path(base, date_str, "summary")
    ibge = carregar_json_gz(norm / "ibge_municipios.json.gz")
    taxa = carregar_json_gz(norm / "ibge_taxa_internet.json.gz")
    sici = carregar_json_gz(pub / "sici_municipios.json.gz")
    if not ibge or not taxa or not sici:
        log.info("IBGE ou SICI municipal ausente: penetração não gerada")
        return {}
    sici_muns = sici["municipios"]
    r = calcular(ibge["municipios"], taxa["ufs"], sici_muns, ibge["censo_ano"], taxa["pnad_ano"])
    sem_ibge = sorted(set(sici_muns) - set(ibge["municipios"]))
    casados = len(set(sici_muns) & set(ibge["municipios"]))
    destino = pub / "territorio"
    destino.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino / "municipios.json.gz", {
        "snapshot_date": date_str, "generated_at": now_iso(), "mes_referencia_sici": sici["mes_referencia"],
        "censo_ano": ibge["censo_ano"], "estimativa_ano": ibge.get("estimativa_ano"), "pnad_ano": taxa["pnad_ano"], "ano_projecao_domicilios": taxa["pnad_ano"],
        "fonte": "IBGE (Censo 2022, PNAD Contínua) e Anatel/SICI", "limites": LIMITES,
        "formulas": {"domicilios_projetados": "domicilios (Censo) × domicílios da UF na PNAD do ano atual ÷ domicílios da UF na PNAD do ano do Censo",
                     "penetracao": "acessos ÷ domicilios_projetados", "penetracao_pf": "acessos_pf ÷ domicilios_projetados",
                     "nao_visto": "max(0, domicilios_projetados × taxa_internet_uf − acessos_pf)"},
        "casamento": {"sici_municipios": len(sici_muns), "casados_com_ibge": casados, "sem_codigo_no_ibge": sem_ibge,
                      "ibge_municipios": len(ibge["municipios"])},
        **r})
    log.info("penetracao written", municipios=len(r["municipios"]), casados=casados, sem_ibge=len(sem_ibge))
    return {"municipios": len(r["municipios"]), "casados": casados, "sem_codigo_no_ibge": len(sem_ibge)}
