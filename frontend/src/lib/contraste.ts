// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Contraste de cor (NBR 17225 5.11.3): números de destaque coloridos precisam de 4,5:1 sobre o fundo claro. */

function lin(c: number): number {
  const s = c / 255
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
}

function rgb(hex: string): [number, number, number] | null {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim())
  if (!m) return null
  const v = parseInt(m[1], 16)
  return [(v >> 16) & 255, (v >> 8) & 255, v & 255]
}

export function luminancia(hex: string): number {
  const c = rgb(hex)
  return c ? 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]) : 0
}

export function contraste(a: string, b: string): number {
  const [x, y] = [luminancia(a), luminancia(b)].sort((p, q) => q - p)
  return (x + 0.05) / (y + 0.05)
}

/** A mesma cor, escurecida em passos de 5% até ter `minimo` de contraste com `fundo` (padrão: branco). Cor que não é #rrggbb volta como veio. */
export function corLegivel(hex: string | undefined, minimo = 4.5, fundo = '#ffffff'): string | undefined {
  const c = hex ? rgb(hex) : null
  if (!hex || !c) return hex
  let [r, g, b] = c
  let atual = `#${[r, g, b].map((v) => v.toString(16).padStart(2, '0')).join('')}`
  for (let i = 0; i < 40 && contraste(atual, fundo) < minimo; i++) {
    ;[r, g, b] = [r, g, b].map((v) => Math.round(v * 0.95)) as [number, number, number]
    atual = `#${[r, g, b].map((v) => v.toString(16).padStart(2, '0')).join('')}`
  }
  return atual
}
