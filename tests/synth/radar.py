# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cloudflare Radar no dataset sintético.

Os quatro primeiros ASNs do Brasil: o 1º tem IPv6, tráfego, velocidade e papéis de BGP (vazou e é vítima de sequestro); o 2º tem IPv6 zero (dado, não ausência) e sequestrou; o 3º foi lido e o Radar
não devolveu dado (`v6` nulo: ausência, não zero); o 4º tem velocidade com poucos testes (abaixo do mínimo, não publicada). Os demais ainda não foram lidos pelo rodízio. Um ASN estrangeiro
(64999) está nas listas e não entra no produto."""
from __future__ import annotations

from tests.synth.world import World


def cloudflare_radar(world: World, d: str) -> dict:
    br = sorted(a for a, x in world.ases.items() if x.is_br)
    a1, a2, a3, a4 = br[:4]
    return {"snapshot_date": d, "fetched_at": f"{d}T00:00:00+00:00", "fonte": "https://api.cloudflare.com/client/v4/radar/", "licenca": "CC BY-NC 4.0",
            "licenca_url": "https://creativecommons.org/licenses/by-nc/4.0/", "atribuicao": "sintético (Cloudflare Radar, CC BY-NC 4.0)", "janela_ipv6": "28d", "bot_class": "LIKELY_HUMAN",
            "lista_asns_em": d, "asns_br": sorted(br + [64999]),
            "ipv6": {str(a1): {"v6": 55.5, "em": d}, str(a2): {"v6": 0.0, "em": d}, str(a3): {"v6": None, "em": d}, "64999": {"v6": 10.0, "em": d}},
            "trafego": {"janela": "28d", "em": d, "topo": [{"asn": a1, "pct": 8.0}, {"asn": 64999, "pct": 3.0}]},
            "velocidade": {"janela": "90d", "em": d, "topo": [
                {"asn": a1, "download_mbps": 250.5, "upload_mbps": 120.25, "latencia_ociosa_ms": 9.5, "latencia_carregada_ms": 20.0, "jitter_ocioso_ms": 2.0, "testes": 321},
                {"asn": a4, "download_mbps": 90.0, "upload_mbps": 40.0, "latencia_ociosa_ms": 15.0, "latencia_carregada_ms": 30.0, "jitter_ocioso_ms": 3.0, "testes": 10}]},
            "bgp": {"em": d,
                    "vazamentos": {"janela_dias": 28, "total_informado": 5, "lidos": 1, "eventos": [{"id": 1, "em": f"{d}T10:00:00", "vazador": a1, "caminho": [a2, a1, 64999], "prefixos": 3, "encerrado": False}]},
                    "sequestros": {"janela_dias": 28, "total_informado": 2, "lidos": 2, "eventos": [
                        {"id": 7, "inicio": f"{d}T10:00:00", "fim": f"{d}T11:00:00", "sequestrador": a2, "vitimas": [a1], "prefixos": 2, "em_andamento": False, "rpki_invalido": True},
                        {"id": 8, "inicio": f"{d}T12:00:00", "fim": f"{d}T12:30:00", "sequestrador": 64999, "vitimas": [64998], "prefixos": 1, "em_andamento": False, "rpki_invalido": False}]}},
            "quedas": {"janela": "52w", "anomalias": 0, "anotacoes": 0, "consultado": True, "em": d}, "ultima_execucao": {}}
