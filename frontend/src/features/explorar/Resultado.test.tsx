// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Resultado, type RespostaConsulta } from './Resultado'

const itens = [{ asn: 1, usuarios: 10 }, { asn: 2, usuarios: 30 }, { asn: 3, usuarios: 20 }]
const montar = (resposta: RespostaConsulta, onOrdem = vi.fn()) => {
  render(<MemoryRouter><Resultado colecao="asns" resposta={resposta} pagina={1} onPagina={() => {}} onOrdem={onOrdem} ordem={null}
    camposOrdenaveis={new Set(['asn', 'usuarios'])} /></MemoryRouter>)
  return onOrdem
}
const primeiraColuna = () => within(screen.getByRole('table', { name: 'Resultado' })).getAllByRole('row').slice(1).map((r) => r.querySelector('td')?.textContent)

describe('Resultado do Explorar: ordenação', () => {
  it('com só uma página do resultado, o clique pede a ordem ao servidor e não reordena a página', () => {
    const onOrdem = montar({ mode: 'list', total: 500, page: 1, pages: 5, items: itens })
    fireEvent.click(screen.getByRole('button', { name: /usuarios/ }))
    expect(onOrdem).toHaveBeenCalledWith(expect.objectContaining({ campo: 'usuarios' }))
    expect(primeiraColuna()).toEqual(['1', '2', '3'])
  })

  it('com o resultado inteiro, ordena na própria tabela', () => {
    const onOrdem = montar({ mode: 'list', total: 3, page: 1, pages: 1, items: itens })
    fireEvent.click(screen.getByRole('button', { name: /usuarios/ }))
    fireEvent.click(screen.getByRole('button', { name: /usuarios/ }))
    expect(onOrdem).not.toHaveBeenCalled()
    expect(new Set([primeiraColuna()[0], primeiraColuna()[2]])).toEqual(new Set(['2', '1']))
  })
})
