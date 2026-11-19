// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

/** CNPJ de 14 dígitos no formato 00.000.000/0000-00; qualquer outra coisa volta como veio. */
export function formatarCnpj(c: string): string {
  const d = (c ?? '').replace(/\D/g, '')
  if (d.length !== 14) return c
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`
}

/**
 * Rótulos que aparecem mais de uma vez numa lista (a mesma marca com CNPJs diferentes: "CLARO" duas vezes na home, "VIVO" nas ERBs).
 * Quem usa mostra o CNPJ ao lado só nesses casos, para a lista não parecer ter linha duplicada.
 */
export function rotulosRepetidos(rotulos: string[]): Set<string> {
  const vistos = new Set<string>()
  const repetidos = new Set<string>()
  for (const r of rotulos) (vistos.has(r) ? repetidos : vistos).add(r)
  return repetidos
}
