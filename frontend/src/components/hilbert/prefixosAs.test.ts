// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { cellIndexToV6Prefix, V6_BLOCKS } from './hilbert'
import { intervaloV4, intervaloV6, rotuloQuadranteV6, semCobertura } from './prefixosAs'

describe('intervalo de células de um prefixo', () => {
  it('IPv4: /24 marca o /16 que o contém; /16 é uma célula; mais curto cobre todas', () => {
    expect(intervaloV4('198.18.5.0/24')).toEqual({ bloco: 'v4', ini: (198 << 8) | 18, fim: (198 << 8) | 19 })
    expect(intervaloV4('200.160.0.0/16')).toEqual({ bloco: 'v4', ini: (200 << 8) | 160, fim: (200 << 8) | 161 })
    expect(intervaloV4('177.0.0.0/8')).toEqual({ bloco: 'v4', ini: 177 << 8, fim: 178 << 8 })
    expect(intervaloV4('200.160.0.0/12')).toEqual({ bloco: 'v4', ini: (200 << 8) | 160, fim: (200 << 8) | 176 })
    expect(intervaloV4('lixo')).toBeNull()
  })

  it('IPv6: /32 é uma célula; /29 cobre 8; /48 marca o /32; fora dos blocos de RIR é null; ida e volta com cellIndexToV6Prefix', () => {
    const lacnic = V6_BLOCKS.find((b) => b.id === 'lacnic')!
    const um = intervaloV6('2804:1234::/32')!
    expect(um.bloco).toBe('lacnic')
    expect(um.fim - um.ini).toBe(1)
    expect(cellIndexToV6Prefix(um.ini, lacnic)).toBe('2804:1234::/32')
    expect(intervaloV6('2804:1234:abcd::/48')).toEqual(um)
    const ampla = intervaloV6('2804:1230::/29')!
    expect(ampla.fim - ampla.ini).toBe(8)
    expect(ampla.ini).toBe(intervaloV6('2804:1230::/32')!.ini)
    expect(intervaloV6('2001:db8::/32')).toEqual({ bloco: 'legacy', ini: 0xdb8, fim: 0xdb9 })
    expect(intervaloV6('3000::/32')).toBeNull()
    expect(intervaloV6('2800::/8')).toBeNull()
    expect(intervaloV6('2800::/12')!.fim - intervaloV6('2800::/12')!.ini).toBe(1 << 20)
  })

  it('rótulo do quadrante /20', () => {
    const lacnic = V6_BLOCKS.find((b) => b.id === 'lacnic')!
    expect(rotuloQuadranteV6(lacnic, intervaloV6('2804:1234::/32')!.ini >> 12)).toBe('2804:1000::/20')
  })
})

describe('semCobertura', () => {
  it('tira o que está dentro de um prefixo alocado, mantém o resto', () => {
    expect(semCobertura(['198.18.0.0/24', '198.19.0.0/24', '198.18.0.0/16'], ['198.18.0.0/16'])).toEqual(['198.19.0.0/24'])
    expect(semCobertura(['2001:db8:1::/48', '2001:db9::/32', '2001:db8::/32'], ['2001:db8::/32'])).toEqual(['2001:db9::/32'])
  })
  it('não confunde famílias nem prefixo mais curto com cobertura', () => {
    expect(semCobertura(['10.0.0.0/8'], ['10.0.0.0/24'])).toEqual(['10.0.0.0/8'])
    expect(semCobertura(['2001:db8::/32'], ['32.1.0.0/16'])).toEqual(['2001:db8::/32'])
  })
})
