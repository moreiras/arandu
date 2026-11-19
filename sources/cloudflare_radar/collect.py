# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cloudflare Radar: IPv6 por ASN em rodízio, tráfego e velocidade dos ASNs de topo, eventos de BGP e quedas do Brasil.

Token só do ambiente (`CLOUDFLARE_API_TOKEN`, conta com `Radar → Read`); nunca em log, argumento ou arquivo. Uma requisição por vez, pausa entre elas,
`User-Agent` identificado e respeito ao `429`/`Retry-After`. A cota da API é de 1.200 requisições por 5 minutos.

Rodízio: a lista de ASNs do Brasil (`entities/asns`, ~9,2 mil, 100 por página) é renovada a cada `LISTA_MAX_IDADE_DIAS`; em cada execução consulta-se o IPv6
de até `RADAR_ASNS_POR_EXECUCAO` ASNs (padrão 1.400), os sem leitura primeiro e depois os de leitura mais antiga. Cada leitura leva a sua data, então um
ASN nunca aparece como "atual" sem ser. Resposta sem dado fica registrada (`v6: null`) e é tentada de novo só quando chega a vez dela.
Lido de novo a cada execução (barato): topo de tráfego, topo de velocidade, vazamentos e sequestros de BGP do país nos últimos 28 dias e a consulta de quedas.

Normalizado: data/normalized/{date}/summary/cloudflare_radar.json.gz (carrega o estado da execução anterior para continuar o rodízio).

Uso:
    python -m sources.cloudflare_radar.collect --date 2026-11-09 [--asns 1400]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date as _date
from pathlib import Path
from typing import Callable, Optional

import httpx

from core import radar, rodizio
from core.common import configure_logging, data_dir, normalized_path, now_iso, today_str, write_json_gz
from core.site import USER_AGENT

HEADERS_BASE = {"User-Agent": USER_AGENT}
ESPERA_S = 0.5
ASNS_POR_EXECUCAO = 1400
LISTA_MAX_IDADE_DIAS = 7


class TokenInvalido(RuntimeError):
    """401/403 da API: token ausente, sem a permissão de Radar ou revogado. Não adianta continuar."""


class Contador:
    def __init__(self) -> None:
        self.requisicoes = 0
        self.erros = 0


def _get(client: httpx.Client, caminho: str, params: dict, cont: Contador, espera_s: float, corpo: bool = False) -> Optional[dict]:
    """GET com até 3 tentativas; devolve `result` (ou o corpo inteiro, com `result_info`, se `corpo`) ou None se a API respondeu 4xx de validação. 401/403 levantam `TokenInvalido`."""
    for tentativa in range(1, 4):
        if espera_s:
            time.sleep(espera_s)
        cont.requisicoes += 1
        try:
            r = client.get(radar.BASE_URL + caminho, params=params)
        except httpx.HTTPError:
            if tentativa == 3:
                cont.erros += 1
                raise
            time.sleep(5 * tentativa)
            continue
        if r.status_code in (401, 403):
            raise TokenInvalido(f"{caminho}: HTTP {r.status_code} (token sem permissão de Radar ou inválido)")
        if r.status_code == 429 or r.status_code >= 500:
            if tentativa == 3:
                cont.erros += 1
                r.raise_for_status()
            time.sleep(min(float(r.headers.get("Retry-After", 5) or 5), 120) if r.status_code == 429 else 5 * tentativa)
            continue
        if r.status_code >= 400:
            cont.erros += 1
            return None
        dados = r.json() or {}
        return dados if corpo else dados.get("result")
    return None


def _lista_asns(client: httpx.Client, cont: Contador, espera_s: float, limite_paginas: int = 200) -> list[int]:
    asns: list[int] = []
    for pagina in range(limite_paginas):
        res = _get(client, "/radar/entities/asns", {"location": radar.PAIS, "limit": radar.MAX_ENTIDADES, "offset": pagina * radar.MAX_ENTIDADES}, cont, espera_s)
        lote = [radar.asn_inteiro(a.get("asn")) for a in ((res or {}).get("asns") or [])]
        asns += [a for a in lote if a]
        if len(lote) < radar.MAX_ENTIDADES:
            break
    return sorted(set(asns))


def _ipv6(client: httpx.Client, asn: int, cont: Contador, espera_s: float) -> Optional[float]:
    res = _get(client, "/radar/http/summary/ip_version", {"asn": asn, "dateRange": radar.JANELA_IPV6, "botClass": radar.BOT_CLASS}, cont, espera_s)
    return radar.numero(((res or {}).get("summary_0") or {}).get("IPv6"))


def _topo_trafego(client: httpx.Client, cont: Contador, espera_s: float) -> list[dict]:
    res = _get(client, "/radar/http/top/ases", {"location": radar.PAIS, "limit": radar.MAX_TOPO, "dateRange": radar.JANELA_IPV6, "botClass": radar.BOT_CLASS}, cont, espera_s)
    return [{"asn": radar.asn_inteiro(x.get("clientASN")), "pct": radar.numero(x.get("value"))} for x in ((res or {}).get("top_0") or []) if radar.asn_inteiro(x.get("clientASN"))]


def _topo_velocidade(client: httpx.Client, cont: Contador, espera_s: float) -> list[dict]:
    res = _get(client, "/radar/quality/speed/top/ases", {"location": radar.PAIS, "limit": radar.MAX_TOPO, "dateRange": "90d"}, cont, espera_s)
    out = []
    for x in ((res or {}).get("top_0") or []):
        asn = radar.asn_inteiro(x.get("clientASN"))
        if asn:
            out.append({"asn": asn, "download_mbps": radar.numero(x.get("bandwidthDownload")), "upload_mbps": radar.numero(x.get("bandwidthUpload")),
                        "latencia_ociosa_ms": radar.numero(x.get("latencyIdle")), "latencia_carregada_ms": radar.numero(x.get("latencyLoaded")),
                        "jitter_ocioso_ms": radar.numero(x.get("jitterIdle")), "testes": x.get("numTests")})
    return out


def _eventos_bgp(client: httpx.Client, tipo: str, cont: Contador, espera_s: float, limite_paginas: int = 60) -> dict:
    """Vazamentos (`leaks`) ou sequestros (`hijacks`) com algum ASN do Brasil, 28 dias, paginados de 50; guarda só o necessário para atribuir papéis."""
    eventos: list[dict] = []
    total = None
    for pagina in range(1, limite_paginas + 1):
        params = {"involvedCountry": radar.PAIS, "dateRange": f"{radar.JANELA_BGP_DIAS}d", "perPage": radar.POR_PAGINA_BGP, "page": pagina}
        corpo = _get(client, f"/radar/bgp/{tipo}/events", params, cont, espera_s, corpo=True)
        if not corpo or not corpo.get("result"):
            break
        lote = corpo["result"].get("events") or []
        for e in lote:
            if tipo == "leaks":
                eventos.append({"id": e.get("id"), "em": e.get("detected_ts"), "vazador": radar.asn_inteiro(e.get("leak_asn")),
                                "caminho": [a for a in (radar.asn_inteiro(x) for x in (e.get("leak_seg") or [])) if a],
                                "prefixos": e.get("prefix_count"), "encerrado": bool(e.get("finished"))})
            else:
                eventos.append({"id": e.get("id"), "inicio": e.get("min_hijack_ts"), "fim": e.get("max_hijack_ts"), "sequestrador": radar.asn_inteiro(e.get("hijacker_asn")),
                                "vitimas": [a for a in (radar.asn_inteiro(x) for x in (e.get("victim_asns") or [])) if a], "prefixos": len(e.get("prefixes") or []),
                                "em_andamento": bool(e.get("on_going_count")), "rpki_invalido": any(t.get("name") == "rpki_new_origin_invalid" and (t.get("score") or 0) > 0 for t in (e.get("tags") or []))})
        total = (corpo.get("result_info") or {}).get("total_count", total)
        if len(lote) < radar.POR_PAGINA_BGP:
            break
    return {"janela_dias": radar.JANELA_BGP_DIAS, "total_informado": total, "lidos": len(eventos), "eventos": eventos}


def _quedas(client: httpx.Client, cont: Contador, espera_s: float) -> dict:
    anom = _get(client, "/radar/traffic_anomalies", {"location": radar.PAIS, "dateRange": radar.JANELA_QUEDAS, "limit": 50}, cont, espera_s)
    anot = _get(client, "/radar/annotations/outages", {"location": radar.PAIS, "dateRange": radar.JANELA_QUEDAS, "limit": 50}, cont, espera_s)
    return {"janela": radar.JANELA_QUEDAS, "anomalias": len((anom or {}).get("trafficAnomalies") or []), "anotacoes": len((anot or {}).get("annotations") or []),
            "consultado": anom is not None and anot is not None}


def escolher_rodizio(asns: list[int], ipv6: dict, limite: int) -> list[int]:
    """Sem leitura primeiro, depois a mais antiga; empate pela ordem do ASN (estável entre execuções)."""
    return rodizio.escolher_por_idade(asns, lambda a: (ipv6.get(str(a)) or {}).get("em"), limite)


def _anterior(base: Path, date_str: str) -> dict:
    """Estado da execução anterior: o normalizado mais recente com data anterior a `date_str` (ou o da própria data, ao repetir com --force)."""
    return rodizio.anterior_normalizado(base, date_str, "cloudflare_radar.json.gz", incluir_data=True)


def run(date_str: str, base: Path, log, token: Optional[str] = None, asns_por_execucao: Optional[int] = None, espera_s: float = ESPERA_S,
        client: Optional[httpx.Client] = None) -> dict:
    token = token if token is not None else os.environ.get("CLOUDFLARE_API_TOKEN", "")
    if not token:
        raise TokenInvalido("CLOUDFLARE_API_TOKEN ausente do ambiente")
    t0 = time.time()
    limite = asns_por_execucao or int(os.environ.get("RADAR_ASNS_POR_EXECUCAO") or ASNS_POR_EXECUCAO)
    antes = _anterior(base, date_str)
    cont = Contador()
    proprio = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(60, read=120), headers={**HEADERS_BASE, "Authorization": f"Bearer {token}"})
    try:
        lista_em = antes.get("lista_asns_em")
        velha = not lista_em or (_date.fromisoformat(date_str) - _date.fromisoformat(lista_em)).days >= LISTA_MAX_IDADE_DIAS
        asns = antes.get("asns_br") or []
        if velha or not asns:
            novos = _lista_asns(client, cont, espera_s)
            if novos:
                asns, lista_em = novos, date_str
            elif not asns:
                raise RuntimeError("cloudflare_radar: a lista de ASNs do Brasil veio vazia")
        ipv6 = {k: v for k, v in (antes.get("ipv6") or {}).items() if int(k) in set(asns)}
        vez = escolher_rodizio(asns, ipv6, limite)
        lidos = 0
        for a in vez:
            ipv6[str(a)] = {"v6": _ipv6(client, a, cont, espera_s), "em": date_str}
            lidos += 1
        topo = _topo_trafego(client, cont, espera_s)
        vel = _topo_velocidade(client, cont, espera_s)
        vaz = _eventos_bgp(client, "leaks", cont, espera_s)
        seq = _eventos_bgp(client, "hijacks", cont, espera_s)
        quedas = _quedas(client, cont, espera_s)
    finally:
        if proprio:
            client.close()
    com_dado = sum(1 for v in ipv6.values() if v.get("v6") is not None)
    medicao = {"asns_lidos": lidos, "limite": limite, "requisicoes": cont.requisicoes, "erros": cont.erros, "segundos": round(time.time() - t0, 1),
               "asns_na_lista": len(asns), "asns_com_leitura": len(ipv6), "asns_com_dado_ipv6": com_dado,
               "dias_ate_cobrir": -(-len(asns) // limite) if limite else None}
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    write_json_gz(destino / "cloudflare_radar.json.gz", {
        "snapshot_date": date_str, "fetched_at": now_iso(), "fonte": radar.BASE_URL + "/radar/", "licenca": radar.LICENCA, "licenca_url": radar.LICENCA_URL,
        "atribuicao": radar.ATRIBUICAO, "janela_ipv6": radar.JANELA_IPV6, "bot_class": radar.BOT_CLASS, "lista_asns_em": lista_em, "asns_br": asns,
        "ipv6": dict(sorted(ipv6.items(), key=lambda kv: int(kv[0]))), "trafego": {"janela": radar.JANELA_IPV6, "em": date_str, "topo": topo},
        "velocidade": {"janela": "90d", "em": date_str, "topo": vel}, "bgp": {"vazamentos": vaz, "sequestros": seq, "em": date_str},
        "quedas": {**quedas, "em": date_str}, "ultima_execucao": medicao})
    log.info("cloudflare_radar written", **medicao)
    return medicao


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Cloudflare Radar: IPv6 por ASN (rodízio), topo de tráfego e velocidade, BGP e quedas do Brasil")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre incremental")
    p.add_argument("--asns", type=int, default=None, help="ASNs a consultar nesta execução (padrão: RADAR_ASNS_POR_EXECUCAO ou 1400)")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        print(run(a.date, data_dir(), log, asns_por_execucao=a.asns))
    except TokenInvalido as exc:
        log.error("cloudflare_radar: token", erro=str(exc))
        return 1
    except Exception:
        log.exception("falha na coleta de cloudflare_radar")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
