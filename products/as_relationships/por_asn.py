# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Fragmento `relacoes` do documento de ASN: os elos do ASN agrupados em provedores, clientes, pares, irmãos e
sem classificação, cada um com probabilidade, nível e famílias; mais `single_homed`/`multihomed` por família **só com visibilidade
suficiente** (nunca por ausência de dado: `null` = indeterminado).

Contagens de provedores: `n_provedores` usa nível `confirmado` ou superior (a mesma definição do histórico); a decisão de
single-homed olha também os `provavel` (um segundo provedor provável impede afirmar single-homed) e, havendo qualquer provedor só
`possivel`, fica indeterminada."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from products.as_relationships.config import Config

ORDEM_NIVEL = {"declarado": 4, "confirmado": 3, "provavel": 2, "possivel": 1, "sem_classificacao": 0}
LIMITES = {"clientes": 200, "pares": 100, "sem_classificacao": 100, "irmaos": 50, "complexas": 50}


def _item(asn: int, r: dict, nomes: dict[int, str]) -> dict:
    item = {"asn": asn, "p": r["p"], "nivel": r["nivel"], "afi": r["afi"]}
    if r["tipo"] == "complexa":
        c = (r.get("evid") or {}).get("complexa", {})
        item["subtipo"] = c.get("subtipo")
        for afi in ("v4", "v6"):
            v = c.get(afi) or {}
            # papel do OUTRO ASN em cada família, visto deste ASN: provedor | cliente | par
            item[afi] = "par" if v.get("tipo") == "p2p" else ("provedor" if v.get("a") == asn else "cliente") if v else None
    if r.get("estrato"):                                              # só p2c; `p_calibrada` é a taxa de acerto observada no estrato (ou null)
        item["estrato"] = r["estrato"]
        item["p_calibrada"] = r.get("p_calibrada")
    if r.get("pendente"):
        item["mudanca_pendente"] = True
    if nomes.get(asn):
        item["nome"] = nomes[asn][:80]
    return item


def _afis(r: dict) -> set[str]:
    return set(r["afi"])


def _visivel(vps: int, ptts: int, cfg: Config) -> bool:
    return vps >= cfg.visibilidade_min_vps or ptts >= cfg.visibilidade_min_ptt


def por_asn(linhas: Iterable[dict], cfg: Config, coletores: dict[str, bool], nomes: dict[int, str] | None = None,
            calibrada: dict[str, bool] | None = None) -> dict[int, dict]:
    """{asn: documento `relacoes`} para todo ASN que aparece em algum elo. `coletores[afi]`: houve caminhos de coletores nessa família."""
    nomes = nomes or {}
    grupos: dict[int, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    vis: dict[int, dict[str, list[int]]] = defaultdict(lambda: {"v4": [0, 0], "v6": [0, 0]})
    for r in linhas:
        a, b, t = r["a"], r["b"], r["tipo"]
        for asn, outro, papel in ((a, b, "p2c_cli" if t == "p2c" else t), (b, a, "p2c_prov" if t == "p2c" else t)):
            chave = {"p2c_cli": "clientes", "p2c_prov": "provedores", "p2p": "pares", "s2s": "irmaos", "complexa": "complexas",
                     "sem_classificacao": "sem_classificacao"}[papel]
            grupos[asn][chave].append(_item(outro, r, nomes))
            for afi in r["afi"]:
                v = vis[asn][afi]
                v[0], v[1] = max(v[0], r.get("n_vps", 0)), max(v[1], r.get("n_ptt", 0))
    out: dict[int, dict] = {}
    for asn in sorted(grupos):
        g = grupos[asn]
        doc: dict = {"algoritmo": f"ARC v{cfg.versao}", "p_calibrada": {afi: bool((calibrada or {}).get(afi)) for afi in ("v4", "v6")}}
        for chave in ("provedores", "clientes", "pares", "irmaos", "complexas", "sem_classificacao"):
            itens = sorted(g.get(chave, []), key=lambda i: (-ORDEM_NIVEL[i["nivel"]], -i["p"], i["asn"]))
            doc[chave] = itens[:LIMITES.get(chave, 10_000)]
            if len(itens) > len(doc[chave]):
                doc[f"{chave}_total"] = len(itens)
        provs = g.get("provedores", [])
        doc["n_provedores"] = {afi: sum(1 for p in provs if afi in _afis(p) and ORDEM_NIVEL[p["nivel"]] >= 3) for afi in ("v4", "v6")}
        doc["visibilidade"] = {afi: {"vps": vis[asn][afi][0], "ptts": vis[asn][afi][1], "coletores": coletores.get(afi, False)}
                               for afi in ("v4", "v6")}
        multi, single = {}, {}
        for afi in ("v4", "v6"):
            fortes = [p for p in provs if afi in _afis(p) and ORDEM_NIVEL[p["nivel"]] >= 2]
            fracos = [p for p in provs if afi in _afis(p) and ORDEM_NIVEL[p["nivel"]] == 1]
            ok = _visivel(vis[asn][afi][0], vis[asn][afi][1], cfg)
            multi[afi] = True if len(fortes) >= 2 else (False if len(fortes) == 1 and not fracos and ok else None)
            single[afi] = True if len(fortes) == 1 and not fracos and ok else (False if len(fortes) >= 2 else None)
        doc["multihomed"], doc["single_homed"] = multi, single
        out[asn] = doc
    return out
