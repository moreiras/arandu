// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Formatos dos números do Panorama técnico: null vira null (o Kpi mostra "—"), nunca "0". */
export const pct = (v?: number | null, casas = 1) => (v == null || !Number.isFinite(v) ? null : `${v.toLocaleString('pt-BR', { maximumFractionDigits: casas })}%`)
export const num = (v?: number | null) => (v == null ? null : v.toLocaleString('pt-BR'))
/** Parte de um todo em %, ou null quando falta um dos dois. */
export const fracao = (parte?: number | null, todo?: number | null) => (parte == null || !todo ? null : (100 * parte) / todo)
/** Números grandes abreviados (161,1 mi; 2,4 bi): espaço em /48 e usuários. */
export function grande(v?: number | null): string | null {
  if (v == null) return null
  const a = Math.abs(v)
  if (a >= 1e12) return `${(v / 1e12).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} tri`
  if (a >= 1e9) return `${(v / 1e9).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} bi`
  if (a >= 1e6) return `${(v / 1e6).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mi`
  return v.toLocaleString('pt-BR')
}
