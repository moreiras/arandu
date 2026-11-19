# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tools do Cloudflare Radar do MCP: `asn_radar` e `uf_radar`.

Mesma fonte das rotas `/asns/{asn}/radar` e `/radar/ufs/{uf}` (`api.services.radar` sobre `radar/asns.json.gz`). Dados do Cloudflare Radar, CC BY-NC 4.0.
"""
from __future__ import annotations

from typing import Optional

from api.services import radar as rdr
from mcp_server.contexto import _resolve, _store, mcp


@mcp.tool()
def asn_radar(asn: int, date: Optional[str] = None) -> dict:
    """Cloudflare Radar numa rede (ASN): IPv6 (% das requisições HTTP de pessoas, com a data da leitura), tráfego e velocidade (só ASNs de topo) e papel nos eventos de BGP dos últimos 28 dias.

    Mede quem usa a Cloudflare, não a rede toda. ASN ausente ou campo ausente = sem dado, NÃO zero. Eventos de BGP (vazou, sequestrou, vítima) não provam intenção nem dano.
    Dados do Cloudflare Radar sob CC BY-NC 4.0: cite a Cloudflare, a licença, a data da leitura e o snapshot.

    Args:
        asn: Número do AS.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    b = rdr.bloco_asn(_store.radar_doc(d), int(asn))
    if b is None:
        raise ValueError(f"AS{asn} sem dado do Cloudflare Radar (ainda não lido pelo rodízio, fora do Radar ou produto não publicado) no snapshot {d}.")
    return b


@mcp.tool()
def uf_radar(uf: str, date: Optional[str] = None) -> dict:
    """Cloudflare Radar agregado por UF: ASNs com IPv6 lido, mediana e média ponderada pelo tráfego e soma dos papéis de BGP.

    DERIVADO dos ASNs pelo mapeamento ASN → UF do projeto (o Radar não tem recorte por UF); veja a cobertura na resposta. Dados CC BY-NC 4.0.

    Args:
        uf: Sigla da UF (ex.: SP).
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    b = rdr.bloco_uf(_store.radar_doc(d), uf.strip())
    if b is None:
        raise ValueError(f"UF {uf} sem dado do Cloudflare Radar (ou produto não publicado) no snapshot {d}.")
    return b
