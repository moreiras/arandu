// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { canonizarPrefixo, caminhoDoPrefixo, cobre, ehIp, ehPrefixo, parsePrefixo } from './prefixo'

describe('prefixo', () => {
  it('reconhece CIDR v4 e v6 bem formados e recusa o resto', () => {
    for (const ok of ['177.75.0.0/16', '0.0.0.0/0', '2804::/32', '2001:db8::/48', '2001:db8:0:0:0:0:0:1/128']) expect(ehPrefixo(ok), ok).toBe(true)
    for (const ruim of ['177.75.0.0', '177.75.0/16', '300.1.1.1/8', '1.2.3.4/33', '2001:db8::/129', 'AS8075', '', '2001::db8::1/64', 'g::/8']) expect(ehPrefixo(ruim), ruim).toBe(false)
  })

  it('cobre: mesmo bloco, mais específico, família diferente e vizinho', () => {
    expect(cobre('198.18.0.0/24', '198.18.0.0/24')).toBe(true)
    expect(cobre('198.18.0.0/16', '198.18.7.0/24')).toBe(true)
    expect(cobre('198.18.0.0/24', '198.18.0.0/16')).toBe(false)      // o mais específico não cobre o maior
    expect(cobre('198.19.0.0/16', '198.18.7.0/24')).toBe(false)
    expect(cobre('2001:db8::/32', '2001:db8:1::/48')).toBe(true)
    expect(cobre('2001:db8::/32', '198.18.0.0/24')).toBe(false)
    expect(cobre('0.0.0.0/0', '10.0.0.0/8')).toBe(true)
  })

  it('lê tamanho e família', () => {
    expect(parsePrefixo('2804::/32')).toMatchObject({ versao: 6, tamanho: 32, max: 128 })
    expect(parsePrefixo('177.75.0.0/16')).toMatchObject({ versao: 4, tamanho: 16, max: 32 })
  })

  it('forma canônica igual à do servidor (PFX-E5): zeros à esquerda, bits de host, compressão RFC 5952', () => {
    expect(canonizarPrefixo('2804:0000::/32')).toBe('2804::/32')
    expect(canonizarPrefixo('2001:0DB8:0000:0000:0000:0000:0000:0000/48')).toBe('2001:db8::/48')
    expect(canonizarPrefixo('2001:db8:0:1:0:0:0:0/64')).toBe('2001:db8:0:1::/64')
    expect(canonizarPrefixo('2001:db8:0:0:1:0:0:0/80')).toBe('2001:db8:0:0:1::/80')
    expect(canonizarPrefixo('2001:db8:1:1:1:1:0:1/128')).toBe('2001:db8:1:1:1:1:0:1/128')
    expect(canonizarPrefixo('::/0')).toBe('::/0')
    expect(canonizarPrefixo('200.192.97.0/21')).toBe('200.192.96.0/21')
    expect(canonizarPrefixo('177.75.0.0/20')).toBe('177.75.0.0/20')
    expect(canonizarPrefixo('abc')).toBeNull()
  })

  it('caminho mantém a barra do CIDR', () => {
    expect(caminhoDoPrefixo(' 177.75.0.0/16 ')).toBe('/prefixo/177.75.0.0/16')
  })
})

describe('ehIp', () => {
  it('aceita IPv4 e IPv6 sem máscara e recusa o resto', () => {
    for (const ok of ['177.75.0.1', '200.160.2.3', '2804::1', '2001:db8::1']) expect(ehIp(ok), ok).toBe(true)
    for (const ruim of ['177.75.0.0/16', '300.1.1.1', '1.2.3', 'AS8075', '', '8075', 'g::1']) expect(ehIp(ruim), ruim).toBe(false)
  })
})
