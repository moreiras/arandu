# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Ligação por referência entre camadas: a camada de serviço (`api`, `mcp_server`) não importa `products`.

O enriquecimento sob demanda do documento de ASN (alertas, RPKI, ASPA) é lógica de produto (`products/asn_saude`) que a API ainda usa para
quem não foi pré-enriquecido no publish (os ASes não-BR, por exemplo). Em vez de um import estático, a API pede a função por uma referência
`"pacote.modulo:funcao"` — configurável por `ARANDU_ENRIQUECEDOR` — e este módulo a resolve na primeira chamada. O import-linter não vê a
dependência e o código de serviço continua sem conhecer os produtos; trocar o enriquecedor (ou desligá-lo) é só configuração.
"""
from __future__ import annotations

import importlib
import os
from functools import lru_cache
from typing import Callable, Optional

ENRIQUECEDOR_PADRAO = "products.asn_saude.enrich:enrich_asn_document"


@lru_cache(maxsize=None)
def resolver(referencia: str) -> Callable:
    """`"pacote.modulo:funcao"` → a função. Levanta ImportError/AttributeError se a referência não existir (falha alto)."""
    modulo, _, nome = referencia.partition(":")
    if not modulo or not nome:
        raise ValueError(f"referência inválida: {referencia!r} (esperado 'pacote.modulo:funcao')")
    return getattr(importlib.import_module(modulo), nome)


def enriquecedor_de_asn() -> Optional[Callable]:
    """A função de enriquecimento do documento de ASN, ou None se `ARANDU_ENRIQUECEDOR=off` (a API serve o documento como está)."""
    ref = os.environ.get("ARANDU_ENRIQUECEDOR", ENRIQUECEDOR_PADRAO)
    if ref.lower() in ("off", "", "none", "nenhum"):
        return None
    return resolver(ref)
