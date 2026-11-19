// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { lembrarOrientacao, orientacaoPreferida, ORIENTACAO_NORTE, ORIENTACAO_SUL } from './orientacaoMapa'

function armazem() {
  const m = new Map<string, string>()
  return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v) }
}

describe('orientação do mapa', () => {
  it('o padrão é sul para cima', () => {
    expect(orientacaoPreferida(armazem())).toBe(ORIENTACAO_SUL)
  })
  it('lembra a escolha por norte e a desfaz', () => {
    const a = armazem()
    lembrarOrientacao(0, a)
    expect(orientacaoPreferida(a)).toBe(ORIENTACAO_NORTE)
    lembrarOrientacao(180, a)
    expect(orientacaoPreferida(a)).toBe(ORIENTACAO_SUL)
  })
  it('armazenamento que falha não quebra: volta ao padrão', () => {
    const quebrado = { getItem: () => { throw new Error('bloqueado') }, setItem: () => { throw new Error('bloqueado') } }
    expect(orientacaoPreferida(quebrado)).toBe(ORIENTACAO_SUL)
    expect(() => lembrarOrientacao(0, quebrado)).not.toThrow()
  })
})
