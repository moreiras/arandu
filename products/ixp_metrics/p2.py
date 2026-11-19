# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Alias de compatibilidade: o módulo vive em `products.ixp_metrics.metricas_ixp` (`gerar_metricas_ixp`)."""
from products.ixp_metrics.metricas_ixp import *  # noqa: F401,F403
from products.ixp_metrics.metricas_ixp import gerar_metricas_ixp as run_p2  # noqa: F401
