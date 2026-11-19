// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

/**
 * Tabelas em cartões no celular. Abaixo de `sm` (639 px) cada linha vira um cartão: o CSS (`index.css`,
 * classe `tab-cartoes`) empilha as células e mostra, antes de cada valor, o rótulo da coluna, que aqui é copiado
 * do cabeçalho para `data-label`. Vale para todas as `<table>` do `<main>`; uma tabela que precisa continuar em grade
 * (matriz, mapa de calor) declara `data-tabela="grade"`. Cabeçalho com `colSpan`/`rowSpan` também fica em grade.
 */

/** Largura em que as tabelas viram cartões (igual ao `sm` do Tailwind). */
export const CONSULTA_CELULAR = '(max-width: 639px)'

function rotulosDoCabecalho(tabela: HTMLTableElement): string[] | null {
  const cab = tabela.tHead?.rows
  if (!cab || cab.length !== 1) return null
  const rotulos: string[] = []
  for (const th of Array.from(cab[0].cells)) {
    if (th.colSpan > 1 || th.rowSpan > 1) return null
    rotulos.push((th.textContent ?? '').replace(/[▲▼]/g, '').trim())
  }
  return rotulos
}

/** Marca e rotula as tabelas dentro de `raiz`; devolve quantas ficaram em cartões. Idempotente. */
export function rotularTabelas(raiz: ParentNode): number {
  let n = 0
  for (const tabela of Array.from(raiz.querySelectorAll<HTMLTableElement>('table'))) {
    if (tabela.dataset.tabela === 'grade') continue
    const rotulos = rotulosDoCabecalho(tabela)
    if (!rotulos) continue
    tabela.classList.add('tab-cartoes')
    n++
    for (const tr of Array.from(tabela.tBodies).flatMap((b) => Array.from(b.rows))) {
      Array.from(tr.cells).forEach((td, i) => {
        // célula que ocupa a linha toda (detalhe de linha expandida) ou sem rótulo fica sem rótulo
        const r = td.colSpan > 1 ? '' : rotulos[i] ?? ''
        if (r) { if (td.dataset.label !== r) td.dataset.label = r } else if (td.dataset.label) delete td.dataset.label
      })
    }
  }
  return n
}
