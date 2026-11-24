// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

/**
 * Escalas de cor para mapas e gráficos, seguras para daltonismo. A sequencial é a Viridis (percepção uniforme,
 * legível em escala de cinza); a divergente é a RdBu/ColorBrewer em versão que separa por luminosidade, não só por matiz.
 * Nunca depender só da cor: legenda com valores e, nas categorias, rótulo ou padrão.
 */
export const ESCALA_SEQUENCIAL = ['#440154', '#3b528b', '#21918c', '#5ec962', '#fde725'] as const
/** Texto único da legenda da escala sequencial: a Viridis vai do roxo (escuro, menor) ao amarelo (claro, maior). */
export const LEGENDA_SEQUENCIAL = 'Cor do roxo (menor valor) ao amarelo (maior valor); cinza = sem dado.'
export const ESCALA_DIVERGENTE = ['#b2182b', '#ef8a62', '#f7f7f7', '#67a9cf', '#2166ac'] as const
/** Categorias (até 8) distinguíveis por quem tem deuteranopia ou protanopia (paleta de Okabe-Ito). */
export const CATEGORIAS_SEGURAS = ['#0072b2', '#e69f00', '#009e73', '#d55e00', '#cc79a7', '#56b4e9', '#f0e442', '#000000'] as const

/** Cor da escala para um valor normalizado em [0, 1]; interpola entre as paradas. */
export function corDaEscala(escala: readonly string[], t: number): string {
  const x = Math.min(1, Math.max(0, Number.isFinite(t) ? t : 0)) * (escala.length - 1)
  const i = Math.min(escala.length - 2, Math.floor(x))
  const f = x - i
  const a = escala[i], b = escala[i + 1]
  const c = (h: string, k: number) => parseInt(h.slice(1 + 2 * k, 3 + 2 * k), 16)
  const mix = (k: number) => Math.round(c(a, k) + (c(b, k) - c(a, k)) * f).toString(16).padStart(2, '0')
  return `#${mix(0)}${mix(1)}${mix(2)}`
}
