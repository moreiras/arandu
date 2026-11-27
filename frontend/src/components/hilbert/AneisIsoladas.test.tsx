// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { HilbertMapV6Block, V6_LAYER_META } from './HilbertMapV6Block'
import { HilbertMapV6 } from './HilbertMapV6'
import { LEGENDA_MARCADOR } from './isoladas'
import { V6_BLOCKS } from './hilbert'

beforeAll(() => { vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} unobserve() {} }) })

const lacnic = V6_BLOCKS.find((b) => b.id === 'lacnic')!
const envolve = (ui: React.ReactNode) => <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>

describe('marcador de célula isolada no mapa IPv6', () => {
  const dados = (cells: number[]) => ({ rir_br: cells, global_br: [], global_all: [], ixp_all: [], rir_br_visible: [] })
  const aneis = (c: HTMLElement) => c.querySelectorAll('[data-testid="aneis-isoladas"] circle')

  it('desenha um anel por célula isolada, em tom neutro, sem mudar o tamanho do canvas', () => {
    const { container } = render(envolve(<HilbertMapV6Block config={lacnic} data={dados([0, 500000, 1000, 1001])} activeLayer="rir_br" cssWidth={240} layerMeta={V6_LAYER_META} />))
    const rs = aneis(container)
    expect(rs).toHaveLength(2)
    for (const c of Array.from(rs)) {
      expect(c.getAttribute('stroke')).toBe('#1e293b')
      expect(c.getAttribute('stroke-opacity')).toBe('0.55')
    }
    const canvas = container.querySelector('canvas')!
    expect(canvas.width).toBe(1024)
    expect(canvas.style.width).toBe('240px')
  })

  it('sem célula isolada não há anel', () => {
    const { container } = render(envolve(<HilbertMapV6Block config={lacnic} data={dados([1000, 1001, 1002])} activeLayer="rir_br" cssWidth={240} layerMeta={V6_LAYER_META} />))
    expect(aneis(container)).toHaveLength(0)
  })

  it('a legenda explica o anel em linguagem simples, sem travessão', () => {
    render(<HilbertMapV6 data={null} />)
    expect(screen.getByText(new RegExp(LEGENDA_MARCADOR.slice(0, 30)))).toBeTruthy()
    expect(LEGENDA_MARCADOR).not.toMatch(/[—–]/)
  })
})
