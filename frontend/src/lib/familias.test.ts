// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { familiasV6Primeiro, nomesFamilias } from './familias'

describe('familias (D6: IPv6 antes de IPv4)', () => {
  it('reordena v4/v6 em qualquer grafia', () => {
    expect(familiasV6Primeiro(['v4', 'v6'])).toEqual(['v6', 'v4'])
    expect(familiasV6Primeiro(['IPv4', 'IPv6'])).toEqual(['IPv6', 'IPv4'])
    expect(familiasV6Primeiro(['v6'])).toEqual(['v6'])
  })
  it('monta o rótulo', () => {
    expect(nomesFamilias(['v4', 'v6'])).toBe('IPv6 e IPv4')
    expect(nomesFamilias(['v4', 'v6'], ' ')).toBe('IPv6 IPv4')
    expect(nomesFamilias(['ipv4'])).toBe('IPv4')
  })
})
