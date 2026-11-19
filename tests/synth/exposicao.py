# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Shodan (exposição de serviços) no dataset sintético.

Os três primeiros ASNs do Brasil: o 1º tem serviços, portas de risco (Telnet, TR-069, RDP) e CVEs; o 2º foi lido e o Shodan não viu serviço (zero observado, não ausência); o 3º tem serviços sem
nenhuma porta de risco. Os demais ainda não foram lidos pelo rodízio. Um ASN estrangeiro (64999) está no estado e não entra no produto. Plano com a faceta `vuln`."""
from __future__ import annotations

from tests.synth.world import World


def shodan_exposicao(world: World, d: str) -> dict:
    br = sorted(a for a, x in world.ases.items() if x.is_br)
    a1, a2, a3 = br[:3]
    return {"snapshot_date": d, "fetched_at": f"{d}T00:00:00+00:00", "fonte": "https://api.shodan.io/shodan/host/count", "licenca": "Shodan (sintético)",
            "atribuicao": "sintético (Shodan)", "plano": {"facetas": {"port": "ok", "vuln": "ok"}}, "asns_no_universo": len(br),
            "asns": {str(a1): {"em": d, "total": 400, "portas": [[80, 220], [443, 120], [23, 40], [7547, 9], [22, 3]], "risco": {"23": 40, "7547": 9, "3389": 2}, "risco_total": 51,
                               "vulns": [["CVE-2099-0001", 12], ["CVE-2099-0002", 5]]},
                     str(a2): {"em": d, "total": 0, "portas": [], "risco": {}, "risco_total": 0, "vulns": None},
                     str(a3): {"em": d, "total": 60, "portas": [[443, 40], [80, 20]], "risco": {}, "risco_total": 0, "vulns": []},
                     "64999": {"em": d, "total": 10, "portas": [[80, 10]], "risco": {"23": 10}, "risco_total": 10, "vulns": None}},
            "ultima_execucao": {}}
