// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { fireEvent, render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { HilbertMap16 } from './HilbertMap16'
import { HilbertMapV6Block, V6_LAYER_META } from './HilbertMapV6Block'
import { V6_BLOCKS, block16ToSlash8 } from './hilbert'
import { nomeAmpliar, prefixoQuadranteV4, prefixoQuadranteV6 } from './quadrantes'

beforeAll(() => { vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} unobserve() {} }) })

const lacnic = V6_BLOCKS.find((b) => b.id === 'lacnic')!
const envolve = (ui: React.ReactNode) => <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>

/** O navegador dispara o clique do botão com Enter (keydown) ou Espaço (keyup); o jsdom não, então o teste faz os dois passos. */
function acionaComEnter(el: HTMLElement) {
  el.focus()
  fireEvent.keyDown(el, { key: 'Enter' })
  fireEvent.click(el)
}

describe('zoom de quadrante pelo teclado', () => {
  it('nomes acessíveis a partir do prefixo real do quadrante', () => {
    expect(nomeAmpliar('2001::/20')).toBe('Ampliar quadrante 2001::/20')
    expect(prefixoQuadranteV4(200)).toBe('200.0.0.0/8')
    expect(prefixoQuadranteV6(lacnic, 0, 0)).toBe('2800:0000::/20')
    expect(prefixoQuadranteV6(V6_BLOCKS[0], 0, 0)).toBe('2001:0000::/20')
  })

  it('IPv6: o botão é focável, abre o ModalAcessivel por Enter e o foco volta ao botão ao fechar', () => {
    const dados = { rir_br: [0, 1, 2], global_br: [], global_all: [], ixp_all: [], rir_br_visible: [] }
    render(envolve(<HilbertMapV6Block config={lacnic} data={dados} activeLayer="rir_br" cssWidth={240} layerMeta={V6_LAYER_META} />))
    const botao = screen.getByRole('button', { name: 'Ampliar quadrante 2800:0000::/20' })
    expect(botao).toHaveAttribute('type', 'button')
    expect(botao.tabIndex).toBe(0)
    acionaComEnter(botao)
    const dialogo = screen.getByRole('dialog')
    expect(dialogo).toHaveAttribute('aria-modal', 'true')
    expect(dialogo.contains(document.activeElement)).toBe(true)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(document.activeElement).toBe(botao)
  })

  it('IPv6: só há botão para quadrante com dado', () => {
    render(envolve(<HilbertMapV6Block config={lacnic} data={{ rir_br: [0], global_br: [], global_all: [], ixp_all: [], rir_br_visible: [] }} activeLayer="rir_br" cssWidth={240} layerMeta={V6_LAYER_META} />))
    expect(screen.getAllByRole('button', { name: /^Ampliar quadrante / })).toHaveLength(1)
  })

  it('IPv4: o botão do /8 abre o zoom e devolve o foco ao fechar', () => {
    const dens = new Array<number>(65536).fill(0)
    const d = (200 << 8) | 5
    dens[d] = 3
    expect(block16ToSlash8(d)).toBe(200)
    render(envolve(<HilbertMap16 data={{ rir_br: dens, global_br: dens, global_all: dens, ixp_all: dens, rir_br_visible: dens }} activeLayer="rir_br" semDetalhe />))
    const botao = screen.getByRole('button', { name: 'Ampliar quadrante 200.0.0.0/8' })
    acionaComEnter(botao)
    const dialogo = screen.getByRole('dialog')
    expect(within(dialogo).getByRole('heading', { name: '200.0.0.0/8' })).toBeTruthy()
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Fechar' }))
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(document.activeElement).toBe(botao)
  })
})
