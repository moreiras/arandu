// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

/**
 * Regra do site: IPv6 aparece antes de IPv4. Os dados chegam na ordem do pipeline (v4, v6);
 * estas funções reordenam listas de famílias (`v4`/`v6`, `ipv4`/`ipv6`, `IPv4`/`IPv6`) para a exibição. O que não é família fica onde está.
 */
const peso = (f: string) => (/6$/.test(f) ? 0 : /4$/.test(f) ? 1 : 2)

export function familiasV6Primeiro<T extends string>(familias: readonly T[]): T[] {
  return [...familias].sort((a, b) => peso(a) - peso(b))
}

/** `['v4', 'v6']` → `"IPv6 e IPv4"` (ou com outro separador). */
export function nomesFamilias(familias: readonly string[], sep = ' e '): string {
  return familiasV6Primeiro(familias).map((f) => f.replace(/^(ip)?v/i, 'IPv')).join(sep)
}
