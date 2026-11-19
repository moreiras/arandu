# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""AS com ROAs que não publicou ASPA (adoção ainda baixa, mas recomendada)."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado

REGRA = Regra(id="sem_aspa", categoria="rpki", severidade="aviso", versao=1,
              descricao="roa_list não vazio e aspa_providers ausente")


def avaliar(ctx: Contexto) -> list[dict]:
    if ctx.doc.get("roa_list") and ctx.doc.get("aspa_providers") is None:
        return [achado(
            "Sem ASPA",
            "O AS possui ROAs no RPKI mas não publicou nenhum objeto ASPA "
            "(Autonomous System Provider Authorization). O ASPA declara os "
            "upstreams autorizados e permite validação de AS_PATH — sua "
            "ausência não expõe o AS a risco imediato, mas a publicação é "
            "recomendada à medida que a adoção cresce.")]
    return []
