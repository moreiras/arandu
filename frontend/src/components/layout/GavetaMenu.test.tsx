// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { GavetaMenu } from './GavetaMenu'
import { GRUPOS_MENU, ITENS_AVULSOS } from './menu'

const montar = (path = '/', topo?: React.ReactNode) => render(<MemoryRouter initialEntries={[path]}><GavetaMenu topo={topo} /></MemoryRouter>)

describe('gaveta do celular', () => {
  it('abre pelo ☰, mostra o topo (login e snapshot) e fecha com Esc devolvendo o foco', () => {
    montar('/', <a href="/login">Entrar</a>)
    const botao = screen.getByRole('button', { name: 'Abrir menu' })
    fireEvent.click(botao)
    expect(screen.getByRole('dialog', { name: 'Menu' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Entrar' })).toBeInTheDocument()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(document.activeElement).toBe(botao)
  })

  it('acordeão: um grupo aberto por vez, e o da página atual já vem aberto', () => {
    montar('/ixp/sp')
    fireEvent.click(screen.getByRole('button', { name: 'Abrir menu' }))
    expect(screen.getByRole('button', { name: /Interconexão/ })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: /^Rede/ })).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(screen.getByRole('button', { name: /^Rede/ }))
    expect(screen.getByRole('button', { name: /^Rede/ })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: /Interconexão/ })).toHaveAttribute('aria-expanded', 'false')
  })

  it('todo grupo e todo item do menu estão na gaveta (nada fora da tela)', () => {
    montar('/')
    fireEvent.click(screen.getByRole('button', { name: 'Abrir menu' }))
    for (const g of GRUPOS_MENU) {
      fireEvent.click(screen.getByRole('button', { name: new RegExp('^' + g.rotulo) }))
      for (const i of g.itens) expect(screen.getByRole('link', { name: i.rotulo }), `${g.rotulo} › ${i.rotulo}`).toHaveAttribute('href', i.to)
    }
  })

  it('o item avulso Comparar aparece na gaveta, fora dos acordeões', () => {
    montar('/')
    fireEvent.click(screen.getByRole('button', { name: 'Abrir menu' }))
    for (const i of ITENS_AVULSOS) expect(screen.getByRole('link', { name: i.rotulo })).toHaveAttribute('href', i.to)
  })

  it('travar a rolagem da página enquanto aberta e liberar ao fechar', () => {
    montar('/')
    fireEvent.click(screen.getByRole('button', { name: 'Abrir menu' }))
    expect(document.body.style.overflow).toBe('hidden')
    fireEvent.click(screen.getByRole('button', { name: 'Fechar menu' }))
    expect(document.body.style.overflow).not.toBe('hidden')
  })
})
