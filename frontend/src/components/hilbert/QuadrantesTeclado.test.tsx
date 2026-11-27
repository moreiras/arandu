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
import { V6_BLOCKS, block16ToSlash8, getPosToD1024 } from './hilbert'
import { ZoomModalV6 } from './IXPHilbertZoom'
import { nomeAmpliar, prefixoQuadranteDeCelula, prefixoQuadranteV4, prefixoQuadranteV6 } from './quadrantes'

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
    expect(prefixoQuadranteV6(lacnic, 0, 0)).toBe('2800::/20')
    expect(prefixoQuadranteV6(V6_BLOCKS[0], 0, 0)).toBe('2001::/20')
  })

  it('prefixo /20 na forma comprimida da RFC 5952: minúsculas, sem zeros à esquerda, "::" no fim', () => {
    const ripe = V6_BLOCKS.find((b) => b.id === 'ripe')!
    expect(prefixoQuadranteDeCelula(V6_BLOCKS[0], 0x1234)).toBe('2001:1000::/20')
    expect(prefixoQuadranteDeCelula(V6_BLOCKS[0], 0x1200)).toBe('2001:1000::/20')
    expect(prefixoQuadranteDeCelula(V6_BLOCKS[0], 0x0fff)).toBe('2001::/20')
    expect(prefixoQuadranteDeCelula(lacnic, 0)).toBe('2800::/20')
    expect(prefixoQuadranteDeCelula(lacnic, 0x10000)).toBe('2801::/20')
    expect(prefixoQuadranteDeCelula(lacnic, 0x12345)).toBe('2801:2000::/20')
    expect(prefixoQuadranteDeCelula(ripe, 0xabcde)).toBe('2a0a:b000::/20')
    expect(prefixoQuadranteDeCelula(lacnic, 0x2000)).toBe('2800:2000::/20')
  })

  it('o título do modal usa o mesmo prefixo comprimido', () => {
    render(envolve(<ZoomModalV6 config={lacnic} gx={0} gy={0} allCells={[0, 1]} ownCells={null} thirdCells={null} isPeerMode={false} color="#0891b2" onClose={() => {}} />))
    expect(screen.getByRole('dialog')).toHaveAccessibleName('2800::/20')
  })

  it('IPv6: o botão é focável, abre o ModalAcessivel por Enter e o foco volta ao botão ao fechar', () => {
    const dados = { rir_br: [0, 1, 2], global_br: [], global_all: [], ixp_all: [], rir_br_visible: [] }
    render(envolve(<HilbertMapV6Block config={lacnic} data={dados} activeLayer="rir_br" cssWidth={240} layerMeta={V6_LAYER_META} />))
    const botao = screen.getByRole('button', { name: 'Ampliar quadrante 2800::/20' })
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

  describe('grupo de quadrantes com roving tabindex', () => {
    const celula = (gx: number, gy: number) => getPosToD1024()[gy * 64 * 1024 + gx * 64]
    // quadrantes (coluna, linha): A (0,0), B (1,0), C (0,1), D (2,2)
    const dados = { rir_br: [celula(0, 0), celula(1, 0), celula(0, 1), celula(2, 2)], global_br: [], global_all: [], ixp_all: [], rir_br_visible: [] }
    const monta = () => {
      render(envolve(<HilbertMapV6Block config={lacnic} data={dados} activeLayer="rir_br" cssWidth={240} layerMeta={V6_LAYER_META} />))
      const b = (gx: number, gy: number) => screen.getByRole('button', { name: nomeAmpliar(prefixoQuadranteV6(lacnic, gx, gy)) })
      return { A: b(0, 0), B: b(1, 0), C: b(0, 1), D: b(2, 2) }
    }
    const paradas = () => screen.getAllByRole('button', { name: /^Ampliar quadrante / }).filter((x) => x.tabIndex === 0)

    it('o contêiner é um grupo nomeado e o grupo tem uma só parada de Tab', () => {
      const { A, B, C, D } = monta()
      expect(screen.getByRole('group', { name: 'Quadrantes do mapa IPv6 2800::/12, use as setas' })).toBeTruthy()
      expect(paradas()).toEqual([A])
      expect([B, C, D].map((x) => x.tabIndex)).toEqual([-1, -1, -1])
    })

    it('setas seguem a geometria da grade e a parada de Tab acompanha o foco', () => {
      const { A, B, C, D } = monta()
      A.focus()
      fireEvent.keyDown(A, { key: 'ArrowLeft' })
      expect(document.activeElement).toBe(A)
      fireEvent.keyDown(A, { key: 'ArrowRight' })
      expect(document.activeElement).toBe(B)
      expect(paradas()).toEqual([B])
      fireEvent.keyDown(B, { key: 'ArrowRight' })
      expect(document.activeElement).toBe(D)
      fireEvent.keyDown(D, { key: 'ArrowUp' })
      expect(document.activeElement).toBe(B)
      fireEvent.keyDown(B, { key: 'ArrowLeft' })
      expect(document.activeElement).toBe(A)
      fireEvent.keyDown(A, { key: 'ArrowDown' })
      expect(document.activeElement).toBe(C)
      fireEvent.keyDown(C, { key: 'ArrowUp' })
      expect(document.activeElement).toBe(A)
      expect(paradas()).toEqual([A])
    })

    it('Home e End vão ao primeiro e ao último quadrante', () => {
      const { A, D } = monta()
      A.focus()
      fireEvent.keyDown(A, { key: 'End' })
      expect(document.activeElement).toBe(D)
      expect(paradas()).toEqual([D])
      fireEvent.keyDown(D, { key: 'Home' })
      expect(document.activeElement).toBe(A)
    })

    it('Enter abre o zoom do quadrante focado e, ao fechar, o foco volta a ele, que segue como a parada de Tab', () => {
      const { A, D } = monta()
      A.focus()
      fireEvent.keyDown(A, { key: 'End' })
      acionaComEnter(D)
      expect(screen.getByRole('dialog')).toBeTruthy()
      fireEvent.keyDown(document, { key: 'Escape' })
      expect(screen.queryByRole('dialog')).toBeNull()
      expect(document.activeElement).toBe(D)
      expect(paradas()).toEqual([D])
    })
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
