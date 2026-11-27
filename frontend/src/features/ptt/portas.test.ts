// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { fmtPortas } from './portas'

describe('porta declarada no PeeringDB', () => {
  it('formata em G/M, agrupa as repetidas e marca a não informada', () => {
    expect(fmtPortas([100000])).toBe('100G')
    expect(fmtPortas([10000, 10000, 1000])).toBe('2× 10G + 1G')
    expect(fmtPortas([100])).toBe('100M')
    expect(fmtPortas([0])).toBe('não informada')
    expect(fmtPortas(undefined)).toBeNull()
  })
})
