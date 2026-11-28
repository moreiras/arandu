# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Extensões de `GET /ufs` (`include=rede,territorio`, estados 5.4): a camada de rede e o mercado não visto por UF numa só chamada aberta.

`rede` junta, por UF, o que já existe em produtos separados: IPv6 estimado, usuários atrás de ROV e acessos com um só provedor de trânsito
(`rede_territorio`), HHI do trânsito (`transito/ufs`) e a mediana de prontidão em segurança de roteamento (`prontidao`), cada um com o n (ou a cobertura) ao lado.
`territorio` traz o mercado não visto: soma de `nao_visto` dos municípios da UF e a razão por 100 domicílios projetados. Tudo é estimativa ou inferência;
sem o produto na data, o campo sai `null` (ausência, não zero) e o bloco de metadados da resposta diz que o produto falta.
"""
from __future__ import annotations

from typing import Optional

INCLUDES_UFS = {"rede", "territorio"}

AVISO_REDE = ("Estimativas e inferências a partir de rotas observadas e de acessos declarados; não medem tráfego, contratos nem a qualidade de uma empresa. "
              "A UF é a da sede das redes. A prontidão e o HHI do trânsito não são veredito sobre a segurança nem sobre o mercado de um estado e não devem ser lidos como ranking.")


def _rede_por_uf(store, date_str: str) -> tuple[dict[str, dict], dict]:
    rede = store.rede_territorio_doc(date_str)
    transito = store.transito_ufs_doc(date_str)
    pront = store.prontidao_doc(date_str)
    meta: dict = {"aviso": AVISO_REDE, "produtos": {"rede_territorio": bool(rede), "transito": bool(transito), "prontidao": bool(pront)}}
    if rede:
        meta["rede_territorio"] = {"natureza": rede.get("natureza"), "limites": rede.get("limites")}
    if transito:
        meta["transito"] = {"limites": transito.get("limites"), "n": "ASNs com sede na UF e ao menos um provedor de trânsito inferido (`asns_com_provedor`)"}
    if pront:
        meta["prontidao"] = {"natureza": pront.get("natureza"), "limites": pront.get("limites"), "estatistica": "mediana do índice dos ASNs com índice; n = `asns_com_indice`"}
    ufs: set[str] = set()
    if rede:
        ufs |= set(rede["ipv6"]["ufs"]) | set(rede["rov"]["ufs"]) | set(rede["transito"]["ufs"])
    if transito:
        ufs |= set(transito["ufs"])
    if pront:
        ufs |= set(pront["por_uf"])
    out: dict[str, dict] = {}
    for uf in ufs:
        v6 = ((rede or {}).get("ipv6") or {}).get("ufs", {}).get(uf) or {}
        rov = ((rede or {}).get("rov") or {}).get("ufs", {}).get(uf) or {}
        tr = ((rede or {}).get("transito") or {}).get("ufs", {}).get(uf) or {}
        t = ((transito or {}).get("ufs") or {}).get(uf) or {}
        p = ((pront or {}).get("por_uf") or {}).get(uf) or {}
        out[uf] = {
            "ipv6_pct": v6.get("pct_v6"), "ipv6_cobertura": v6.get("cobertura"),
            "rov_pct": rov.get("pct_atras_rov"), "rov_cobertura": rov.get("cobertura"),
            "transito_unico_pct": tr.get("pct_provedor_unico"), "transito_unico_cobertura": tr.get("cobertura"),
            "hhi_transito": t.get("hhi_clientes"), "hhi_transito_n": t.get("asns_com_provedor"),
            "prontidao_mediana": p.get("mediana"), "prontidao_n": p.get("asns_com_indice"),
        }
    return out, meta


def _territorio_por_uf(store, date_str: str) -> tuple[dict[str, dict], dict]:
    """Soma de `nao_visto` por UF e razão por 100 domicílios projetados, só dos municípios que têm a estimativa (o denominador acompanha o numerador)."""
    doc = store.territorio_doc(date_str)
    meta: dict = {"produto": bool(doc)}
    if not doc:
        return {}, meta
    meta.update({"mes_referencia_sici": doc.get("mes_referencia_sici"), "pnad_ano": doc.get("pnad_ano"), "limites": doc.get("limites"),
                 "formula": "soma dos municípios da UF de max(0, domicílios projetados × taxa de Internet da UF − acessos fixos de pessoa física); razão por 100 domicílios projetados dos mesmos municípios"})
    nv: dict[str, int] = {}
    dom: dict[str, int] = {}
    for r in store.territorio_linhas(date_str) or []:
        if r.get("nao_visto") is None:
            continue
        u = (r.get("uf") or "").upper()
        nv[u] = nv.get(u, 0) + int(r["nao_visto"])
        dom[u] = dom.get(u, 0) + int(r.get("domicilios_projetados") or 0)
    return {u: {"nao_visto": n, "nao_visto_por_100_dom": round(100 * n / dom[u], 1) if dom.get(u) else None} for u, n in nv.items()}, meta


def com_extras(store, date_str: str, itens: list[dict], extras: Optional[set[str]]) -> tuple[list[dict], dict]:
    """Devolve as linhas de `resumo_ufs` com `rede` e/ou `territorio` (cada UF, `null` sem o produto) e os metadados a pôr na resposta (`rede_meta`, `territorio_meta`)."""
    if not extras:
        return itens, {}
    rede, meta_rede = _rede_por_uf(store, date_str) if "rede" in extras else ({}, None)
    terr, meta_terr = _territorio_por_uf(store, date_str) if "territorio" in extras else ({}, None)
    out = []
    for r in itens:
        linha = dict(r)
        if meta_rede is not None:
            linha["rede"] = rede.get(r["uf"])
        if meta_terr is not None:
            linha["territorio"] = terr.get(r["uf"])
        out.append(linha)
    meta: dict = {}
    if meta_rede is not None:
        meta["rede_meta"] = meta_rede
    if meta_terr is not None:
        meta["territorio_meta"] = meta_terr
    return out, meta
