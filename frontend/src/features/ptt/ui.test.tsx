// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useCountUp } from './ui'

const original = window.matchMedia
const media = (reduzir: boolean) => vi.fn().mockImplementation((q: string) => ({
  matches: reduzir && q.includes('reduce'), media: q, addEventListener() {}, removeEventListener() {},
}))
afterEach(() => { window.matchMedia = original; vi.restoreAllMocks() })

describe('useCountUp (PTT, IXP-E11)', () => {
  it('com prefers-reduced-motion: reduce mostra o número final, sem animar', () => {
    window.matchMedia = media(true)
    const raf = vi.spyOn(window, 'requestAnimationFrame')
    const { result } = renderHook(() => useCountUp(1234))
    expect(result.current).toBe(1234)
    expect(raf).not.toHaveBeenCalled()
  })

  it('sem a preferência, começa do zero e anima', () => {
    window.matchMedia = media(false)
    const raf = vi.spyOn(window, 'requestAnimationFrame')
    const { result } = renderHook(() => useCountUp(1234))
    expect(result.current).toBeLessThan(1234)
    expect(raf).toHaveBeenCalled()
  })
})
