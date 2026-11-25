# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Mudanças na matriz de CDNs entre dois snapshots (PT-28 / CDNS-5.4), com a regra de comparabilidade de `core/comparabilidade.py`.

Diferença observada no cadastro de membros dos PTTs do IX.br (`cdns.json`: o ASN da CDN consta, ou deixou de constar, na lista de participantes do PTT). Não diz que a CDN
ligou ou desligou serviço nem a causa: diz o que as duas fotografias mostram. Duas coisas não são mudança da rede e ficam separadas:

  * **catálogo**: a curadoria (`config/cdns.yaml`) não é versionada por snapshot; CDN incluída ou retirada, e ASN incluído ou retirado de uma CDN, aparecem em `catalogo`, e a
    entrada ou saída de PTT dessa CDN não é comparável (`base_diferente`: o conjunto de ASNs mudou);
  * **cobertura**: PTT sem a lista de membros numa das datas não permite dizer que a CDN entrou ou saiu dele (`cobertura_mudou`).

Ordem neutra (por nome da CDN e código do PTT): não é ranking."""
from __future__ import annotations

import hashlib

from core import comparabilidade as comp

LIMITES = ("Cadastro de membros do PTT não é sessão nem tráfego: a CDN que deixou de constar na lista não necessariamente deixou de operar no PTT. "
           "Mudanças de curadoria da lista de CDNs são listadas à parte, e PTT sem lista de membros numa das datas fica fora da comparação.")


def _base(asns: list[int]) -> str:
    return hashlib.sha256(",".join(str(a) for a in sorted(asns)).encode()).hexdigest()[:10]


def mudancas(a: dict, b: dict, ixp_a: list[dict], ixp_b: list[dict]) -> dict:
    """`a` e `b`: `cdns.json` das duas datas (a anterior à b); `ixp_a`/`ixp_b`: `ixps/index.json` de cada data (para a cobertura da lista de membros)."""
    da, db = a["snapshot_date"], b["snapshot_date"]
    cobre = {d: {e["code"]: bool(e.get("ixbr_members_count")) for e in idx} for d, idx in ((da, ixp_a), (db, ixp_b))}
    ca = {c["name"]: c for c in a.get("cdns") or []}
    cb = {c["name"]: c for c in b.get("cdns") or []}
    entradas: list[dict] = []
    saidas: list[dict] = []
    fora: list[dict] = []
    catalogo_asns: list[dict] = []
    for nome in sorted(set(ca) & set(cb), key=str.lower):
        x, y = ca[nome], cb[nome]
        base_a, base_b = _base(x.get("asns") or []), _base(y.get("asns") or [])
        if base_a != base_b:
            sa, sb = set(x.get("asns") or []), set(y.get("asns") or [])
            catalogo_asns.append({"cdn": nome, "asns_incluidos": sorted(sb - sa), "asns_retirados": sorted(sa - sb)})
        ma, mb = set(x.get("ixbr") or []), set(y.get("ixbr") or [])
        for ptt in sorted(ma ^ mb):
            pa = {"date": da, "valor": int(ptt in ma), "meta": {"base": base_a, "coleta_ok": cobre[da].get(ptt, False)}}
            pb = {"date": db, "valor": int(ptt in mb), "meta": {"base": base_b, "coleta_ok": cobre[db].get(ptt, False)}}
            av = comp.avaliar(pa, pb)
            item = {"cdn": nome, "ptt": ptt}
            if not av["comparavel"]:
                fora.append({**item, "motivos": [m["codigo"] for m in av["motivos"]], "detalhes": av["motivos"], "estava": bool(pa["valor"]), "esta": bool(pb["valor"])})
            elif pb["valor"]:
                entradas.append(item)
            else:
                saidas.append(item)
    out = {
        "a": da, "b": db, "entradas": entradas, "saidas": saidas, "nao_comparaveis": fora,
        "catalogo": {"cdns_incluidas": sorted(set(cb) - set(ca), key=str.lower), "cdns_retiradas": sorted(set(ca) - set(cb), key=str.lower), "asns_alterados": catalogo_asns},
        "totais": {"cdns_a": len(ca), "cdns_b": len(cb), "entradas": len(entradas), "saidas": len(saidas), "nao_comparaveis": len(fora)},
        "comparabilidade": {"versao": comp.VERSAO_REGRA, "texto": list(comp.REGRA_COMO_LER),
                            "avisos": comp.avaliar({"date": da, "valor": 0}, {"date": db, "valor": 0})["avisos"]},
        "limites": LIMITES, "fonte": "cadastro de participantes dos PTTs do IX.br e lista curada de CDNs do site", "selo": "fato",
    }
    return out
