# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Demanda × oferta de banda larga fixa. Saída: `published/{date}/mercado/demanda_oferta.json.gz`, por UF, grande região e Brasil.

  demanda        = domicilios_projetados (IBGE) × proporção de domicílios com banda larga fixa (TIC Domicílios, estimativa do Arandurapé)
  oferta         = acessos fixos de pessoa física declarados ao SICI (mês de referência do snapshot)
  razao          = oferta ÷ demanda
  nao_visto      = max(0, demanda − oferta)

O denominador do IBGE é tratado como fixo: a incerteza vem só da proporção (erro-padrão dos 200 pesos de réplica). Não se usa o total de domicílios dos
microdados porque o erro-padrão dele (13% no Brasil) inflaria o intervalo sem relação com a pergunta. O SICI é declaração, sem erro amostral.
Região e Brasil usam a proporção estimada do próprio grupo e a soma das UFs para domicílios e acessos.

Classe (intervalo de 95% da razão): `oferta_abaixo_da_demanda` (limite superior < 1), `oferta_acima_da_demanda` (limite inferior > 1), `compativel` (o intervalo
contém 1) e `indeterminado` (precisão baixa, CV > 30%, ou grupo suprimido). É diferente do "não visto" do produto `penetracao`, que usa a taxa de uso de internet da PNAD
(inclui quem só usa o celular): aqui o termo de comparação é a banda larga fixa, que é o que o SICI mede.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from core.cetic_microdados import REGIOES_UF
from core.common import now_iso, published_path
from core.jsonio import carregar_json_gz, gravar_json_gz

Z95 = 1.96
LIMITES = (
    "Estimativa do Arandurapé. A demanda é a proporção de domicílios com banda larga fixa da TIC Domicílios (amostra: 700 a 1.500 domicílios por UF) aplicada aos "
    "domicílios do IBGE projetados; a margem vem só da amostra e é menor que a das tabelas oficiais do Cetic.br. A oferta é autodeclaração ao SICI: acesso não é "
    "domicílio (um domicílio pode ter vários acessos ou nenhum) e o mês do SICI não é o da pesquisa. Razão abaixo de 1 não prova que haja provedor sem declarar: "
    "é um sinal para investigar."
)


def _linha(domicilios: float, acessos_pf: int, g: Optional[dict]) -> Optional[dict]:
    """`g`: indicador `banda_larga_fixa` do grupo (proporção, erro_padrão em pp, cv, precisao) ou None."""
    if not g or g.get("proporcao") is None or not domicilios:
        return {"classe": "indeterminado", "motivo": "grupo suprimido ou sem estimativa", "domicilios_projetados": round(domicilios), "oferta_acessos_pf": acessos_pf}
    p, se = g["proporcao"] / 100, g["erro_padrao"] / 100
    demanda, margem = domicilios * p, Z95 * domicilios * se
    r = {"domicilios_projetados": round(domicilios), "proporcao_bl_fixa": g["proporcao"], "proporcao_margem": g["margem"], "demanda_domicilios": round(demanda),
         "demanda_margem": round(margem), "oferta_acessos_pf": acessos_pf, "razao": round(acessos_pf / demanda, 4) if demanda else None,
         "nao_visto": max(0, round(demanda - acessos_pf)), "nao_visto_min": max(0, round(demanda - margem - acessos_pf)),
         "nao_visto_max": max(0, round(demanda + margem - acessos_pf))}
    if demanda - margem > 0:
        r["razao_min"], r["razao_max"] = round(acessos_pf / (demanda + margem), 4), round(acessos_pf / (demanda - margem), 4)
    if g.get("precisao") == "baixa" or "razao_min" not in r:
        r["classe"], r["motivo"] = "indeterminado", "precisão baixa da estimativa (CV > 30%)"
    elif r["razao_max"] < 1:
        r["classe"] = "oferta_abaixo_da_demanda"
    elif r["razao_min"] > 1:
        r["classe"] = "oferta_acima_da_demanda"
    else:
        r["classe"] = "compativel"
    return r


def calcular(ufs_pen: dict[str, dict], grupos: dict[str, dict]) -> dict:
    """`ufs_pen`: `ufs` de territorio/municipios.json.gz; `grupos`: `grupos` de cetic/domicilios_uf.json.gz."""
    def bl(nome: str) -> Optional[dict]:
        return ((grupos.get(nome) or {}).get("indicadores") or {}).get("banda_larga_fixa")

    ufs = {uf: _linha(u["domicilios_projetados"], u["acessos_pf"], bl(uf)) for uf, u in sorted(ufs_pen.items()) if uf in REGIOES_UF}
    regioes: dict[str, dict] = {}
    for reg in sorted(set(REGIOES_UF.values())):
        membros = [ufs_pen[u] for u in REGIOES_UF if REGIOES_UF[u] == reg and u in ufs_pen]
        regioes[reg] = _linha(sum(m["domicilios_projetados"] for m in membros), sum(m["acessos_pf"] for m in membros), bl(reg))
    todos = [u for k, u in ufs_pen.items() if k in REGIOES_UF]
    brasil = _linha(sum(u["domicilios_projetados"] for u in todos), sum(u["acessos_pf"] for u in todos), bl("BR"))
    return {"ufs": ufs, "regioes": regioes, "brasil": brasil}


def publicar_demanda_oferta(base: Path, date_str: str, log) -> dict:
    pub = published_path(base, date_str)
    pen = carregar_json_gz(pub / "territorio" / "municipios.json.gz")
    tic = carregar_json_gz(pub / "cetic" / "domicilios_uf.json.gz")
    if not pen or not tic:
        log.info("penetração ou estimativas da TIC ausentes: demanda × oferta não gerada")
        return {}
    r = calcular(pen["ufs"], tic["grupos"])
    destino = pub / "mercado"
    destino.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino / "demanda_oferta.json.gz", {
        "snapshot_date": date_str, "generated_at": now_iso(), "natureza": "estimativa_arandurape",
        "fonte": "TIC Domicílios (Cetic.br|NIC.br, CC BY 4.0), IBGE e Anatel/SICI", "tic_edicao": tic.get("edicao"), "mes_referencia_sici": pen.get("mes_referencia_sici"),
        "pnad_ano": pen.get("pnad_ano"), "limites": LIMITES, "intervalo": "95% (1,96 × erro-padrão)",
        "formulas": {"demanda": "domicilios_projetados × proporção de domicílios com banda larga fixa (TIC)", "razao": "acessos_pf ÷ demanda",
                     "nao_visto": "max(0, demanda − acessos_pf)", "classe": "intervalo de 95% da razão contra 1; CV > 30% = indeterminado"},
        **r})
    contagem: dict[str, int] = {}
    for u in r["ufs"].values():
        contagem[u["classe"]] = contagem.get(u["classe"], 0) + 1
    log.info("demanda_oferta written", ufs=len(r["ufs"]), **contagem)
    return {"ufs": len(r["ufs"]), **contagem}
