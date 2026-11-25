# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Penetração, mercado não visto e município sem PTT próximo. Funções puras sobre `territorio/municipios.json.gz` e as linhas por município.

Estimativas e fórmulas ficam à vista: toda resposta traz `limites` e `formulas` do artefato, o mês de referência do SICI e o ano do Censo/PNAD.
"""
from __future__ import annotations

from typing import Optional

CAMPOS = {
    "penetracao": "Acessos fixos declarados por domicílio",
    "penetracao_pf": "Acessos fixos de pessoa física por domicílio",
    "nao_visto": "Mercado não visto (estimativa, domicílios)",
    "nao_visto_pct": "Mercado não visto como parcela dos domicílios (estimativa)",
    "populacao": "População (Censo 2022)",
    "populacao_estimada": "População estimada (IBGE, ano mais recente)",
    "domicilios": "Domicílios particulares permanentes ocupados (Censo 2022)",
    "domicilios_projetados": "Domicílios projetados para o ano mais recente da PNAD (estimativa)",
    "acessos": "Acessos fixos declarados",
    "km_ptt": "Distância em linha reta ao PTT mais próximo (km)",
    "fibra_pct": "Parcela de fibra nos acessos fixos declarados (%)",
    "reclam_100mil": "Reclamações na Anatel por 100 mil habitantes (último ano completo; só municípios com 30 ou mais reclamações)",
}


class TerritorioErro(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status, self.mensagem = status, mensagem


def meta(doc: dict) -> dict:
    return {"snapshot_date": doc["snapshot_date"], "mes_referencia_sici": doc["mes_referencia_sici"], "censo_ano": doc["censo_ano"], "estimativa_ano": doc.get("estimativa_ano"), "pnad_ano": doc["pnad_ano"],
            "ano_projecao_domicilios": doc.get("ano_projecao_domicilios"),
            "fonte": doc["fonte"], "formulas": doc["formulas"], "limites": doc["limites"]}


def ranking(doc: dict, linhas: list[dict], campo: str, uf: Optional[str], asc: bool, sem_ptt: Optional[bool], min_domicilios: int, limit: int, offset: int) -> dict:
    if campo not in CAMPOS:
        raise TerritorioErro(400, f"campo inválido: {campo}. Use: {', '.join(CAMPOS)}")
    uf = uf.upper() if uf else None
    sel = [r for r in linhas if (not uf or r["uf"] == uf) and r.get("domicilios", 0) >= min_domicilios
           and (sem_ptt is None or bool(r.get("sem_ptt_proximo")) is sem_ptt) and r.get(campo) is not None]
    if uf and not any(r["uf"] == uf for r in linhas):
        raise TerritorioErro(404, f"UF {uf} desconhecida.")
    sel.sort(key=lambda r: (r[campo], r["ibge"]), reverse=not asc)
    itens = [{"posicao": offset + i + 1, **r} for i, r in enumerate(sel[offset:offset + limit])]
    return {**meta(doc), "criterio": CAMPOS[campo] + (" (crescente)" if asc else " (decrescente)"), "escopo": {"uf": uf} if uf else {"pais": "BR"},
            "filtros": {"sem_ptt_proximo": sem_ptt, "min_domicilios": min_domicilios}, "total": len(sel), "items": itens}


def bloco_municipio(doc: Optional[dict], linhas: list[dict], ibge: str) -> Optional[dict]:
    if not doc or ibge not in doc["municipios"]:
        return None
    ln = next((r for r in linhas if r["ibge"] == ibge), None) or doc["municipios"][ibge]
    return {**meta(doc), **{k: v for k, v in ln.items() if k != "ibge"}}


def bloco_uf(doc: Optional[dict], uf: str) -> Optional[dict]:
    if not doc or uf not in doc["ufs"]:
        return None
    return {**meta(doc), **doc["ufs"][uf]}


# Indicadores do mapa coroplético: cada um é NORMALIZADO e declara a normalização (nunca valor absoluto sem denominador).
MAPA = {
    "penetracao": ("Acessos fixos por 100 domicílios", "acessos fixos declarados ÷ domicílios projetados × 100", lambda r: _x100(r.get("penetracao"))),
    "penetracao_pf": ("Acessos fixos de pessoa física por 100 domicílios", "acessos fixos de pessoa física ÷ domicílios projetados × 100", lambda r: _x100(r.get("penetracao_pf"))),
    "nao_visto_pct": ("Mercado não visto (% dos domicílios, estimativa)", "domicílios com internet sem acesso fixo de pessoa física ÷ domicílios projetados × 100", lambda r: _x100(r.get("nao_visto_pct"))),
    "acessos_por_mil_hab": ("Acessos fixos por mil habitantes", "acessos fixos declarados ÷ população estimada × 1.000", lambda r: _por_mil(r.get("acessos"), r.get("populacao_estimada") or r.get("populacao"))),
    "fibra_pct": ("Fibra nos acessos fixos (%)", "acessos fixos em fibra (meio de acesso declarado ao SICI) ÷ acessos fixos declarados × 100", lambda r: r.get("fibra_pct")),
    "reclam_100mil": ("Reclamações na Anatel por 100 mil habitantes", "reclamações de consumidores registradas na Anatel no último ano completo ÷ população × 100.000, só em municípios com 30 ou mais reclamações; depende da adesão ao canal e do conhecimento dele, não mede qualidade", lambda r: r.get("reclam_100mil")),
    "km_ptt": ("Distância ao PTT mais próximo (km)", "distância em linha reta do centróide do município ao PTT do IX.br mais próximo, em km", lambda r: r.get("km_ptt")),
}


# Indicadores que vêm de outro produto, já normalizados por ele: o mapa de FUST usa `por_10mil_hab` do próprio artefato.
EXTERNOS = {
    "fust_por_10mil_hab": ("Compromissos do FUST por 10 mil habitantes",
                           "compromissos de universalização cadastrados no FUST no município ÷ população × 10.000 (cadastro de obrigações, não desembolso; município sem compromisso fica sem cor)"),
}
INDICADORES = [*MAPA, *EXTERNOS, "ipv6_estimado_pct", "transito_unico_pct"]     # os dois últimos vêm de `rede_territorio`


def mapa_fust(doc: dict, fust: dict) -> dict:
    """`{ibge: compromissos por 10 mil hab.}` dos municípios com compromisso FUST (o valor é do artefato do FUST; o território só dá as datas e os limites)."""
    rotulo, normalizacao = EXTERNOS["fust_por_10mil_hab"]
    valores = {ibge: m["por_10mil_hab"] for ibge, m in fust["municipios"].items() if m.get("por_10mil_hab") is not None}
    return {**meta(doc), "indicador": "fust_por_10mil_hab", "rotulo": rotulo, "normalizacao": normalizacao, "total": len(valores), "valores": valores,
            "fonte_complementar": fust.get("fonte")}


def _x100(v):
    return None if v is None else round(v * 100, 2)


def _por_mil(a, h):
    return round(a / h * 1000, 2) if a is not None and h else None


def mapa(doc: dict, linhas: list[dict], campo: str) -> dict:
    """`{ibge: valor}` de todos os municípios com o indicador (sem dado = ausente, nunca zero), para colorir o mapa de uma vez."""
    if campo not in MAPA:
        raise TerritorioErro(400, f"indicador inválido: {campo}. Use: {', '.join(INDICADORES)}")
    rotulo, normalizacao, f = MAPA[campo]
    valores = {r["ibge"]: v for r in linhas if r.get("ibge") and (v := f(r)) is not None}
    return {**meta(doc), "indicador": campo, "rotulo": rotulo, "normalizacao": normalizacao, "total": len(valores), "valores": valores}


# Municípios semelhantes: mesmo porte, medido em domicílios projetados; é uma regra simples e declarada, não um modelo.
FAIXA_PORTE = 2.0     # semelhante = entre metade e o dobro dos domicílios do município
MAX_SEMELHANTES = 12


def _dom(r: dict):
    return r.get("domicilios_projetados") or r.get("domicilios")


def semelhantes(doc: dict, linhas: list[dict], ibge: str, limite: int = 8) -> dict:
    """Municípios do mesmo porte (domicílios entre metade e o dobro), os mais próximos em tamanho primeiro, e a posição do município em penetração e fibra entre eles."""
    base = next((r for r in linhas if r.get("ibge") == ibge), None)
    if base is None or not _dom(base):
        raise TerritorioErro(404, f"Município {ibge} sem domicílios no território.")
    import math
    d0 = _dom(base)
    pares = [r for r in linhas if r["ibge"] != ibge and _dom(r) and d0 / FAIXA_PORTE <= _dom(r) <= d0 * FAIXA_PORTE]
    pares.sort(key=lambda r: (abs(math.log(_dom(r) / d0)), r["ibge"]))
    limite = max(1, min(limite, MAX_SEMELHANTES))

    def posicao(campo):
        com = [r for r in [base, *pares] if r.get(campo) is not None]
        if base.get(campo) is None:
            return None
        return {"posicao": 1 + sum(1 for r in com if r[campo] > base[campo]), "de": len(com)}

    cols = ("ibge", "nome", "uf", "acessos", "penetracao", "fibra_pct", "km_ptt")
    linha = lambda r: {**{k: r.get(k) for k in cols}, "domicilios": _dom(r)}   # noqa: E731
    return {**meta(doc), "ibge": ibge, "criterio": f"mesmo porte: entre {1 / FAIXA_PORTE:g}× e {FAIXA_PORTE:g}× os domicílios projetados do município",
            "total_do_porte": len(pares) + 1, "municipio": linha(base), "posicao": {"penetracao": posicao("penetracao"), "fibra_pct": posicao("fibra_pct")},
            "items": [linha(r) for r in pares[:limite]]}


# Municípios menores que isto em domicílios ficam fora das listas de penetração (o filtro `dom` da página `/municipios`); o resumo conta quantos são.
PORTE_MINIMO_DOMICILIOS = 1000


def _agrega(rs: list[dict]) -> dict:
    """Soma de um grupo de municípios. Soma só o que existe (ausência não vira zero na linha); a razão usa só os municípios com domicílios projetados."""
    com_dom = [r for r in rs if (r.get("domicilios_projetados") or 0) > 0]
    dom = sum(r["domicilios_projetados"] for r in com_dom)
    acessos_com_dom = sum(r.get("acessos") or 0 for r in com_dom)
    return {
        "municipios": len(rs),
        "populacao_estimada": sum(r.get("populacao_estimada") or r.get("populacao") or 0 for r in rs),
        "domicilios_projetados": sum(r.get("domicilios_projetados") or 0 for r in rs),
        "acessos": sum(r.get("acessos") or 0 for r in rs),
        "nao_visto": sum(r.get("nao_visto") or 0 for r in rs),
        "acessos_por_domicilio": round(acessos_com_dom / dom, 3) if dom else None,
    }


def resumo(doc: dict, linhas: list[dict], uf: Optional[str]) -> dict:
    """Agregados do país (ou de uma UF) por distância ao PTT: a base da síntese de `/municipios` (PT-22). Todos os municípios da tabela do IBGE entram; os grupos
    `a_mais_de_100km` e `ate_100km` não se sobrepõem e `sem_distancia` junta os sem centróide, de modo que as três contagens somam o total. É comparação de médias entre
    grupos, sem causa: renda, urbanização e densidade explicam parte da diferença, e a resposta não afirma nenhuma delas."""
    uf = uf.upper() if uf else None
    if uf and not any(r["uf"] == uf for r in linhas):
        raise TerritorioErro(404, f"UF {uf} desconhecida.")
    sel = [r for r in linhas if not uf or r["uf"] == uf]
    longe = [r for r in sel if r.get("sem_ptt_proximo") is True]
    perto = [r for r in sel if r.get("sem_ptt_proximo") is False]
    sem_dist = [r for r in sel if r.get("sem_ptt_proximo") is None]
    porte = [r for r in sel if (r.get("domicilios") or 0) >= PORTE_MINIMO_DOMICILIOS and r.get("penetracao") is not None]
    return {
        **meta(doc), "escopo": {"uf": uf} if uf else {"pais": "BR"}, "raio_sem_ptt_km": 100,
        "total": _agrega(sel), "a_mais_de_100km": _agrega(longe), "ate_100km": _agrega(perto), "sem_distancia": _agrega(sem_dist),
        "penetracao": {"porte_minimo_domicilios": PORTE_MINIMO_DOMICILIOS, "municipios_com_penetracao": len(porte),
                       "municipios_abaixo_do_porte": sum(1 for r in sel if r.get("domicilios") is not None and r["domicilios"] < PORTE_MINIMO_DOMICILIOS),
                       "municipios_sem_domicilios": sum(1 for r in sel if r.get("domicilios") is None),
                       "com_mais_acessos_que_domicilios": sum(1 for r in porte if r["penetracao"] > 1)},
        "criterio": "agregado por distância em linha reta do centróide do município ao PTT do IX.br mais próximo (100 km); razão = acessos fixos declarados ÷ domicílios projetados, "
                    "só dos municípios com domicílios projetados",
    }
