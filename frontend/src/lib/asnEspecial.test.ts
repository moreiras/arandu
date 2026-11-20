// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { asnEspecial } from './asnEspecial'

describe('asnEspecial', () => {
  it('reconhece privados, documentação e reservados', () => {
    expect(asnEspecial(65000)).toBe('ASN privado (RFC 6996)')
    expect(asnEspecial(4200000001)).toBe('ASN privado (RFC 6996)')
    expect(asnEspecial(64500)).toBe('ASN de documentação (RFC 5398)')
    expect(asnEspecial(23456)).toBe('AS_TRANS (RFC 6793)')
    expect(asnEspecial(0)).toBe('ASN reservado (RFC 7607)')
  })
  it('ASN público não é especial', () => {
    expect(asnEspecial(22548)).toBeNull()
    expect(asnEspecial(270382)).toBeNull()
  })
})
