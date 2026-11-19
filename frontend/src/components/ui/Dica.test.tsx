// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { Dica } from './Dica'
import { ComoLer } from './ComoLer'

describe('Dica (T2; NBR 17225 5.1.8 e 5.1.9)', () => {
  it('o ⓘ tem nome acessível; aberto, a explicação fica ligada por aria-describedby', () => {
    render(<Dica texto="Membros registrados no PTT" rotulo="Participantes" />)
    const botao = screen.getByRole('button', { name: 'Sobre: Participantes' })
    expect(screen.queryByRole('tooltip')).toBeNull()
    fireEvent.focus(botao)
    const balao = screen.getByRole('tooltip')
    expect(botao.getAttribute('aria-describedby')).toBe(balao.id)
    expect(balao.textContent).toBe('Membros registrados no PTT')
  })

  it('abre no toque/clique e fica; fecha com Esc e com toque fora', () => {
    render(<div><Dica texto="explicação" rotulo="X" /><span>fora</span></div>)
    const botao = screen.getByRole('button', { name: 'Sobre: X' })
    fireEvent.click(botao)
    expect(botao.getAttribute('aria-expanded')).toBe('true')
    fireEvent.mouseLeave(botao)
    expect(screen.getByRole('tooltip')).toBeTruthy()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('tooltip')).toBeNull()
    fireEvent.click(botao)
    fireEvent.pointerDown(screen.getByText('fora'))
    expect(screen.queryByRole('tooltip')).toBeNull()
  })

  it('abre no hover e continua aberta com o mouse no balão', () => {
    render(<Dica texto="explicação" rotulo="Y" />)
    const botao = screen.getByRole('button', { name: 'Sobre: Y' })
    fireEvent.mouseEnter(botao)
    const balao = screen.getByRole('tooltip')
    fireEvent.mouseLeave(botao)
    fireEvent.mouseEnter(balao)
    expect(screen.getByRole('tooltip')).toBeTruthy()
  })

  it('com children, o próprio conteúdo é o gatilho e o clique não chega ao pai (ordenação de coluna)', () => {
    let cliques = 0
    render(<div onClick={() => { cliques++ }}><Dica texto="nível">provável</Dica></div>)
    fireEvent.click(screen.getByRole('button', { name: 'provável' }))
    expect(cliques).toBe(0)
  })
})

describe('ComoLer (T3)', () => {
  it('fica fechado por padrão, com o resumo padronizado', () => {
    render(<ComoLer><p>método</p></ComoLer>)
    const d = screen.getByTestId('como-ler') as HTMLDetailsElement
    expect(d.open).toBe(false)
    expect(screen.getByText('Como ler')).toBeTruthy()
  })
})

describe('TabelaDados (T4)', () => {
  it('ordena por botão, mostra a dica da coluna e troca o tamanho da página', async () => {
    const { TabelaDados } = await import('./TabelaDados')
    const dados = Array.from({ length: 30 }, (_, i) => ({ n: i + 1 }))
    render(<TabelaDados rotulo="números" dados={dados} colunas={[{ accessorKey: 'n', header: 'Número', meta: { dica: 'um número', alinhar: 'right' } }]} />)
    expect(screen.getByRole('table', { name: 'números' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Sobre: Número' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /^Número/ }))
    expect(screen.getByRole('columnheader').getAttribute('aria-sort')).not.toBe('none')
    expect(screen.getAllByRole('row')).toHaveLength(26)
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '50' } })
    expect(screen.getAllByRole('row')).toHaveLength(31)
  })
})
