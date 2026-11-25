// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurapé.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

/**
 * Como mostrar a margem de erro de uma célula das tabelas do Cetic.br.
 * - `zero_registrado`: proporção entre 0 e 100 com margem 0 na planilha. Numa estimativa amostral isso não é precisão perfeita; o
 *   valor vem assim da planilha e a causa não se conhece daqui. Não se escreve "±0,0".
 * - `precisao_baixa`: margem de pelo menos metade do valor estimado.
 * - `normal`, ou `sem` quando não há valor ou margem.
 */
export type EstadoMargem = 'sem' | 'normal' | 'zero_registrado' | 'precisao_baixa'

export const TEXTO_ZERO_REGISTRADO = 'margem de erro registrada como zero na planilha do Cetic.br'

export function estadoMargem(valor: number | null | undefined, margem: number | null | undefined, medida: 'proporcao' | 'total'): EstadoMargem {
  if (valor == null || margem == null) return 'sem'
  if (medida === 'proporcao' && margem === 0 && valor > 0 && valor < 100) return 'zero_registrado'
  if (valor > 0 && margem > 0 && margem >= 0.5 * valor) return 'precisao_baixa'
  return 'normal'
}
