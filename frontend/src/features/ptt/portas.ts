// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** 100000 → "100G", 10000 → "10G", 1000 → "1G", 100 → "100M"; repetidas viram "2× 10G". 0 = não informada. */
export function fmtPortas(v: number[] | undefined): string | null {
  if (!v?.length) return null
  const rot = (m: number) => (m <= 0 ? 'não informada' : m >= 1000 ? `${(m / 1000).toLocaleString('pt-BR')}G` : `${m}M`)
  const cont = new Map<string, number>()
  for (const m of v) cont.set(rot(m), (cont.get(rot(m)) ?? 0) + 1)
  return [...cont].map(([r, q]) => (q > 1 ? `${q}× ${r}` : r)).join(' + ')
}
