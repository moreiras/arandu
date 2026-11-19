# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tool de exposição de serviços do MCP: `asn_exposicao` (por ASN ou, no mesmo tool, por UF).

Mesma fonte das rotas `/asns/{asn}/exposicao` e `/exposicao/ufs/{uf}` (`api.services.exposicao` sobre `exposicao/asns.json.gz`). Só contagens do Shodan, com atribuição; nunca lista de IPs.
"""
from __future__ import annotations

from typing import Optional

from api.services import exposicao as expo
from mcp_server.contexto import _resolve, _store, mcp


@mcp.tool()
def asn_exposicao(asn: Optional[int] = None, uf: Optional[str] = None, date: Optional[str] = None) -> dict:
    """Serviços expostos à Internet que o Shodan observou numa rede (ASN) ou, derivado, numa UF: total, portas mais vistas, serviços de risco (Telnet, RDP, gestão de roteador, banco de dados) e CVEs se o plano tiver.

    Informe `asn` OU `uf`. Só contagens observadas pelo Shodan na data da leitura (rodízio; veja `lido_em` e a cobertura): NÃO é prova de vulnerabilidade, serviço é banner e não IP único, e
    ASN sem leitura = sem dado (NÃO zero). Nunca lista de IPs. Cite o Shodan, a data da leitura e o snapshot. A UF é agregado derivado dos ASNs lidos, sem CVEs.

    Args:
        asn: Número do AS.
        uf: Sigla da UF (ex.: SP), em vez do ASN.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    if (asn is None) == (uf is None):
        raise ValueError("Informe `asn` ou `uf` (um dos dois).")
    d = _resolve(date)
    doc = _store.exposicao_doc(d)
    b = expo.bloco_asn(doc, int(asn)) if asn is not None else expo.bloco_uf(doc, uf.strip())
    if b is None:
        raise ValueError(f"{'AS' + str(asn) if asn is not None else 'UF ' + uf} sem leitura de exposição do Shodan (ainda não consultado pelo rodízio ou produto não publicado) no snapshot {d}.")
    return b
