// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { asnValido, codigoPttValido } from './identificadores'

describe('identificadores de rota', () => {
  it('ASN: inteiro de 1 a 4294967295', () => {
    for (const ok of ['1', '28573', 4294967295, '4294967295']) expect(asnValido(ok), String(ok)).toBe(true)
    for (const ruim of ['abc', '0', '4294967296', '-1', '01', ' 1', '1.5', '', undefined]) expect(asnValido(ruim), String(ruim)).toBe(false)
  })
  it('código de PTT: minúsculas, dígitos e hífen', () => {
    for (const ok of ['sp', 'equinix-sp', 'ams-ix', 'xx-inexistente']) expect(codigoPttValido(ok)).toBe(true)
    for (const ruim of ['SP', '-sp', 'a/b', '..', '', undefined, 'x'.repeat(65)]) expect(codigoPttValido(ruim)).toBe(false)
  })
})
