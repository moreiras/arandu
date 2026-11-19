// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { formatarCnpj, rotulosRepetidos } from './marca'

describe('marca', () => {
  it('detecta rótulo repetido e formata CNPJ', () => {
    expect([...rotulosRepetidos(['CLARO', 'VIVO', 'CLARO', 'TIM'])]).toEqual(['CLARO'])
    expect(formatarCnpj('90000001000129')).toBe('90.000.001/0001-29')
    expect(formatarCnpj('abc')).toBe('abc')
  })
})
