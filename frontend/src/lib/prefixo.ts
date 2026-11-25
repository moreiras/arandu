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

function v6Texto(n: bigint): string {
  const g = Array.from({ length: 8 }, (_, i) => Number((n >> BigInt(16 * (7 - i))) & 0xffffn))
  let ini = -1
  let tam = 0
  for (let i = 0; i < 8; ) {     // maior sequência de zeros com 2 ou mais grupos, a primeira em caso de empate (RFC 5952)
    if (g[i] !== 0) { i++; continue }
    let j = i
    while (j < 8 && g[j] === 0) j++
    if (j - i > tam && j - i > 1) { ini = i; tam = j - i }
    i = j
  }
  const hex = g.map((x) => x.toString(16))
  if (ini < 0) return hex.join(':')
  return `${hex.slice(0, ini).join(':')}::${hex.slice(ini + tam).join(':')}`
}

/** Forma canônica do prefixo (bits de host zerados, IPv6 comprimido em minúsculas, RFC 5952), a mesma de `ipaddress` no servidor; null se malformado. */
export function canonizarPrefixo(texto: string): string | null {
  const p = parsePrefixo(texto)
  if (!p) return null
  const host = (1n << BigInt(p.max - p.tamanho)) - 1n
  const rede = p.bits & ~host
  const end = p.versao === 4
    ? [24n, 16n, 8n, 0n].map((s) => String((rede >> s) & 0xffn)).join('.')
    : v6Texto(rede)
  return `${end}/${p.tamanho}`
}

/** Caminho da página de um prefixo (a barra do CIDR fica como separador de rota, sem codificar). */
export function caminhoDoPrefixo(prefixo: string): string {
  return `/prefixo/${prefixo.trim()}`
}
