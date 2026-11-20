// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { asnValido, cnpjValido, codigoPttValido, idInstalacaoValido } from './identificadores'

describe('identificadores de rota', () => {
  it('ASN: inteiro de 1 a 4294967295', () => {
    for (const ok of ['1', '28573', 4294967295, '4294967295']) expect(asnValido(ok), String(ok)).toBe(true)
    for (const ruim of ['abc', '0', '4294967296', '-1', '01', ' 1', '1.5', '', undefined]) expect(asnValido(ruim), String(ruim)).toBe(false)
  })
  it('código de PTT: minúsculas, dígitos e hífen', () => {
    for (const ok of ['sp', 'equinix-sp', 'ams-ix', 'xx-inexistente']) expect(codigoPttValido(ok)).toBe(true)
    for (const ruim of ['SP', '-sp', 'a/b', '..', '', undefined, 'x'.repeat(65)]) expect(codigoPttValido(ruim)).toBe(false)
  })
  it('CNPJ: 14 dígitos, com ou sem formatação', () => {
    for (const ok of ['02558157000162', '02.558.157/0001-62']) expect(cnpjValido(ok), ok).toBe(true)
    for (const ruim of ['xyz', '0255815700016', '025581570001620', '', undefined]) expect(cnpjValido(ruim), String(ruim)).toBe(false)
  })
  it('instalação: inteiro positivo', () => {
    for (const ok of ['1', '99999999', 42]) expect(idInstalacaoValido(ok), String(ok)).toBe(true)
    for (const ruim of ['0', 'abc', '-1', '01', '', undefined]) expect(idInstalacaoValido(ruim), String(ruim)).toBe(false)
  })
})
