# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Trânsito por UF e cone de clientes: blocos e linhas do `/query` sobre `transito/ufs.json.gz` e `transito/asns.json.gz`.

Tudo é inferência (ARC v2 sobre rotas observadas): a UF é a da sede da organização e a concentração mede os provedores inferidos dos ASNs da UF, não tráfego.
Toda resposta traz data, fonte e limites.
"""
from __future__ import annotations

from typing import Optional


def _cab(doc: dict) -> dict:
    return {"snapshot_date": doc["snapshot_date"], "fonte": doc.get("fonte"), "limites": doc["limites"], "cobertura": doc.get("cobertura")}


def resumo_ufs(doc: Optional[dict]) -> Optional[dict]:
    """Lista de UFs sem os provedores (o detalhe vem em `/transito/ufs/{uf}`)."""
    if not doc:
        return None
    ufs = [{"uf": uf, **{k: v for k, v in d.items() if k != "provedores"}} for uf, d in sorted(doc["ufs"].items())]
    return {**_cab(doc), "total": len(ufs), "ufs": ufs}


def bloco_uf(doc: Optional[dict], uf: str) -> Optional[dict]:
    if not doc or uf.upper() not in doc["ufs"]:
        return None
    return {**_cab(doc), "uf": uf.upper(), **doc["ufs"][uf.upper()]}


def bloco_asn(doc: Optional[dict], asn: int) -> Optional[dict]:
    """Cone do ASN; `cone_asns = 0` quando o ASN não tem cliente inferido. None só se o produto não foi publicado."""
    if not doc:
        return None
    x = doc["asns"].get(str(asn)) or {"clientes_diretos": 0, "cone_asns": 0, "cone_br": 0, "cone_usuarios": 0, "cone_ufs": {}, "irmaos_excluidos": 0}
    return {**_cab(doc), "asn": asn, "com_cliente": str(asn) in doc["asns"], **x}


def linhas_uf(doc: Optional[dict]) -> list[dict]:
    if not doc:
        return []
    out = []
    for uf, d in sorted(doc["ufs"].items()):
        prov = d.get("provedores") or []
        out.append({"uf": uf, **{k: v for k, v in d.items() if k != "provedores"},
                    "provedor_principal": prov[0]["asn"] if prov else None, "provedor_principal_nome": prov[0].get("nome") if prov else None})
    return out


def linhas_asn(doc: Optional[dict]) -> list[dict]:
    if not doc:
        return []
    return [{"asn": int(a), **{k: v for k, v in d.items() if k != "cone_ufs"}, "n_ufs_cone": len(d.get("cone_ufs") or {})}
            for a, d in sorted(doc["asns"].items(), key=lambda kv: int(kv[0]))]
