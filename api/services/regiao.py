# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Região: agrega os ASNs de um conjunto de municípios — participação em PTTs, provedores de trânsito e ASNs que carregam o tráfego até os PTTs.

Funções puras sobre `territorio/regiao.json.gz` (produto `regiao_municipios`). O conjunto é a união dos ASNs dos municípios pedidos; cada ASN conta uma vez.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Optional

from core.prontidao_agregado import agregar as agregar_prontidao

MAX_MUNICIPIOS = 50
TOPO = 20
MAX_PROVEDORES = 300
VINCULOS = {"s": "sici", "h": "sede", "g": "geo"}
NIVEIS = ("confirmado", "provavel", "possivel")


class RegiaoErro(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


def ibges_da_consulta(texto: Optional[str]) -> list[str]:
    ibges = list(dict.fromkeys(p.strip() for p in (texto or "").split(",") if p.strip()))
    if not ibges:
        raise RegiaoErro(400, "Informe ibges=código1,código2,… (até %d municípios)." % MAX_MUNICIPIOS)
    if len(ibges) > MAX_MUNICIPIOS:
        raise RegiaoErro(400, "No máximo %d municípios por consulta." % MAX_MUNICIPIOS)
    if any(not i.isdigit() or len(i) != 7 for i in ibges):
        raise RegiaoErro(400, "Os códigos IBGE de município têm 7 dígitos.")
    return ibges


def _pct(parte: int, total: int) -> Optional[float]:
    return round(100 * parte / total, 1) if total else None


def membros(doc: dict, ibges: list[str]) -> dict[str, dict]:
    """ASN → vínculos e números, somando os municípios pedidos."""
    por: dict[str, dict] = {}
    for ibge in ibges:
        m = (doc.get("municipios") or {}).get(ibge)
        if not m:
            continue
        for asn, (fixo, movel) in (m.get("s") or {}).items():
            e = por.setdefault(asn, {"vinculos": set(), "fixo": 0, "movel": 0, "prefixos_geo": 0})
            e["vinculos"].add("sici"); e["fixo"] += fixo; e["movel"] += movel
        for asn in m.get("h") or []:
            por.setdefault(str(asn), {"vinculos": set(), "fixo": 0, "movel": 0, "prefixos_geo": 0})["vinculos"].add("sede")
        for asn, n in (m.get("g") or {}).items():
            e = por.setdefault(asn, {"vinculos": set(), "fixo": 0, "movel": 0, "prefixos_geo": 0})
            e["vinculos"].add("geo"); e["prefixos_geo"] += n
    return por


def _nome(doc: dict, asn) -> str:
    return (doc["asns"].get(str(asn)) or {}).get("n") or ""


def agregar(doc: dict, ibges: list[str], prontidao: Optional[dict] = None) -> dict:
    asns = doc["asns"]
    por = membros(doc, ibges)
    total = len(por)
    # participação nos PTTs
    ptts: dict[str, dict] = defaultdict(lambda: {"direto": 0, "indireto": 0})
    com_direto = so_indireto = 0
    for asn in por:
        t = asns.get(asn) or {}
        d, o = set(t.get("d") or []), set(t.get("o") or [])
        if d:
            com_direto += 1
        elif o:
            so_indireto += 1
        for c in d:
            ptts[c]["direto"] += 1
        for c in o - d:
            ptts[c]["indireto"] += 1
    lista_ptts = sorted(({"codigo": c, **v, "total": v["direto"] + v["indireto"], "pct_direto": _pct(v["direto"], total), "pct_total": _pct(v["direto"] + v["indireto"], total)} for c, v in ptts.items()),
                        key=lambda x: (-x["total"], -x["direto"], x["codigo"]))
    # trânsito: provedores (ARC) dos ASNs do conjunto
    trans: dict[str, Counter] = defaultdict(Counter)
    for asn in por:
        for p, _prob, nivel in (asns.get(asn) or {}).get("p") or []:
            trans[str(p)][NIVEIS[nivel]] += 1
    transito = []
    for p, c in trans.items():
        n = sum(c.values())
        transito.append({"asn": int(p), "nome": _nome(doc, p), "asns": n, "pct": _pct(n, total), "niveis": {k: c.get(k, 0) for k in NIVEIS},
                         "na_regiao": p in por, "ptts_diretos": (asns.get(p) or {}).get("d") or []})
    transito.sort(key=lambda x: (-(x["niveis"]["confirmado"] + x["niveis"]["provavel"]), -x["asns"], x["asn"]))
    # carregadores: vizinhos observados nos caminhos dos PTTs, que estão eles mesmos num PTT
    carreg: dict[str, int] = Counter()
    sem_carregador = 0
    for asn, e in por.items():
        t = asns.get(asn) or {}
        if t.get("d") or not t.get("o"):
            continue
        cs = [c for c in t.get("c") or [] if (asns.get(str(c)) or {}).get("d")]
        if not cs:
            sem_carregador += 1
        for c in cs:
            carreg[str(c)] += 1
    indiretos = so_indireto
    carregadores = sorted(({"asn": int(c), "nome": _nome(doc, c), "asns": n, "pct": _pct(n, indiretos), "na_regiao": c in por, "ptts_diretos": (asns.get(c) or {}).get("d") or []}
                           for c, n in carreg.items()), key=lambda x: (-x["asns"], x["asn"]))
    # a lista de provedores
    provedores = sorted(({"asn": int(a), "nome": _nome(doc, a), "vinculos": sorted(e["vinculos"], key=("sici", "sede", "geo").index), "acessos_fixo": e["fixo"], "acessos_movel": e["movel"],
                          "prefixos_geo": e["prefixos_geo"], "ptts_diretos": (asns.get(a) or {}).get("d") or [],
                          "ptts_indiretos": sorted(set((asns.get(a) or {}).get("o") or []) - set((asns.get(a) or {}).get("d") or []))} for a, e in por.items()),
                        key=lambda x: (-(x["acessos_fixo"] + x["acessos_movel"]), -len(x["vinculos"]), -x["prefixos_geo"], x["asn"]))
    vinc = Counter(v for e in por.values() for v in e["vinculos"])
    return {
        "prontidao": _prontidao(prontidao, por),
        "snapshot_date": doc["snapshot_date"], "natureza": doc.get("natureza", "inferido"), "limites": doc.get("limites"), "fontes": doc.get("fontes"),
        "ptts_nomes": doc.get("ptts_nomes") or {}, "ibges": ibges, "municipios_com_dados": sum(1 for i in ibges if i in (doc.get("municipios") or {})),
        "asns": {"total": total, "por_vinculo": {k: vinc.get(k, 0) for k in ("sici", "sede", "geo")}},
        "participacao_ptts": {"com_ptt_direto": com_direto, "so_indireto": so_indireto, "sem_ptt": total - com_direto - so_indireto,
                              "pct_direto": _pct(com_direto, total), "pct_indireto": _pct(so_indireto, total), "pct_sem_ptt": _pct(total - com_direto - so_indireto, total), "ptts": lista_ptts},
        "transito": transito[:TOPO], "transito_total": len(transito),
        "carregadores": carregadores[:TOPO], "carregadores_total": len(carregadores), "indiretos_sem_carregador": sem_carregador,
        "provedores": provedores[:MAX_PROVEDORES], "provedores_total": total,
    }


def _prontidao(pdoc: Optional[dict], por: dict) -> Optional[dict]:
    """Prontidão em segurança de roteamento dos ASNs do conjunto: o mesmo agregado de UF e do Brasil, sobre os ASNs da região que têm índice. Vale com qualquer número de ASNs,
    inclusive 1; por isso a resposta diz quantos ASNs sustentam cada número. DNSSEC e IPv6 não existem por ASN no dataset e ficam de fora."""
    if not pdoc:
        return None
    ids = {a: pdoc["asns"][a] for a in por if a in pdoc["asns"]}
    if not ids:
        return {"agregado": None, "asns_no_indice": 0, "brasil": pdoc["brasil"], "regras": pdoc["regras"], "limites": pdoc["limites"], "fontes": pdoc["fontes"]}
    return {"agregado": agregar_prontidao(ids, {a: "R" for a in ids})["R"], "asns_no_indice": len(ids), "brasil": pdoc["brasil"], "regras": pdoc["regras"],
            "limites": pdoc["limites"], "fontes": pdoc["fontes"]}
