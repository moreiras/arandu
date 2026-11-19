# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Produto `transito`: concentração do trânsito por UF e cone de clientes (customer cone) dos ASNs.

Entrada: `published/{date}/as_relationships.json.gz` (ARC v2): usa só as relações p2c de nível `provavel` ou superior (o
estado publicado, depois da histerese); elos `complexa`, `s2s` e `sem_classificacao` não entram. Saídas:
  published/{date}/transito/ufs.json.gz    por UF: provedores dos ASNs com sede na UF, participação e concentração (HHI, top 1 e 3)
  published/{date}/transito/asns.json.gz   por ASN: cone de clientes (todos e só do Brasil), usuários estimados e UFs no cone

Tudo é **inferência** sobre relações inferidas: a UF é a da sede da organização (geo_org), o provedor é o que o ARC infere nos caminhos
BGP observados e o número de usuários é estimativa APNIC. Não é a lista de contratos de trânsito de ninguém.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

from core.common import configure_logging, data_dir, normalized_path, now_iso, published_path, read_json_gz, today_str, write_json_gz
from products.as_relationships import restricoes
from products.as_relationships.config import carregar
from products.seguranca.build import _docs_br

NIVEIS_FIRMES = ("declarado", "confirmado", "provavel")
LIMITES = ("Relações p2c inferidas pelo ARC v2 (probabilidade e nível por elo; veja `as_relationships`) em nível provável ou superior, no estado publicado depois da histerese. "
           "Só existem elos com ao menos um ASN brasileiro: provedores estrangeiros aparecem, mas o cone de um ASN estrangeiro só conta o que tem ligação com o Brasil. "
           "UF = sede da organização, não onde o trânsito é entregue. Concentração mede quem os ASNs da UF têm como provedor inferido, não volume de tráfego. "
           "Usuários são estimativa APNIC e se repetem em cada ASN da mesma operadora. Irmãos (mesmo CNPJ raiz ou organização do CAIDA) não contam como clientes.")


def _p2c(doc: dict) -> dict[int, dict[int, dict]]:
    """{provedor: {cliente: {p, nivel}}} das relações p2c firmes; se o par aparece em duas famílias fica o de maior p."""
    out: dict[int, dict[int, dict]] = defaultdict(dict)
    for r in doc.get("relacoes", []):
        if r["tipo"] != "p2c" or r["nivel"] not in NIVEIS_FIRMES:
            continue
        atual = out[r["a"]].get(r["b"])
        if atual is None or r["p"] > atual["p"]:
            out[r["a"]][r["b"]] = {"p": r["p"], "nivel": r["nivel"]}
    return out


def cone(cliente_de: dict[int, dict[int, dict]], raiz: int, excluir: set[int]) -> set[int]:
    """Clientes diretos e indiretos de `raiz` (busca em largura; seguro com ciclos), sem `excluir` (o próprio ASN e os irmãos)."""
    visto = {raiz}
    fila = [raiz]
    while fila:
        x = fila.pop()
        for c in cliente_de.get(x, ()):
            if c not in visto:
                visto.add(c)
                fila.append(c)
    return visto - excluir


def calcular(rel: dict, docs_br: dict[int, dict], irmaos: dict[int, int], nomes: dict[int, str], cfg) -> tuple[dict, dict, dict]:
    """`(asns, ufs, cobertura)`. `docs_br`: {asn: {uf, usuarios}} dos ASNs do Brasil."""
    cliente_de = _p2c(rel)
    provedores_de: dict[int, dict[int, dict]] = defaultdict(dict)
    for p, cs in cliente_de.items():
        for c, v in cs.items():
            provedores_de[c][p] = v
    br = set(docs_br)

    asns: dict[str, dict] = {}
    for p in sorted(cliente_de):
        grupo = {a for a, g in irmaos.items() if g == irmaos.get(p)} if p in irmaos else set()
        c = cone(cliente_de, p, {p} | grupo)
        c_br = c & br
        if not c:
            continue
        por_uf: dict[str, int] = defaultdict(int)
        for a in c_br:
            if docs_br[a].get("uf"):
                por_uf[docs_br[a]["uf"]] += 1
        asns[str(p)] = {"clientes_diretos": sum(1 for x in cliente_de[p] if x not in grupo), "cone_asns": len(c), "cone_br": len(c_br),
                        "cone_usuarios": sum(int(docs_br[a].get("usuarios") or 0) for a in c_br), "cone_ufs": dict(sorted(por_uf.items())),
                        "irmaos_excluidos": len(grupo - {p}), "br": p in br}
    ordem = sorted(asns, key=lambda a: (-asns[a]["cone_br"], -asns[a]["cone_asns"], int(a)))
    for i, a in enumerate(ordem, 1):
        asns[a]["posicao_cone_br"] = i

    ufs: dict[str, dict] = {}
    por_uf_asns: dict[str, list[int]] = defaultdict(list)
    for a, d in docs_br.items():
        if d.get("uf"):
            por_uf_asns[d["uf"]].append(a)
    for uf, lista in sorted(por_uf_asns.items()):
        com = [a for a in lista if provedores_de.get(a)]
        cli: dict[int, list[int]] = defaultdict(list)
        for a in com:
            for p in provedores_de[a]:
                cli[p].append(a)
        total_elos = sum(len(v) for v in cli.values())
        total_usr = sum(sum(int(docs_br[a].get("usuarios") or 0) for a in v) for v in cli.values())
        provs = []
        for p, v in sorted(cli.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            usr = sum(int(docs_br[a].get("usuarios") or 0) for a in v)
            provs.append({"asn": p, "nome": nomes.get(p), "br": p in br, "clientes_uf": len(v), "usuarios_uf": usr,
                          "share_clientes": round(len(v) / total_elos, 4) if total_elos else None,
                          "share_usuarios": round(usr / total_usr, 4) if total_usr else None})
        sh = [x["share_clientes"] for x in provs if x["share_clientes"] is not None]
        hhi = round(sum(s * s for s in sh) * 10000) if sh else None
        ufs[uf] = {"asns_br": len(lista), "asns_com_provedor": len(com), "pct_com_provedor": round(100 * len(com) / len(lista), 1),
                   "elos_provedor": total_elos, "provedores_distintos": len(provs), "hhi_clientes": hhi,
                   "top1_share": sh[0] if sh else None, "top3_share": round(sum(sh[:3]), 4) if sh else None,
                   "share_provedores_estrangeiros": round(sum(x["clientes_uf"] for x in provs if not x["br"]) / total_elos, 4) if total_elos else None,
                   "provedores": provs[:20]}
    cobertura = {"asns_br": len(br), "asns_br_com_provedor": sum(1 for a in br if provedores_de.get(a)),
                 "asns_com_cone": len(asns), "elos_p2c_firmes": sum(len(v) for v in cliente_de.values()),
                 "algoritmo": rel.get("algoritmo"), "relacoes_de": rel.get("snapshot_date")}
    return asns, ufs, cobertura


def publicar(base: Path, date_str: str, log, cfg=None) -> dict:
    cfg = cfg or carregar()
    rel = read_json_gz(published_path(base, date_str, "as_relationships.json.gz")) if published_path(base, date_str, "as_relationships.json.gz").exists() else None
    if not rel:
        log.info("as_relationships.json.gz ausente: transito não gerado")
        return {}
    from products.as_relationships import build as rb

    reg_p = normalized_path(base, date_str, "summary") / "registro_br.json.gz"
    reg = read_json_gz(reg_p) if reg_p.exists() else {"asns": []}
    cnpj = {int(a["asn"]): str(a["cnpj"])[:8] for a in reg.get("asns", []) if a.get("cnpj") and len(str(a["cnpj"])) >= 8}
    irmaos = restricoes.grupos_de_irmaos(cnpj, rb._organizacoes(base, date_str))
    nomes_arq = rb._achar(base, date_str, "summary", "asn_names.json.gz")
    nomes = {int(k): v for k, v in (read_json_gz(nomes_arq) if nomes_arq else {}).items()}
    asns, ufs, cobertura = calcular(rel, _docs_br(base, date_str), irmaos, nomes, cfg)
    destino = published_path(base, date_str) / "transito"
    destino.mkdir(parents=True, exist_ok=True)
    cab = {"snapshot_date": date_str, "generated_at": now_iso(), "limites": LIMITES, "cobertura": cobertura,
           "fonte": {"nome": "Arandurapé: relações entre ASNs inferidas (ARC v2) sobre rotas dos coletores RouteViews/RIPE RIS e dos route servers do IX.br, ASPA e organização do CAIDA",
                     "coletores_coletados_em": (rel.get("entradas") or {}).get("coletores_coletados_em")}}
    write_json_gz(destino / "asns.json.gz", {**cab, "asns": asns})
    write_json_gz(destino / "ufs.json.gz", {**cab, "ufs": ufs})
    log.info("transito published", asns_com_cone=len(asns), ufs=len(ufs))
    return {"asns_com_cone": len(asns), "ufs": len(ufs)}


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Trânsito por UF e cone de clientes (a partir do ARC v2)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true")
    a = p.parse_args(argv)
    log = configure_logging()
    base = data_dir()
    if not a.force and (published_path(base, a.date) / "transito" / "ufs.json.gz").exists():
        log.info("already exists, skipping", date=a.date)
        return 0
    return 0 if publicar(base, a.date, log) else 1


if __name__ == "__main__":
    sys.exit(main())
