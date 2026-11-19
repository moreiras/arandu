# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Bloqueios e interferência medidos pelo OONI: bloco do ASN e tabela do `/query`. Funções puras sobre `bloqueios/asns.json.gz`.

Toda resposta traz a licença (CC BY-NC-SA 4.0), a atribuição, o aviso de que o veredito é da sonda (não do backend do OONI, não é prova de censura), os limites e a janela.
"""
from __future__ import annotations

from typing import Optional

from core import ooni


def _cabecalho(doc: dict) -> dict:
    return {"snapshot_date": doc["snapshot_date"], "coletado_em": doc.get("coletado_em"), "fonte": doc["fonte"], "licenca": doc["licenca"], "aviso": doc["aviso"],
            "limites": doc["limites"], "janela": doc["janela"], "minimo_medicoes": doc["minimo_medicoes"]}


def bloco_asn(doc: Optional[dict], asn: int) -> Optional[dict]:
    """Bloco `bloqueios` do perfil do ASN; None se o produto não foi publicado ou o ASN não tem célula com o mínimo de medições."""
    if not doc or str(asn) not in doc["asns"]:
        return None
    a = doc["asns"][str(asn)]
    return {**_cabecalho(doc), "testes": [{**t, "criterio": ooni.CRITERIOS[t["teste"]]} for t in a["testes"]]}


def linhas(doc: Optional[dict]) -> list[dict]:
    """Uma linha por ASN × teste publicado (coleção `bloqueios_asn` do `/query`). Só células com o mínimo de medições; sem ranking nominal na API."""
    if not doc:
        return []
    j = doc["janela"]
    out = []
    for a, x in doc["asns"].items():
        for c in x["testes"]:
            t = c["teste"]
            ln = {"asn": int(a), "teste": t, "n": c["n"], "anomalias": c["anomalias"], "pct_anomalia": c["pct_anomalia"], "amostra": bool(c.get("amostra")),
                  "janela_inicio": j["inicio"], "janela_fim": j["fim"], "veredito": "da sonda", "licenca": doc["licenca"]}
            out.append(ln)
    out.sort(key=lambda r: (r["asn"], r["teste"]))
    return out
