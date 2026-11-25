# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Interligação de cada PTT na lista `/ixps` (PT-24 / IXPS-E5.4): sessões nos route servers por família e CDNs da lista curada.

Junta dois produtos já publicados (`route_servers/ixps.json.gz` e `cdns.json`) na leitura, sem mexer no que está em `published/`: assim vale também para snapshots antigos.
São fatos medidos na data da coleta e contagens de uma lista curada; nada aqui mede a qualidade do PTT nem diz a causa de uma sessão down.

Regras de leitura:
  * route server sem cache de vizinhos atual (`vizinhos_incerto`) fica fora da contagem e é contado à parte (`rs_sem_vizinhos_atuais`): a sessão dele pode estar velha;
  * família sem nenhum route server consultado vem `null` (n/d), nunca zero;
  * `cdns_curados` é o número de CDNs da lista curada com ASN no cadastro do PTT; PTT sem entrada na lista vem `null` quando o produto não existe, e 0 quando existe e não há CDN.
"""
from __future__ import annotations

from typing import Optional


def sessoes_por_ptt(rs_doc: Optional[dict]) -> dict[str, dict]:
    """`{código: {"v6": {...}|None, "v4": {...}|None, "rs_sem_vizinhos_atuais": n}}` dos PTTs com route server consultado."""
    out: dict[str, dict] = {}
    for code, p in ((rs_doc or {}).get("ixps") or {}).items():
        fam: dict[str, Optional[dict]] = {"v6": None, "v4": None}
        sem_atual = 0
        consultados = 0
        for r in p.get("rs") or []:
            if not r.get("consultado"):
                continue
            consultados += 1
            if r.get("vizinhos_incerto"):
                sem_atual += 1
                continue
            a = r.get("afi")
            if a not in fam:
                continue
            f = fam[a] or {"up": 0, "down": 0, "sessoes": 0, "rs": 0}
            total, up = r.get("sessoes") or 0, r.get("sessoes_up") or 0
            f["sessoes"] += total
            f["up"] += up
            f["down"] += max(0, total - up)
            f["rs"] += 1
            fam[a] = f
        if consultados:
            out[code] = {**fam, "rs_sem_vizinhos_atuais": sem_atual}
    return out


def enriquecer(index: list[dict], rs_doc: Optional[dict], cdns_doc: Optional[dict]) -> list[dict]:
    """Cópia das linhas do índice com `route_servers` (ou `null`) e `cdns_curados` (ou `null`); o índice em cache não é alterado."""
    rs = sessoes_por_ptt(rs_doc)
    cdns = {c["code"]: c.get("cdn_count") for c in ((cdns_doc or {}).get("ixbr_columns") or []) if c.get("code")} if cdns_doc else None
    return [{**e, "route_servers": rs.get(e.get("code")), "cdns_curados": (cdns.get(e.get("code"), 0) if cdns is not None else None)} for e in index]


def fontes(rs_doc: Optional[dict], cdns_doc: Optional[dict], date_str: str) -> dict:
    """Proveniência das duas colunas para a resposta: fonte, data da coleta e tamanho da lista curada."""
    return {
        "route_servers": {"fonte": (rs_doc or {}).get("fonte"), "coletado_em": (rs_doc or {}).get("coletado_em"), "versao_alice": (rs_doc or {}).get("versao_alice")} if rs_doc else None,
        "cdns": {"fonte": "lista curada de CDNs (config/cdns.yaml)", "snapshot": date_str, "cdns_na_lista": len((cdns_doc or {}).get("cdns") or [])} if cdns_doc else None,
    }
