# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tool de bloqueios medidos pelo OONI do MCP: `asn_bloqueios`.

Mesma fonte da rota `/asns/{asn}/bloqueios` (`api.services.bloqueios` sobre `bloqueios/asns.json.gz`). Veredito da sonda, não do backend do OONI; dados CC BY-NC-SA 4.0.
"""
from __future__ import annotations

from typing import Optional

from api.services import bloqueios as blq
from mcp_server.contexto import _resolve, _store, mcp


@mcp.tool()
def asn_bloqueios(asn: int, date: Optional[str] = None) -> dict:
    """Medições do OONI numa rede (ASN): por teste (WhatsApp, Telegram, Signal, Messenger, Tor, Psiphon e, por amostra, Web Connectivity), quantas medições e quantas a PRÓPRIA sonda declarou anômalas.

    NÃO é censura confirmada: é o veredito da sonda do voluntário (não o do backend do OONI), que pode ser filtro do cliente, VPN, falha do serviço ou falso positivo; sondas são poucas e enviesadas.
    Só testes com 10 ou mais medições na janela; ASN ausente = sem dados suficientes, NÃO "sem bloqueio". Dados do OONI sob CC BY-NC-SA 4.0: cite OONI (ooni.org), a licença, a janela e o snapshot.
    Para cruzar vários ASNs, `query(collection="bloqueios_asn")`.

    Args:
        asn: Número do AS.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    b = blq.bloco_asn(_store.bloqueios_doc(d), int(asn))
    if b is None:
        raise ValueError(f"AS{asn} sem teste do OONI com o mínimo de medições (ou produto não publicado) no snapshot {d}.")
    return b
