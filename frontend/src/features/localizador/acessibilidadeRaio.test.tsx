// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Localizador sem mouse (PT-22 / localizador 5.3): diálogo com foco e Escape, ponto por coordenadas e a tabela do raio em texto. */
import { MemoryRouter } from 'react-router-dom'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ModalEntidades } from './ModalEntidades'
import { PainelControles } from './PainelControles'
import { POR_PAGINA_TABELA, TabelaEntidades } from './TabelaEntidades'
import type { Entity } from './tipos'

const ent = (i: number, extra: Partial<Entity> = {}): Entity => ({
  key: `cnpj:${i}`, cnpj: String(10000000000000 + i), asns: [i, i + 1000], asnsNoRaio: [i], name: `Rede ${i}`, city: 'Juazeiro do Norte', uf: 'CE',
  fromHq: true, v4: true, v6: false, scm: true, scmHq: false, ...extra,
})

describe('ModalEntidades', () => {
  it('é um diálogo com nome, o foco vai ao botão Fechar e Escape fecha', () => {
    const fechar = vi.fn()
    render(<ModalEntidades titulo="3 redes neste ponto" html="<p>corpo</p>" aoFechar={fechar} />)
    const d = screen.getByRole('dialog', { name: '3 redes neste ponto' })
    expect(d).toHaveAttribute('aria-modal', 'true')
    expect(within(d).getByRole('button', { name: 'Fechar' })).toHaveFocus()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(fechar).toHaveBeenCalledTimes(1)
  })

  it('o clique no fundo fecha, o clique no conteúdo não', () => {
    const fechar = vi.fn()
    render(<ModalEntidades titulo="t" html="<p>corpo</p>" aoFechar={fechar} />)
    fireEvent.click(screen.getByText('corpo'))
    expect(fechar).not.toHaveBeenCalled()
    fireEvent.click(screen.getByTestId('modal-entidades'))
    expect(fechar).toHaveBeenCalledTimes(1)
  })
})

describe('PainelControles: ponto por coordenadas', () => {
  const montar = (aoDefinir = vi.fn()) => {
    render(<PainelControles className="" search="" setSearch={() => {}} searching={false} onSearch={() => {}} radius={80} setRadius={() => {}}
      show={{ asns: true, prefixes: true, scms: true, sici: true }} setShow={() => {}} aoDefinirCoordenadas={aoDefinir} />)
    return aoDefinir
  }

  it('campos com rótulo; vírgula decimal aceita; só habilita com valores válidos', () => {
    const aoDefinir = montar()
    const botao = screen.getByRole('button', { name: 'Usar estas coordenadas' })
    expect(botao).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Latitude'), { target: { value: '-7,21' } })
    fireEvent.change(screen.getByLabelText('Longitude'), { target: { value: '-39,31' } })
    expect(botao).toBeEnabled()
    fireEvent.click(botao)
    expect(aoDefinir).toHaveBeenCalledWith(-7.21, -39.31)
  })

  it('fora do intervalo não habilita', () => {
    montar()
    fireEvent.change(screen.getByLabelText('Latitude'), { target: { value: '95' } })
    fireEvent.change(screen.getByLabelText('Longitude'), { target: { value: '10' } })
    expect(screen.getByRole('button', { name: 'Usar estas coordenadas' })).toBeDisabled()
  })

  it('a busca tem nome acessível', () => {
    montar()
    expect(screen.getByRole('textbox', { name: /Município/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Ir ao município/ })).toBeInTheDocument()
  })
})

describe('TabelaEntidades', () => {
  const abrir = () => { const d = screen.getByTestId('tabela-localizador') as HTMLDetailsElement; d.open = true }

  it('legenda, cabeçalhos de coluna e de linha, ASNs do raio e os de fora à parte', () => {
    render(<MemoryRouter><TabelaEntidades entities={[ent(1), ent(2, { asnsNoRaio: [], cnpj: undefined, asns: [2], v4: false, v6: true, scm: false, sici: { acessos: 1200, municipios: 1 } })]} /></MemoryRouter>)
    abrir()
    const t = screen.getByRole('table')
    expect(within(t).getAllByRole('columnheader')).toHaveLength(8)
    expect(within(t).getByRole('rowheader', { name: /Rede 1/ })).toBeInTheDocument()
    expect(t).toHaveTextContent('AS1')
    expect(t).toHaveTextContent('mais 1 ASN do mesmo CNPJ fora do raio')
    expect(t).toHaveTextContent('1.200 (1 município)')
  })

  it('pagina de 50 em 50', () => {
    const todas = Array.from({ length: POR_PAGINA_TABELA + 5 }, (_, i) => ent(i + 1))
    render(<MemoryRouter><TabelaEntidades entities={todas} /></MemoryRouter>)
    abrir()
    expect(screen.getAllByRole('row')).toHaveLength(POR_PAGINA_TABELA + 1)
    fireEvent.click(screen.getByRole('button', { name: 'Próxima' }))
    expect(screen.getAllByRole('row')).toHaveLength(5 + 1)
    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument()
  })
})
