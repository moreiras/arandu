# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""AS com ROAs que não publicou ASPA (adoção ainda baixa, mas recomendada)."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado
from core import alerta_textos

REGRA = Regra(id="sem_aspa", categoria="rpki", severidade="aviso", versao=1,
              descricao="roa_list não vazio e aspa_providers ausente")


def avaliar(ctx: Contexto) -> list[dict]:
    if ctx.doc.get("roa_list") and ctx.doc.get("aspa_providers") is None:
        return [achado(
            "Sem ASPA",
            alerta_textos.sem_aspa())]
    return []
