// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Posição do PTT entre os do IX.br (PT-22 / ixp 5.4): maior valor é 1, empate divide a posição, família sem coleta não vira zero. */
import { describe, expect, it } from 'vitest'
import { outrosPttsNaUf, posicaoEntrePttsDoIxbr } from './posicaoPtt'

const afi = (diretos: number, rotas = 10) => ({ coleta: rotas ? 'ok' : 'vazia', total_routes: rotas, asn_direct_count: diretos }) as never
const p = (code: string, uf: string, membros: number, uniao: number, v6: unknown, v4: unknown) =>
  ({ code, name: code.toUpperCase(), uf, status: 'ok', ixbr_members_count: membros, asn_direct_union_count: uniao, v6, v4 }) as never
const todos = [
  p('sp', 'SP', 2400, 2251, afi(1500), afi(2000)),
  p('fec', 'BA', 52, 40, { missing: true }, afi(40)),
  p('ba', 'BA', 100, 90, afi(60), afi(80)),
  p('cac', 'PR', 45, 40, afi(30), afi(40)),
  p('ap', 'AP', 3, 2, afi(0, 0), afi(2)),
]

describe('posicaoEntrePttsDoIxbr', () => {
  it('sp em 1º e ap em último na sessão direta', () => {
    expect(posicaoEntrePttsDoIxbr('sp', todos).find((l) => l.id === 'diretos')).toMatchObject({ valor: 2251, posicao: 1, de: 5 })
    expect(posicaoEntrePttsDoIxbr('ap', todos).find((l) => l.id === 'diretos')).toMatchObject({ valor: 2, posicao: 5, de: 5 })
  })

  it('empate divide a posição e a mediana é a dos PTTs com a medida', () => {
    const fec = posicaoEntrePttsDoIxbr('fec', todos).find((l) => l.id === 'diretos')!
    const cac = posicaoEntrePttsDoIxbr('cac', todos).find((l) => l.id === 'diretos')!
    expect(fec.posicao).toBe(3)
    expect(cac.posicao).toBe(3)
    expect(fec.mediana).toBe(40)
  })

  it('família sem coleta ou vazia fica sem valor e fora da mediana, nunca zero', () => {
    const v6fec = posicaoEntrePttsDoIxbr('fec', todos).find((l) => l.id === 'diretos-v6')!
    expect(v6fec.valor).toBeNull()
    expect(v6fec.posicao).toBeNull()
    expect(v6fec.de).toBe(3)                        // sp, ba, cac (ap tem v6 vazia)
    expect(posicaoEntrePttsDoIxbr('ap', todos).find((l) => l.id === 'diretos-v6')!.valor).toBeNull()
  })

  it('IPv6 vem antes de IPv4 e PTT desconhecido ou lista ausente não gera linhas', () => {
    expect(posicaoEntrePttsDoIxbr('sp', todos).map((l) => l.id)).toEqual(['membros', 'diretos', 'diretos-v6', 'diretos-v4'])
    expect(posicaoEntrePttsDoIxbr('xx', todos)).toEqual([])
    expect(posicaoEntrePttsDoIxbr('sp', undefined)).toEqual([])
  })
})

describe('outrosPttsNaUf', () => {
  it('lista os outros PTTs da UF em ordem de código', () => {
    expect(outrosPttsNaUf('fec', 'BA', todos).map((i) => i.code)).toEqual(['ba'])
    expect(outrosPttsNaUf('sp', 'SP', todos)).toEqual([])
    expect(outrosPttsNaUf('sp', undefined, todos)).toEqual([])
  })
})
