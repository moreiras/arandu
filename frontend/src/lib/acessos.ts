// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

/**
 * Base das barras de geração e modalidade do SICI móvel: a soma das próprias categorias. O coletor soma ali todo produto (M2M e ponto
 * de serviço inclusive), enquanto `acessos`/`total_acessos` contam só o produto padrão; com essa base as barras somavam 127% (PANORAMA-E1).
 */
export const somaValores = (d: Record<string, number> | null | undefined): number => Object.values(d ?? {}).reduce((a, b) => a + b, 0)
