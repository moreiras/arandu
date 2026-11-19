# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""IODA: quedas de Internet por país/ASN. **BLOQUEADO, não coleta**.

O host da API é `api.ioda.caida.org` (o `api.ioda.inetintelligence.cc.gatech.edu` não resolve). Não há termos de uso dos dados localizados (o repositório
da API restringe o software a pesquisa e educação acadêmica sem permissão; os dados são da Georgia Tech Research Corporation) e o host não respondeu nos testes (2026-11-06).
Pela regra de fontes, só entra com termos lidos ou autorização escrita. Este módulo existe para a fonte constar no catálogo como `ativa: false`; avisa e sai com código 0 sem fazer requisição (a etapa do arandu não aborta nem repete).
"""
from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    sys.stderr.write("ioda_outages: bloqueado (termos de uso dos dados não localizados; I-009). Nenhuma requisição feita.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
