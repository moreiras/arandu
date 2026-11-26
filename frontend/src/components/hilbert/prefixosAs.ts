// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/**
 * Prefixos de um AS sobre a curva de Hilbert: funções puras, sem React.
 * IPv4 usa a grade de /16 (índice `a<<8|b`); IPv6 usa a de /32 de cada bloco de `V6_BLOCKS`.
 * Um prefixo mais curto que a célula ocupa todas as células que cobre; um mais longo marca a célula que o contém.
 */
import { V6_BLOCKS, type V6BlockConfig } from './hilbert'

/** Faixa de células [ini, fim) de um prefixo; `bloco` é 'v4' ou o id de `V6_BLOCKS`. */
export interface Intervalo { bloco: string; ini: number; fim: number }

interface Analisado { g: number[]; len: number; v6: boolean }

function analisarV4(p: string): Analisado | null {
  const [end, l] = p.split('/')
  const o = end.split('.').map(Number)
  const len = Number(l)
  if (o.length !== 4 || o.some((x) => !Number.isInteger(x) || x < 0 || x > 255) || !Number.isInteger(len) || len < 0 || len > 32) return null
  return { g: [(o[0] << 8) | o[1], (o[2] << 8) | o[3]], len, v6: false }
}

function analisarV6(p: string): Analisado | null {
  const [end, l] = p.split('/')
  const len = Number(l)
  if (!end || !Number.isInteger(len) || len < 0 || len > 128) return null
  const partes = end.split('::')
  if (partes.length > 2) return null
  const grupos = (s: string) => (s === '' ? [] : s.split(':'))
  const esq = grupos(partes[0])
  const dir = partes.length === 2 ? grupos(partes[1]) : []
  if (partes.length === 1 && esq.length !== 8) return null
  const falta = 8 - esq.length - dir.length
  if (falta < 0 || (partes.length === 2 && falta < 1)) return null
  const todos = [...esq, ...Array(falta).fill('0'), ...dir]
  const g = todos.map((x) => (/^[0-9a-f]{1,4}$/i.test(x) ? parseInt(x, 16) : NaN))
  return g.some(Number.isNaN) ? null : { g, len, v6: true }
}

function analisar(p: string): Analisado | null {
  return p.includes(':') ? analisarV6(p) : analisarV4(p)
}

/** Os primeiros `len` bits do prefixo, como texto: chave de comparação entre um prefixo e seus ancestrais. */
function chave(a: Analisado, len: number): string {
  const cheios = Math.floor(len / 16)
  const resto = len % 16
  const partes = a.g.slice(0, cheios).map((x) => x.toString(16))
  if (resto > 0) partes.push(((a.g[cheios] >> (16 - resto)) << (16 - resto)).toString(16))
  return `${a.v6 ? 6 : 4}/${len}/${partes.join(':')}`
}

/** Intervalo de /16 de um prefixo IPv4, ou null se não for um prefixo válido. */
export function intervaloV4(p: string): Intervalo | null {
  const a = analisarV4(p)
  if (!a) return null
  const base = a.g[0]
  if (a.len >= 16) return { bloco: 'v4', ini: base, fim: base + 1 }
  const n = 2 ** (16 - a.len)
  const ini = base - (base % n)
  return { bloco: 'v4', ini, fim: ini + n }
}

/** Bloco de `V6_BLOCKS` que contém o primeiro grupo de 16 bits, ou null (fora dos blocos de RIR mostrados). */
export function blocoV6(g1: number): V6BlockConfig | null {
  return V6_BLOCKS.find((b) => (b.baseLen === 16 ? g1 === b.baseG1 : (g1 & 0xfff0) === b.baseG1)) ?? null
}

/** Intervalo de /32 de um prefixo IPv6 dentro do bloco de RIR que o contém; null se estiver fora ou for mais curto que o bloco. */
export function intervaloV6(p: string): Intervalo | null {
  const a = analisarV6(p)
  if (!a) return null
  const cfg = blocoV6(a.g[0])
  if (!cfg || a.len < cfg.baseLen) return null
  const base = cfg.baseLen === 16 ? a.g[1] : ((a.g[0] & 0xf) << 16) | a.g[1]
  if (a.len >= 32) return { bloco: cfg.id, ini: base, fim: base + 1 }
  const n = 2 ** (32 - a.len)
  const ini = base - (base % n)
  return { bloco: cfg.id, ini, fim: ini + n }
}

export function intervaloDe(p: string): Intervalo | null {
  return p.includes(':') ? intervaloV6(p) : intervaloV4(p)
}

/** Prefixos de `candidatos` que NÃO estão contidos (nem são iguais) em algum de `cobertura`. Prefixo inválido é mantido. */
export function semCobertura(candidatos: string[], cobertura: string[]): string[] {
  const chaves = new Set<string>()
  const comprimentos = { 4: new Set<number>(), 6: new Set<number>() }
  for (const c of cobertura) {
    const a = analisar(c)
    if (!a) continue
    chaves.add(chave(a, a.len))
    comprimentos[a.v6 ? 6 : 4].add(a.len)
  }
  return candidatos.filter((p) => {
    const a = analisar(p)
    if (!a) return true
    for (const len of comprimentos[a.v6 ? 6 : 4]) {
      if (len <= a.len && chaves.has(chave(a, len))) return false
    }
    return true
  })
}

/** Verdadeiro se o intervalo cruza [ini, fim). */
export function cruza(a: Intervalo, ini: number, fim: number): boolean {
  return a.ini < fim && a.fim > ini
}

/** Rótulo do quadrante de 4096 células (64×64) de um bloco IPv6: um /20. */
export function rotuloQuadranteV6(cfg: V6BlockConfig, quad: number): string {
  const d = quad << 12
  const g1 = cfg.baseLen === 16 ? cfg.baseG1 : (cfg.baseG1 | (d >> 16)) & 0xffff
  return `${g1.toString(16)}:${(d & 0xffff).toString(16)}::/20`
}
