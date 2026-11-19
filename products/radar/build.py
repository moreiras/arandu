# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cloudflare Radar por ASN e por UF. Saída: `published/{date}/radar/asns.json.gz`.

Por ASN do Brasil do snapshot: IPv6 (com a data da leitura, pelo rodízio), participação no tráfego e velocidade/latência (só os ASNs das listas de topo) e o papel nos eventos de
BGP dos últimos 28 dias (vazou, no caminho do vazamento, sequestrou, vítima de sequestro). Ausência de dado nunca vira zero: o ASN fora do topo não tem tráfego nem velocidade, e o sem leitura
de IPv6 não tem IPv6. Por UF, só agregado **derivado** dos ASNs (o Radar não tem recorte por UF), com a cobertura declarada. Quedas: só a consulta do país e a data. Sem ranking de ASN.
Dados do Cloudflare Radar, CC BY-NC 4.0: licença e atribuição vão no arquivo.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Optional

from core import radar
from core.common import normalized_path, now_iso, published_path
from core.jsonio import carregar_json_gz, gravar_json_gz
from products.seguranca.build import _docs_br

MIN_TESTES_VELOCIDADE = 30          # velocidade de ASN com menos testes é ruído; o topo do Radar já filtra, mas o mínimo fica explícito

AVISO = ("O IPv6 é o percentual das requisições HTTP de pessoas (não de robôs) que a Cloudflare viu naquele ASN nos últimos 28 dias; mede quem usa a Cloudflare, não a rede inteira. "
         "Tráfego e velocidade só existem para os ASNs de topo do Brasil; ASN fora das listas não tem esses números, e isso não quer dizer zero. "
         "Os eventos de BGP são os que o Radar detectou: não provam intenção nem dano. Os agregados por UF são derivados dos ASNs do mapeamento ASN → UF do projeto.")
LIMITES = ("Rodízio: cada ASN tem a sua data de leitura de IPv6 (até ~7 dias de idade além da janela de 28 dias); ASN sem leitura ainda não foi consultado. Cobertura declarada em `cobertura`. "
           "Velocidade: só os ASNs com testes suficientes na lista do Radar. Quedas: o Radar só anota quedas de escala nacional ou regional ampla; 'sem quedas' é o que a consulta do país devolveu. "
           "UF é agregado derivado, não dado do Radar; ASN multi-UF conta na UF do seu cadastro.")


def _papeis(bgp: dict, br: set[int]) -> dict[int, dict]:
    p: dict[int, dict] = defaultdict(lambda: {"vazou": 0, "no_caminho_de_vazamento": 0, "sequestrou": 0, "vitima_de_sequestro": 0})
    for e in (bgp.get("vazamentos") or {}).get("eventos") or []:
        if e.get("vazador") in br:
            p[e["vazador"]]["vazou"] += 1
        for a in set(e.get("caminho") or []):
            if a in br and a != e.get("vazador"):
                p[a]["no_caminho_de_vazamento"] += 1
    for e in (bgp.get("sequestros") or {}).get("eventos") or []:
        if e.get("sequestrador") in br:
            p[e["sequestrador"]]["sequestrou"] += 1
        for a in set(e.get("vitimas") or []):
            if a in br:
                p[a]["vitima_de_sequestro"] += 1
    return p


def calcular(doc: dict, docs_br: dict[int, dict], minimo_testes: int = MIN_TESTES_VELOCIDADE) -> dict:
    br = set(docs_br)
    trafego = {x["asn"]: x["pct"] for x in (doc.get("trafego") or {}).get("topo") or [] if x.get("asn") in br and x.get("pct") is not None}
    velocidade = {x["asn"]: x for x in (doc.get("velocidade") or {}).get("topo") or [] if x.get("asn") in br and (x.get("testes") or 0) >= minimo_testes}
    papeis = _papeis(doc.get("bgp") or {}, br)
    asns: dict[str, dict] = {}
    for a in sorted(br):
        s: dict = {}
        leitura = (doc.get("ipv6") or {}).get(str(a))
        if leitura and leitura.get("v6") is not None:
            s["ipv6"] = {"pct": round(leitura["v6"], 2), "em": leitura["em"]}
        if a in trafego:
            s["trafego_pct_do_brasil"] = round(trafego[a], 4)
        if a in velocidade:
            v = velocidade[a]
            s["velocidade"] = {k: v[k] for k in ("download_mbps", "upload_mbps", "latencia_ociosa_ms", "latencia_carregada_ms", "jitter_ocioso_ms", "testes") if v.get(k) is not None}
        if a in papeis and any(papeis[a].values()):
            s["bgp"] = {k: n for k, n in papeis[a].items() if n}
        if s:
            asns[str(a)] = s
    lidos = {int(k): v for k, v in (doc.get("ipv6") or {}).items() if int(k) in br}
    datas = sorted(v["em"] for v in lidos.values() if v.get("em"))
    cobertura = {"asns_do_brasil_no_snapshot": len(br), "asns_na_lista_do_radar": len(doc.get("asns_br") or []), "asns_com_leitura_ipv6": len(lidos),
                 "asns_com_dado_ipv6": sum(1 for v in lidos.values() if v.get("v6") is not None), "leitura_mais_antiga": datas[0] if datas else None,
                 "leitura_mais_recente": datas[-1] if datas else None, "asns_no_topo_de_trafego": len(trafego), "asns_com_velocidade": len(velocidade)}
    return {"cobertura": cobertura, "asns": asns, "por_uf": _por_uf(asns, docs_br), "bgp": _resumo_bgp(doc.get("bgp") or {}), "quedas": doc.get("quedas") or {}}


def _resumo_bgp(bgp: dict) -> dict:
    return {"janela_dias": (bgp.get("vazamentos") or {}).get("janela_dias"), "em": bgp.get("em"),
            "vazamentos_com_asn_do_brasil": (bgp.get("vazamentos") or {}).get("total_informado"), "sequestros_com_asn_do_brasil": (bgp.get("sequestros") or {}).get("total_informado"),
            "criterio": "evento com algum ASN do Brasil no caminho (vazamento) ou como sequestrador/vítima (sequestro); por ASN vale o papel, não a contagem do país"}


def _por_uf(asns: dict[str, dict], docs_br: dict[int, dict]) -> dict:
    """Agregado DERIVADO por UF a partir dos ASNs. IPv6 ponderado pelo tráfego só entre ASNs que têm os dois números; a cobertura do ponderado vem junto."""
    ufs: dict[str, dict] = {}
    for a, d in docs_br.items():
        uf = d.get("uf")
        if not uf:
            continue
        u = ufs.setdefault(uf, {"asns": 0, "asns_com_ipv6": 0, "_v6": [], "_pond": [], "bgp": {"vazou": 0, "no_caminho_de_vazamento": 0, "sequestrou": 0, "vitima_de_sequestro": 0}})
        u["asns"] += 1
        s = asns.get(str(a)) or {}
        if "ipv6" in s:
            u["asns_com_ipv6"] += 1
            u["_v6"].append(s["ipv6"]["pct"])
            if "trafego_pct_do_brasil" in s:
                u["_pond"].append((s["ipv6"]["pct"], s["trafego_pct_do_brasil"]))
        for k, n in (s.get("bgp") or {}).items():
            u["bgp"][k] += n
    out = {}
    for uf in sorted(ufs):
        u = ufs[uf]
        peso = sum(w for _, w in u["_pond"])
        out[uf] = {"asns": u["asns"], "asns_com_ipv6": u["asns_com_ipv6"], "ipv6_mediana_pct": round(median(u["_v6"]), 2) if u["_v6"] else None,
                   "ipv6_ponderado_pelo_trafego_pct": round(sum(v * w for v, w in u["_pond"]) / peso, 2) if peso else None, "asns_no_ponderado": len(u["_pond"]), "bgp": u["bgp"], "derivado": True}
    return out


def publicar_radar(base: Path, date_str: str, log) -> dict:
    doc = carregar_json_gz(normalized_path(base, date_str, "summary") / "cloudflare_radar.json.gz")
    if not doc:
        log.info("cloudflare_radar.json.gz ausente: radar não gerado")
        return {}
    r = calcular(doc, _docs_br(base, date_str))
    destino = published_path(base, date_str) / "radar"
    destino.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino / "asns.json.gz", {
        "snapshot_date": date_str, "generated_at": now_iso(), "coletado_em": doc.get("fetched_at"),
        "fonte": {"nome": "Cloudflare Radar", "url": "https://radar.cloudflare.com", "api": doc.get("fonte"), "licenca": doc.get("licenca") or radar.LICENCA,
                  "licenca_url": doc.get("licenca_url") or radar.LICENCA_URL, "atribuicao": doc.get("atribuicao") or radar.ATRIBUICAO},
        "licenca": doc.get("licenca") or radar.LICENCA, "aviso": AVISO, "limites": LIMITES, "janela_ipv6": doc.get("janela_ipv6"), **r})
    log.info("radar published", asns=len(r["asns"]), ufs=len(r["por_uf"]))
    return {"asns": len(r["asns"]), "ufs": len(r["por_uf"])}
