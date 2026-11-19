# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cloudflare Radar: constantes e leitura dos formatos da API v4, compartilhadas pela coleta e pelo produto.

Layout conferido em 2026-11-09 contra a API real (`https://api.cloudflare.com/client/v4/radar/`), com token de conta `Account → Radar → Read`:
  * `entities/asns?location=BR&limit=100&offset=N` → `result.asns[].{asn,name,aka,country,...}` (máximo de 100 por página).
  * `http/summary/ip_version?asn=N&dateRange=28d&botClass=LIKELY_HUMAN` → `result.summary_0.{IPv4,IPv6}` (strings, percentual das requisições HTTP).
  * `http/top/ases?location=BR&limit=300&dateRange=28d` → `result.top_0[].{clientASN,clientASName,value}` (`value` = % das requisições HTTP do Brasil; máximo 300).
  * `quality/speed/top/ases?location=BR&limit=300&dateRange=28d` → `result.top_0[].{clientASN,bandwidthDownload,bandwidthUpload,latencyIdle,latencyLoaded,jitterIdle,numTests}`.
  * `bgp/leaks/events` e `bgp/hijacks/events` (`involvedCountry=BR`, `perPage` ≤ 50, `page`) → `result.events[]` + `result_info.total_count`.
  * `traffic_anomalies` e `annotations/outages` (`location=BR`) → `result.trafficAnomalies[]` e `result.annotations[]`.
"""
from __future__ import annotations

from typing import Optional

BASE_URL = "https://api.cloudflare.com/client/v4"
LICENCA = "CC BY-NC 4.0"
LICENCA_URL = "https://creativecommons.org/licenses/by-nc/4.0/"
ATRIBUICAO = ("Dados: Cloudflare Radar (https://radar.cloudflare.com), licença CC BY-NC 4.0; agregados e atribuídos a ASN pelo Arandurapé "
              "(adaptação). O IPv6 é o percentual das requisições HTTP de pessoas (`botClass=LIKELY_HUMAN`) vistas pela Cloudflare nos últimos 28 dias.")
PAIS = "BR"
JANELA_IPV6 = "28d"
BOT_CLASS = "LIKELY_HUMAN"
JANELA_BGP_DIAS = 28
JANELA_QUEDAS = "52w"
POR_PAGINA_BGP = 50
MAX_TOPO = 300
MAX_ENTIDADES = 100


def numero(valor) -> Optional[float]:
    """A API devolve percentuais como string (`"69.244578"`); vazio ou inválido vira None."""
    try:
        return None if valor is None or valor == "" else float(valor)
    except (TypeError, ValueError):
        return None


def asn_inteiro(valor) -> Optional[int]:
    try:
        n = int(valor)
    except (TypeError, ValueError):
        return None
    return n if 0 < n < 2 ** 32 else None
