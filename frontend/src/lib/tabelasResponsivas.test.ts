// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { rotularTabelas } from './tabelasResponsivas'

function html(corpo: string) {
  const d = document.createElement('div')
  d.innerHTML = corpo
  return d
}

describe('tabelas em cartões no celular', () => {
  it('copia o cabeçalho para data-label de cada célula e marca a tabela', () => {
    const d = html('<table><thead><tr><th>Fonte</th><th>Licença ▲</th></tr></thead><tbody><tr><td>A</td><td>CC</td></tr></tbody></table>')
    expect(rotularTabelas(d)).toBe(1)
    const tds = d.querySelectorAll('td')
    expect(d.querySelector('table')!.classList.contains('tab-cartoes')).toBe(true)
    expect(tds[0].dataset.label).toBe('Fonte')
    expect(tds[1].dataset.label).toBe('Licença')
  })

  it('célula com colSpan (detalhe de linha) e coluna sem título ficam sem rótulo', () => {
    const d = html('<table><thead><tr><th></th><th>Nome</th></tr></thead><tbody><tr><td>▸</td><td>x</td></tr><tr><td colspan="2">detalhe</td></tr></tbody></table>')
    rotularTabelas(d)
    const tds = d.querySelectorAll('td')
    expect(tds[0].dataset.label).toBeUndefined()
    expect(tds[1].dataset.label).toBe('Nome')
    expect(tds[2].dataset.label).toBeUndefined()
  })

  it('tabela declarada como grade, ou com cabeçalho de duas linhas ou colSpan, não vira cartão', () => {
    const d = html('<table data-tabela="grade"><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table>'
      + '<table><thead><tr><th colspan="2">Grupo</th></tr></thead><tbody><tr><td>1</td><td>2</td></tr></tbody></table>'
      + '<table><thead><tr><th>A</th></tr><tr><th>B</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table>')
    expect(rotularTabelas(d)).toBe(0)
  })

  it('é idempotente', () => {
    const d = html('<table><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table>')
    expect(rotularTabelas(d)).toBe(1)
    expect(rotularTabelas(d)).toBe(1)
    expect(d.querySelector('td')!.dataset.label).toBe('A')
  })
})
