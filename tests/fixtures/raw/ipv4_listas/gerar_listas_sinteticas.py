# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Gera as listas sintéticas de numeração (Registro.br, LACNIC) e o `delegated` de 3 dias, no formato real medido em 2026-11-02. Organizações e blocos inventados (blocos 198.18.0.0/15 e
203.0.113.0/24 são de documentação). Uso: python tests/fixtures/raw/ipv4_listas/gerar_listas_sinteticas.py"""
import gzip
import json
from pathlib import Path

AQUI = Path(__file__).parent

# data|origem|rir|pais|destino|rir|pais|recurso|conjunto original|data original
TRANSF = [
    ("2025-03-10", "ALFA TELECOM LTDA", "NICBR", "BR", "BETA REDES LTDA - ME", "NICBR", "BR", "198.18.0.0/22", "198.18.0.0/22", "2012-05-01"),
    ("2025-03-10", "ALFA TELECOM LTDA", "NICBR", "BR", "BETA REDES LTDA - ME", "NICBR", "BR", "198.18.4.0/22", "198.18.4.0/22", "2012-05-01"),        # mesma operação (lote)
    ("2025-06-02", "JOAO DA SILVA SANTOS", "NICBR", "BR", "GAMA NET S/A", "NICBR", "BR", "198.18.8/22", "198.18.8/22", "2013-01-01"),                # PF + CIDR abreviado
    ("2026-01-15", "GAMA NET S/A", "NICBR", "BR", "DELTA CORP", "LACNIC", "AR", "198.19.0.0/24", "198.19.0.0/24", "2014-02-02"),                     # saída para o exterior
    ("2026-10-29", "BETA REDES LTDA - ME", "NICBR", "BR", "EPSILON COMUNICACOES LTDA", "NICBR", "BR", "198.18.0.0/22", "198.18.0.0/22", "2025-03-10"),
]
RECUP = ["198.19.4.0/24|2026-09-01 - 2026-11-30", "64999|2026-09-01 - 2026-11-30", "2001:db8:1::/48|2026-09-01 - 2026-11-30"]
RECUPERADOS = ["198.19.5.0/24", "65001", "2001:db8:2::/48"]
LOG = {"version": "1", "transfers": [
    {"asns": [], "ip4nets": [{"original_set": [{"start_address": "198.19.0.0", "end_address": "198.19.0.255"}], "transfer_set": [{"start_address": "198.19.0.0", "end_address": "198.19.0.255"}]}], "ip6nets": [],
     "recipient_organization": {"country_code": "AR", "name": "DELTA CORP"}, "recipient_rir": "LACNIC", "source_organization": {"country_code": "BR", "name": "GAMA NET S/A"}, "source_rir": "NICBR",
     "source_registration_date": "2014-02-02 05:00:00.000-0700", "transfer_date": "2026-01-15 04:00:00.000-0700", "type": "RESOURCE_TRANSFER"},
    {"asns": [], "ip4nets": [{"original_set": [{"start_address": "203.0.113.0", "end_address": "203.0.113.255"}], "transfer_set": [{"start_address": "203.0.113.0", "end_address": "203.0.113.255"}]}], "ip6nets": [],
     "recipient_organization": {"country_code": "MX", "name": "OMEGA SA"}, "recipient_rir": "LACNIC", "source_organization": {"country_code": "CL", "name": "SIGMA LTDA"}, "source_rir": "LACNIC",
     "source_registration_date": "2010-01-01 05:00:00.000-0700", "transfer_date": "2026-10-20 04:00:00.000-0700", "type": "RESOURCE_TRANSFER"},
    {"asns": [], "ip4nets": [{"original_set": [{"start_address": None, "end_address": None}], "transfer_set": [{"start_address": None, "end_address": None}]}], "ip6nets": [],
     "recipient_organization": {"country_code": "MX", "name": "SEM ENDERECO"}, "recipient_rir": "LACNIC", "source_organization": {"country_code": "CL", "name": "X"}, "source_rir": "LACNIC",
     "source_registration_date": "2010-01-01 05:00:00.000-0700", "transfer_date": "2026-10-21 04:00:00.000-0700", "type": "RESOURCE_TRANSFER"}]}


def delegated(dia: str, estado: dict) -> str:
    """Linhas no formato `registro|cc|tipo|início|quantidade|data|status|opaque-id`."""
    ln = [f"2.3|lacnic|{dia}|0|19870101|{dia}|-0300", "lacnic|*|ipv4|*|0|summary"]
    for (ini, q), (cc, data, status, opaque) in estado.items():
        ln.append(f"lacnic|{cc}|ipv4|{ini}|{q}|{data}|{status}|{opaque}")
    return "\n".join(ln) + "\n"


# 3 dias: d1 base; d2 troca de titularidade (opaque), recuperação (allocated→reserved) e bloco novo; d3 liberação (reserved→allocated), mudança de país e bloco removido
D1 = {("198.18.0.0", 1024): ("BR", "20120501", "allocated", "org-alfa"), ("198.18.8.0", 1024): ("BR", "20130101", "allocated", "org-pf"),
      ("198.19.4.0", 256): ("BR", "20140101", "allocated", "org-recup"), ("198.19.8.0", 256): ("BR", "20150101", "allocated", "org-x"), ("198.19.9.0", 256): ("BR", "20150101", "allocated", "org-y")}
D2 = {**D1, ("198.18.0.0", 1024): ("BR", "20120501", "allocated", "org-beta"), ("198.19.4.0", 256): ("", "", "reserved", ""), ("198.19.12.0", 256): ("BR", "20261101", "allocated", "org-novo")}
D3 = {k: v for k, v in D2.items() if k != ("198.19.9.0", 256)}
D3[("198.19.4.0", 256)] = ("BR", "20261102", "allocated", "org-recup2")
D3[("198.19.8.0", 256)] = ("AR", "20150101", "allocated", "org-x")


def main():
    (AQUI / "registrobr-transferencias-diretas-lacnic").write_text("# Generated on 2026-11-02\n# Format: <transfer date>|...\n" + "\n".join("|".join(t) for t in TRANSF) + "\n", encoding="latin-1")
    (AQUI / "registrobr-transferencias-diretas").write_text("# Generated on 2026-11-02\n# Format: <transfer date>|...\n" + "\n".join("|".join(t[:8]) for t in TRANSF) + "\n", encoding="latin-1")
    (AQUI / "registrobr-recuperacao").write_text("# Generated on 2026-11-02\n# Format:\n# RESOURCE|init date - end date\n" + "\n".join(RECUP) + "\n", encoding="latin-1")
    (AQUI / "registrobr-recuperados").write_text("# Generated on 2026-11-02\n" + "\n".join(RECUPERADOS) + "\n", encoding="latin-1")
    (AQUI / "lacnic-transfers.json").write_text(json.dumps(LOG))
    for dia, est in (("20261031", D1), ("20261101", D2), ("20261102", D3)):
        (AQUI / f"delegated-lacnic-extended-{dia}.gz").write_bytes(gzip.compress(delegated(dia, est).encode(), mtime=0))
    print("ok")


if __name__ == "__main__":
    main()
