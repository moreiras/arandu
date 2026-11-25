// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

/**
 * A data do snapshot na URL (`?date=`) é o que torna um endereço citável: quem abre o link vê o mesmo snapshot. Estas funções a carregam
 * na navegação interna. Sem `date` na URL a página mostra o snapshot mais recente e o link também segue sem data.
 */

/** Acrescenta `date` a um caminho interno (`/asn/1`, `/x?aba=y#bloco`). Não mexe em endereço externo, em âncora pura nem em quem já traz `date`. */
export function comData(to: string, date: string | null | undefined): string {
  if (!date || !to.startsWith('/') || to.startsWith('//')) return to
  const i = to.indexOf('#')
  const semAncora = i >= 0 ? to.slice(0, i) : to
  const ancora = i >= 0 ? to.slice(i) : ''
  const j = semAncora.indexOf('?')
  // Acrescenta em vez de reserializar: os demais parâmetros ficam escritos como estavam (`ids=a,b` não vira `ids=a%2Cb`).
  if (j >= 0 && new URLSearchParams(semAncora.slice(j + 1)).has('date')) return to
  const sep = j < 0 ? '?' : j === semAncora.length - 1 ? '' : '&'
  return `${semAncora}${sep}date=${encodeURIComponent(date)}${ancora}`
}

/** Parâmetros novos (ex.: a aba escolhida) mantendo a data do snapshot dos atuais; os demais parâmetros são do estado anterior e saem. */
export function manterData(atuais: URLSearchParams, novos: Record<string, string> = {}): URLSearchParams {
  const p = new URLSearchParams(novos)
  const date = atuais.get('date')
  if (date) p.set('date', date)
  return p
}
