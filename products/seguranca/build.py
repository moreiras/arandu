# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Segurança de roteamento por ASN, parte A. Saída: `published/{date}/seguranca/asns.json.gz`.

Reúne, por ASN do Brasil, sinais de quatro fontes e do que o Arandurapé já publica:
  * `rov`: % das medições do APNIC em que a rede não alcança rota RPKI-inválida (`apnic_irov`; alto = valida); medição por amostragem, com `amostras`;
  * `dnssec`: % de clientes que validam DNSSEC, total e parcial (`apnic_dnssec`); medição por amostragem;
  * `asrank`: rank, grau e cone do CAIDA AS Rank (`caida_asrank`); inferência do CAIDA, rotulada como estimada;
  * `bogons`: prefixos que o ASN origina dentro de espaço reservado (IANA) ou não alocado (Team Cymru, na data da lista) e ASN reservado.
Agregados por UF e por faixa de porte (usuários estimados do APNIC; a faixa de acessos declarados ao SICI do CNPJ fica como informação extra em `faixa_acessos_sici`): só ASNs com amostras suficientes entram nas contagens de ROV e DNSSEC, em faixas neutras.

Nada aqui é veredito: são medições e fatos de terceiros, com fonte e data (política editorial). Sem o `spamhaus_drop`.
"""
from __future__ import annotations

import bisect
import ipaddress
import json
import statistics
from pathlib import Path
from typing import Iterable, Optional

from core import compose
from core.avisos_agregado import avisos, peso_top1
from core.common import normalized_path, now_iso, published_path
from core.jsonio import carregar_json_gz, gravar_json_gz

MIN_AMOSTRAS = 100                       # abaixo disso o percentual do APNIC é instável e não entra nos agregados
FAIXAS_ROV = ((10.0, "ate_10"), (90.0, "de_10_a_90"))      # percentual até 10, de 10 a 90 e acima de 90 (valida)
MAX_PREFIXOS_BOGON = 20                  # lista por ASN limitada; o total vai em `n_prefixos_bogon`
FAIXAS_PORTE = ((0, "sem_usuarios"), (1000, "ate_1000"), (10000, "de_1000_a_10000"), (100000, "de_10000_a_100000"), (1000000, "de_100000_a_1000000"))      # porte = usuários estimados do APNIC
FAIXAS_ACESSOS_SICI = ((0, "sem_acessos"), (1000, "ate_1000"), (10000, "de_1000_a_10000"), (100000, "de_10000_a_100000"))                      # informação extra: acessos fixos declarados ao SICI


class Intervalos:
    """Conjunto de blocos CIDR de uma família, fundidos em intervalos: `contem(prefixo)` diz se o prefixo está inteiro dentro de algum bloco."""

    def __init__(self, blocos: Iterable[str]):
        faixas = sorted((int(n.network_address), int(n.broadcast_address)) for n in (ipaddress.ip_network(b, strict=False) for b in blocos))
        fund: list[list[int]] = []
        for ini, fim in faixas:
            if fund and ini <= fund[-1][1] + 1:
                fund[-1][1] = max(fund[-1][1], fim)
            else:
                fund.append([ini, fim])
        self._ini = [f[0] for f in fund]
        self._fim = [f[1] for f in fund]

    def contem(self, prefixo: str) -> bool:
        rede = ipaddress.ip_network(prefixo, strict=False)
        ini, fim = int(rede.network_address), int(rede.broadcast_address)
        i = bisect.bisect_right(self._ini, ini) - 1
        return i >= 0 and fim <= self._fim[i]


def montar_bogons(bogons: dict) -> dict:
    """{'iana': {4: Intervalos, 6: Intervalos}, 'cymru': {...}} a partir de bogons.json.gz."""
    def fam(blocos, v):
        return Intervalos(b for b in blocos if (":" in b) == (v == 6))
    iana = [b["bloco"] for b in bogons["iana"]["v4"] + bogons["iana"]["v6"]]
    cymru = bogons["cymru"]["v4"] + bogons["cymru"]["v6"]
    return {"iana": {4: fam(iana, 4), 6: fam(iana, 6)}, "cymru": {4: fam(cymru, 4), 6: fam(cymru, 6)}}


def prefixos_em_bogon(prefixos: Iterable[str], listas: dict) -> list[dict]:
    out = []
    for p in prefixos:
        v = 6 if ":" in p else 4
        for origem in ("iana", "cymru"):
            if listas[origem][v].contem(p):
                out.append({"prefixo": p, "lista": origem})
                break
    return out


def asn_reservado(asn: int, faixas: list[dict]) -> Optional[str]:
    return next((f["motivo"] for f in faixas if f["inicio"] <= asn <= f["fim"]), None)


def faixa_porte(usuarios: Optional[int]) -> str:
    """Porte do ASN pelos usuários estimados do APNIC (estimativa de usuários de Internet, não assinantes). Sem estimativa: `sem_usuarios`."""
    if not usuarios:
        return FAIXAS_PORTE[0][1]
    for limite, nome in FAIXAS_PORTE[1:]:
        if usuarios <= limite:
            return nome
    return "acima_de_1000000"


def faixa_acessos_sici(acessos: Optional[int]) -> str:
    """Faixa de acessos fixos declarados ao SICI pelo CNPJ do ASN (informação extra; um CNPJ pode ter vários ASNs)."""
    if not acessos:
        return FAIXAS_ACESSOS_SICI[0][1]
    for limite, nome in FAIXAS_ACESSOS_SICI[1:]:
        if acessos <= limite:
            return nome
    return "acima_de_100000"


def _faixa_pct(v: float) -> str:
    return "ate_10" if v <= FAIXAS_ROV[0][0] else "de_10_a_90" if v <= FAIXAS_ROV[1][0] else "acima_de_90"


def _agregar(valores: list[tuple[float, int]]) -> dict:
    """`valores`: [(percentual, amostras)] dos ASNs com amostras suficientes."""
    if not valores:
        return {"asns": 0, "n_asns_com_dado": 0, "peso_top1": None, "avisos": avisos(0)}
    pct = [v for v, _ in valores]
    pesos = sum(a for _, a in valores)
    faixas = {"ate_10": 0, "de_10_a_90": 0, "acima_de_90": 0}
    for v in pct:
        faixas[_faixa_pct(v)] += 1
    peso = peso_top1(a for _, a in valores)           # o peso da média ponderada são as amostras do APNIC
    return {"asns": len(pct), "n_asns_com_dado": len(pct), "peso_top1": peso, "avisos": avisos(len(pct), peso), "mediana_pct": round(statistics.median(pct), 2), "media_ponderada_pct": round(sum(v * a for v, a in valores) / pesos, 2),
            "faixas": faixas}


def agregar(asns: dict[str, dict], grupo: dict[str, str]) -> dict[str, dict]:
    """Agregado de ROV e DNSSEC por grupo (UF ou faixa de porte); `grupo`: {asn: nome do grupo}."""
    por: dict[str, dict[str, list]] = {}
    for a, s in asns.items():
        g = grupo.get(a)
        if g is None:
            continue
        e = por.setdefault(g, {"asns": 0, "rov": [], "dnssec": []})
        e["asns"] += 1
        if s.get("rov") and s["rov"]["amostras"] >= MIN_AMOSTRAS:
            e["rov"].append((s["rov"]["validates_pct"], s["rov"]["amostras"]))
        if s.get("dnssec") and s["dnssec"]["amostras"] >= MIN_AMOSTRAS:
            e["dnssec"].append((s["dnssec"]["validates_pct"], s["dnssec"]["amostras"]))
    return {g: {"asns": e["asns"], "rov": _agregar(e["rov"]), "dnssec": _agregar(e["dnssec"]),
                "asns_com_prefixo_bogon": sum(1 for a, s in asns.items() if grupo.get(a) == g and s.get("n_prefixos_bogon"))}
            for g, e in sorted(por.items())}


def calcular(irov: Optional[dict], dnssec: Optional[dict], asrank: Optional[dict], bogons: Optional[dict], docs: dict[int, dict], acessos_por_cnpj: dict[str, int]) -> dict:
    """`docs`: {asn: {uf, cnpj, prefixos}} dos ASNs do Brasil. Devolve {asns, por_uf, por_faixa_porte, brasil}."""
    listas = montar_bogons(bogons) if bogons else None
    universo = set(docs)
    for fonte in (irov, dnssec, asrank):
        universo |= {int(a) for a in (fonte or {}).get("asns", {})}
    asns: dict[str, dict] = {}
    for a in sorted(universo):
        s: dict = {}
        if irov and str(a) in irov["asns"]:
            s["rov"] = dict(irov["asns"][str(a)])
        if dnssec and str(a) in dnssec["asns"]:
            s["dnssec"] = dict(dnssec["asns"][str(a)])
        if asrank and str(a) in asrank["asns"]:
            s["asrank"] = {k: v for k, v in asrank["asns"][str(a)].items() if k != "clique"}      # cliqueMember da API vem true para ASNs de rank baixo: não confiável
        d = docs.get(a)
        if listas and d is not None:
            achados = prefixos_em_bogon(d.get("prefixos") or [], listas)
            if achados:
                s["prefixos_em_bogon"] = achados[:MAX_PREFIXOS_BOGON]
                s["n_prefixos_bogon"] = len(achados)
        if bogons:
            motivo = asn_reservado(a, bogons["iana"]["asns"])
            if motivo:
                s["asn_reservado"] = motivo
        if d is not None:
            if d.get("uf"):
                s["uf"] = d["uf"]
            s["faixa_porte"] = faixa_porte(d.get("usuarios"))
            s["faixa_acessos_sici"] = faixa_acessos_sici(acessos_por_cnpj.get(d.get("cnpj") or ""))
        if s:
            asns[str(a)] = s
    uf = {str(a): d["uf"] for a, d in docs.items() if d.get("uf")}
    porte = {str(a): s["faixa_porte"] for a, s in ((str(a), asns.get(str(a), {})) for a in docs) if "faixa_porte" in s}
    todos = {a: s for a, s in asns.items() if int(a) in docs}
    brasil_g = {a: "BR" for a in todos}
    return {"asns": asns, "por_uf": agregar(todos, uf), "por_faixa_porte": agregar(todos, porte), "brasil": agregar(todos, brasil_g).get("BR", {})}


def _doc_resumido(d: dict) -> dict:
    return {"uf": ((d.get("geo_org") or {}).get("uf") or None), "cnpj": d.get("cnpj") or None, "usuarios": int(d.get("apnic_users") or 0),
            "prefixos": sorted(set((d.get("global_prefixes_v4") or []) + (d.get("global_prefixes_v6") or [])))}      # ordem do documento varia entre fluxos


def _docs_br(base: Path, date_str: str) -> dict[int, dict]:
    """{asn: {uf, cnpj, prefixos}} dos ASNs do Brasil. No fluxo de fragmentos o documento final só existe no fim do build, então lê o fragmento `base`
    (documento completo de ASN, que já traz geo_org e os prefixos); no fluxo antigo lê os documentos publicados."""
    if compose.ativo() and compose.fluxo_novo(base, date_str):
        return {asn: _doc_resumido(d) for asn, d in compose.iterar_documentos(base, date_str, ("base",)) if d.get("is_br")}
    pub = published_path(base, date_str)
    idx = json.loads((pub / "asns" / "index.json").read_text(encoding="utf-8")) if (pub / "asns" / "index.json").exists() else []
    out: dict[int, dict] = {}
    for e in idx:
        p = pub / "asns" / f"{e['asn']}.json"
        if e.get("is_br") and p.exists():
            out[e["asn"]] = _doc_resumido(json.loads(p.read_text(encoding="utf-8")))
    return out


def publicar_seguranca(base: Path, date_str: str, log) -> dict:
    pub = published_path(base, date_str)
    norm = normalized_path(base, date_str, "summary")
    irov, dnssec = carregar_json_gz(norm / "apnic_irov.json.gz"), carregar_json_gz(norm / "apnic_dnssec.json.gz")
    asrank, bogons = carregar_json_gz(norm / "caida_asrank.json.gz"), carregar_json_gz(norm / "bogons.json.gz")
    if not any((irov, dnssec, asrank, bogons)):
        log.info("nenhuma fonte de segurança disponível: seguranca/asns.json.gz não gerado")
        return {}
    docs = _docs_br(base, date_str)
    sici = carregar_json_gz(pub / "sici.json.gz") or {}
    acessos = {c: v.get("acessos", 0) for c, v in (sici.get("cnpjs") or {}).items()}
    r = calcular(irov, dnssec, asrank, bogons, docs, acessos)
    destino = pub / "seguranca"
    destino.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino / "asns.json.gz", {
        "snapshot_date": date_str, "generated_at": now_iso(),
        "fontes": {
            "rov": {"fonte": "APNIC Labs I-RoV (stats.labs.apnic.net/rpki/BR)", "as_of": (irov or {}).get("as_of"), "janela_dias": (irov or {}).get("janela_dias"),
                    "copyright": (irov or {}).get("copyright")},
            "dnssec": {"fonte": "APNIC Labs (stats.labs.apnic.net/dnssec/BR)", "as_of": (dnssec or {}).get("as_of"), "janela_dias": (dnssec or {}).get("janela_dias"),
                       "copyright": (dnssec or {}).get("copyright")},
            "asrank": {"fonte": "CAIDA AS Rank (asrank.caida.org)", "coletado_em": (asrank or {}).get("fetched_at"), "citacao": (asrank or {}).get("copyright")},
            "bogons": {"fonte": "IANA (registros de uso especial) e Team Cymru (fullbogons)", "lista_cymru_em": ((bogons or {}).get("cymru") or {}).get("as_of")},
        },
        "parametros": {"min_amostras": MIN_AMOSTRAS, "faixas_pct": {"ate_10": "0 a 10", "de_10_a_90": "10 a 90", "acima_de_90": "acima de 90"},
                       "faixas_porte": "usuários estimados do APNIC por ASN (sem estimativa: sem_usuarios)", "faixas_acessos_sici": "acessos fixos declarados ao SICI do CNPJ do ASN (informação extra)"},
        "limites": ("ROV e DNSSEC são medições do APNIC por amostragem de usuários e de destinos de teste, não declarações da rede; ASN com poucas amostras fica fora dos "
                    "agregados. O AS Rank é inferência do CAIDA. Bogon = prefixo originado dentro de espaço reservado (IANA) ou ainda não alocado (Team Cymru, na data da lista); "
                    "um bloco recém-alocado pode aparecer como não alocado por horas. Listas de reputação (Spamhaus DROP) ficam de fora por termos de uso (I-006)."),
        **r})
    log.info("seguranca written", asns=len(r["asns"]), ufs=len(r["por_uf"]))
    return {"asns": len(r["asns"]), "ufs": len(r["por_uf"]), "com_bogon": sum(1 for s in r["asns"].values() if s.get("n_prefixos_bogon"))}
