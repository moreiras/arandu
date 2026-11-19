# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Mercado do grupo econômico: série e posição do grupo no mercado fixo, onde ele atua, concentração nas suas UFs e concorrentes presentes.

Fatos declarados à Anatel (SICI) com o agrupamento **inferido** do quadro societário. A unidade de comparação é o grupo (com mais de um CNPJ) ou o
CNPJ avulso, a mesma do treemap de `/mercado/maiores`. Soma-se só o que é aditivo (acessos); a concentração (HHI) vem pronta do cruzamento do 1.6.18.
"""
from __future__ import annotations

from typing import Optional

MESES = 24


def unidade_de(grupos: list[dict]) -> dict[str, str]:
    """CNPJ → identificador da unidade (o grupo, se tem mais de um CNPJ; senão o próprio CNPJ)."""
    return {x["cnpj"]: g["grupo_id"] for g in grupos if g.get("tamanho", len(g.get("cnpjs", []))) >= 2 for x in g["cnpjs"]}


def indice(dados: dict, grupos: list[dict], meses: int = MESES) -> dict:
    """Acessos mensais por unidade e a posição de cada uma no último mês e 12 meses antes (entre todas as unidades que declararam)."""
    de = unidade_de(grupos)
    series = dados.get("serie_por_cnpj", {})
    todos = sorted({l[0] for v in series.values() for l in v})
    janela = todos[-meses:]
    ultimo = janela[-1] if janela else None
    antes = janela[-13] if len(janela) >= 13 else None
    por_unidade: dict[str, dict[str, int]] = {}
    for cnpj, linhas in series.items():
        u = de.get(cnpj, cnpj)
        for mes, acessos, *_ in linhas:
            if mes in janela and acessos:
                por_unidade.setdefault(u, {})[mes] = por_unidade.get(u, {}).get(mes, 0) + acessos

    def posicoes(mes: Optional[str]) -> dict[str, int]:
        if not mes:
            return {}
        ordem = sorted((u for u, m in por_unidade.items() if m.get(mes)), key=lambda u: (-por_unidade[u][mes], u))
        return {u: i + 1 for i, u in enumerate(ordem)}

    total_uf: dict[str, int] = {}
    for a in dados.get("cnpjs", {}).values():
        for m in (a.get("por_municipio") or {}).values():
            total_uf[m.get("uf", "")] = total_uf.get(m.get("uf", ""), 0) + m["acessos"]

    return {"total_uf": total_uf, "meses": janela, "ultimo": ultimo, "antes": antes, "por_unidade": por_unidade, "pos_ultimo": posicoes(ultimo), "pos_antes": posicoes(antes),
            "total": {t["mes"]: t["acessos"] for t in dados.get("serie_total", [])}, "de": de}


def mercado_do_grupo(g: dict, idx: dict, dados: dict, mg: Optional[dict]) -> dict:
    """O bloco de mercado de um grupo de `grupos_societarios_overview` (ou de um CNPJ avulso, que é um grupo de uma empresa)."""
    cnpjs = [x["cnpj"] for x in g["cnpjs"]]
    unidade = g["grupo_id"] if g.get("tamanho", len(cnpjs)) >= 2 else cnpjs[0]
    mensal = idx["por_unidade"].get(unidade, {})
    serie = [{"mes": m, "acessos": mensal.get(m), "parcela": round(100 * mensal[m] / idx["total"][m], 3) if mensal.get(m) and idx["total"].get(m) else None} for m in idx["meses"]]
    cad = {c: dados.get("cnpjs", {}).get(c) for c in cnpjs}
    com = [c for c, a in cad.items() if a]
    uf_ac: dict[str, int] = {}
    mun_cnpjs: dict[str, int] = {}
    tecnologia: dict[str, int] = {}
    for c in com:
        for ibge, m in cad[c].get("por_municipio", {}).items():
            uf_ac[m.get("uf", "")] = uf_ac.get(m.get("uf", ""), 0) + m["acessos"]
            mun_cnpjs[ibge] = mun_cnpjs.get(ibge, 0) + 1
        for t, v in (cad[c].get("por_tecnologia") or {}).items():
            tecnologia[t] = tecnologia.get(t, 0) + (v if isinstance(v, int) else v.get("acessos", 0) if isinstance(v, dict) else 0)
    total_uf = idx["total_uf"]
    soma = sum(uf_ac.values())
    ufs_mg = (mg or {}).get("ufs", {})
    por_uf = []
    for u, a in sorted(uf_ac.items(), key=lambda kv: -kv[1]):
        h = ufs_mg.get(u, {})
        por_uf.append({"uf": u, "acessos": a, "parcela_do_grupo": round(100 * a / soma, 2) if soma else None, "parcela_na_uf": round(100 * a / total_uf[u], 2) if total_uf.get(u) else None,
                       "hhi_cnpj": h.get("hhi_cnpj"), "hhi_grupo": h.get("hhi_grupo"), "faixa_grupo": h.get("faixa_grupo")})
    membros = set(cnpjs)
    conc: dict[str, dict] = {}
    for c in cnpjs:
        for x in ((mg or {}).get("sobreposicao", {}).get(c) or []):
            if x.get("mesmo_grupo") or x["cnpj"] in membros:
                continue
            atual = conc.get(x["cnpj"])
            if not atual or x["municipios_em_comum"] > atual["municipios_em_comum"]:
                conc[x["cnpj"]] = {"cnpj": x["cnpj"], "empresa": x.get("empresa"), "municipios_em_comum": x["municipios_em_comum"], "acessos_dele_nos_comuns": x.get("acessos_dele_nos_comuns")}
    p_atual, p_antes = idx["pos_ultimo"].get(unidade), idx["pos_antes"].get(unidade)
    return {
        "grupo_id": g["grupo_id"], "mes_referencia": idx["ultimo"], "meses": idx["meses"], "serie": serie,
        "posicao": {"atual": p_atual, "ha_12_meses": p_antes, "mes_ha_12_meses": idx["antes"], "unidades": len(idx["pos_ultimo"])},
        "cnpjs_total": len(cnpjs), "cnpjs_com_acessos": len(com),
        "por_uf": por_uf, "por_tecnologia": dict(sorted(tecnologia.items(), key=lambda kv: -kv[1])),
        "sobreposicao_interna": {"municipios": len(mun_cnpjs), "com_mais_de_um_cnpj": sum(1 for v in mun_cnpjs.values() if v > 1)},
        "concorrentes": sorted(conc.values(), key=lambda x: -x["municipios_em_comum"])[:8],
        "natureza": "fato (acessos declarados ao SICI, banda larga fixa) com agrupamento inferido",
        "limites": "Posição por acessos declarados do mês, entre todas as empresas ou grupos que declararam; não mede receita nem qualidade. O grupo é inferido do quadro societário e pode juntar empresas independentes. "
                   "A concorrência é presença nos mesmos municípios, não rivalidade; para cada concorrente vale a maior sobreposição com um CNPJ do grupo (não a união).",
    }
