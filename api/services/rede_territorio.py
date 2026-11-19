# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Rede no território a partir de `territorio/rede_territorio.json.gz`: estimativas e inferências com a suposição e a cobertura à vista."""
from __future__ import annotations

from typing import Optional

INDICADORES = {
    "ipv6_estimado_pct": ("Acessos em IPv6 (estimativa, %)", "acessos fixos × adoção de IPv6 do AS da operadora (APNIC) ÷ acessos com estimativa × 100; supõe a mesma adoção em todos os municípios da operadora",
                          lambda d, i: (d["ipv6"]["municipios"].get(i) or {}).get("pct_v6")),
    "transito_unico_pct": ("Acessos com um único provedor de trânsito (inferido, %)", "acessos das operadoras cujos ASNs têm um só provedor de trânsito inferido ÷ acessos das operadoras com relação inferida × 100",
                           lambda d, i: (d["transito"]["municipios"].get(i) or {}).get("pct_provedor_unico")),
}


def _meta(doc: dict) -> dict:
    return {"snapshot_date": doc["snapshot_date"], "natureza": doc["natureza"], "limites": doc["limites"], "fontes": doc["fontes"]}


def bloco_municipio(doc: Optional[dict], ibge: str) -> Optional[dict]:
    if not doc:
        return None
    v6, tr = doc["ipv6"]["municipios"].get(ibge), doc["transito"]["municipios"].get(ibge)
    return {**_meta(doc), "ipv6": v6, "transito": tr} if (v6 or tr) else None


def bloco_uf(doc: Optional[dict], uf: str) -> Optional[dict]:
    if not doc:
        return None
    v6, rov, tr = doc["ipv6"]["ufs"].get(uf), doc["rov"]["ufs"].get(uf), doc["transito"]["ufs"].get(uf)
    return {**_meta(doc), "ipv6": v6, "rov": rov, "transito": tr} if (v6 or rov or tr) else None


def resumo(doc: dict) -> dict:
    """UFs e país, sem os municípios: o que os panoramas mostram."""
    return {**_meta(doc), "ipv6": {"ufs": doc["ipv6"]["ufs"], "brasil": doc["ipv6"]["brasil"]}, "rov": doc["rov"],
            "transito": {"ufs": doc["transito"]["ufs"]}}


def mapa(doc: dict, indicador: str) -> dict:
    rotulo, normalizacao, f = INDICADORES[indicador]
    valores = {i: v for i in doc["ipv6"]["municipios"].keys() | doc["transito"]["municipios"].keys() if (v := f(doc, i)) is not None}
    return {**_meta(doc), "indicador": indicador, "rotulo": rotulo, "normalizacao": normalizacao, "total": len(valores), "valores": valores}
