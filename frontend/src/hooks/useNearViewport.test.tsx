// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useNearViewport } from './useNearViewport'

let observadores: Array<{ cb: (e: Array<{ isIntersecting: boolean }>) => void; opts: IntersectionObserverInit; desligado: boolean }> = []

function Sonda() {
  const [ref, perto] = useNearViewport(500)
  return <div ref={ref} data-testid="sonda">{perto ? 'perto' : 'longe'}</div>
}

beforeEach(() => {
  observadores = []
  vi.stubGlobal('IntersectionObserver', class {
    rec: (typeof observadores)[number]
    constructor(cb: (e: Array<{ isIntersecting: boolean }>) => void, opts: IntersectionObserverInit) { this.rec = { cb, opts, desligado: false }; observadores.push(this.rec) }
    observe() {}
    disconnect() { this.rec.desligado = true }
  })
})
afterEach(() => vi.unstubAllGlobals())

describe('useNearViewport (1.4.2.4)', () => {
  it('começa longe, vira perto ao cruzar a margem e não volta atrás', () => {
    render(<Sonda />)
    expect(screen.getByTestId('sonda')).toHaveTextContent('longe')
    expect(observadores[0].opts.rootMargin).toBe('500px 0px')
    act(() => observadores[0].cb([{ isIntersecting: false }]))
    expect(screen.getByTestId('sonda')).toHaveTextContent('longe')
    act(() => observadores[0].cb([{ isIntersecting: true }]))
    expect(screen.getByTestId('sonda')).toHaveTextContent('perto')
    expect(observadores[0].desligado).toBe(true)
  })

  it('sem IntersectionObserver devolve perto de imediato (o dado nunca deixa de carregar)', () => {
    vi.unstubAllGlobals()
    vi.stubGlobal('IntersectionObserver', undefined)
    render(<Sonda />)
    expect(screen.getByTestId('sonda')).toHaveTextContent('perto')
  })
})
