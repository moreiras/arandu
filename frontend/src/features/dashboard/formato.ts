// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Formatação de números e contagem animada da Visão geral. */


// ─── number formatting helpers ───────────────────────────────────────────────

export function fmtN(n: number | undefined | null): string {
  if (n == null) return '—'
  return n.toLocaleString('pt-BR')
}

export function fmtLarge(n: number | undefined | null): string {
  if (n == null) return '—'
  if (n >= 1e9) return `${(n / 1e9).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}B`
  if (n >= 1e6) return `${(n / 1e6).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}M`
  return n.toLocaleString('pt-BR')
}

export function fmtPct(n: number | undefined | null, dec = 1): string {
  if (n == null) return '—'
  return `${n.toLocaleString('pt-BR', { minimumFractionDigits: dec, maximumFractionDigits: dec })}%`
}
