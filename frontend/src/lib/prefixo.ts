// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
export interface PrefixoParseado { versao: 4 | 6; bits: bigint; tamanho: number; max: number }

function parseV4(s: string): bigint | null {
  const p = s.split('.')
  if (p.length !== 4) return null
  let n = 0n
  for (const x of p) {
    if (!/^\d{1,3}$/.test(x) || Number(x) > 255) return null
    n = (n << 8n) | BigInt(x)
  }
  return n
}

function parseV6(s: string): bigint | null {
  if (!/^[0-9a-fA-F:]+$/.test(s) || s.split('::').length > 2) return null
  const [cabeca, cauda] = s.split('::')
  const a = cabeca ? cabeca.split(':') : []
  const b = cauda !== undefined && cauda ? cauda.split(':') : []
  const faltam = 8 - a.length - b.length
  if (s.includes('::') ? faltam < 1 : faltam !== 0) return null
  const grupos = [...a, ...Array(s.includes('::') ? faltam : 0).fill('0'), ...b]
  if (grupos.length !== 8) return null
  let n = 0n
  for (const g of grupos) {
    if (!/^[0-9a-fA-F]{1,4}$/.test(g)) return null
    n = (n << 16n) | BigInt(parseInt(g, 16))
  }
  return n
}

/** Lê "a.b.c.d/n" ou "v6::/n". Devolve null se não for um prefixo bem formado. */
export function parsePrefixo(texto: string): PrefixoParseado | null {
  const m = /^([^/\s]+)\/(\d{1,3})$/.exec(texto.trim())
  if (!m) return null
  const tamanho = Number(m[2])
  const v6 = m[1].includes(':')
  const bits = v6 ? parseV6(m[1]) : parseV4(m[1])
  const max = v6 ? 128 : 32
  if (bits == null || tamanho > max) return null
  return { versao: v6 ? 6 : 4, bits, tamanho, max }
}

export function ehPrefixo(texto: string): boolean {
  return parsePrefixo(texto) !== null
}

/** Endereço IP solto (v4 ou v6, sem máscara): a página de prefixo resolve o prefixo mais específico que o contém. */
export function ehIp(texto: string): boolean {
  const t = texto.trim()
  return t.includes(':') ? parseV6(t) !== null : parseV4(t) !== null
}

/** `outer` cobre `inner` (mesma família, `outer` igual ou menos específico e com os mesmos bits iniciais). */
export function cobre(outer: string, inner: string): boolean {
  const o = parsePrefixo(outer)
  const i = parsePrefixo(inner)
  if (!o || !i || o.versao !== i.versao || o.tamanho > i.tamanho) return false
  const deslocar = BigInt(o.max - o.tamanho)
  return o.tamanho === 0 ? true : (o.bits >> deslocar) === (i.bits >> deslocar)
}

/** Caminho da página de um prefixo (a barra do CIDR fica como separador de rota, sem codificar). */
export function caminhoDoPrefixo(prefixo: string): string {
  return `/prefixo/${prefixo.trim()}`
}
