// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Síntese do PTT (PT-22, ixp 5.4): sp na frente, ap no fim, empates, família sem coleta e nada de "maior" ou "mais importante". */
import { describe, expect, it } from 'vitest'
import { PALAVRAS_PROIBIDAS } from '../../lib/sintese'
import type { PttCtx } from './contexto'
import { posicaoEntrePtts, sinteseIxp } from './sinteseIxp'

const lista = [
  { code: 'sp', asn_direct_union_count: 2251 }, { code: 'ce', asn_direct_union_count: 927 }, { code: 'fec', asn_direct_union_count: 40 },
  { code: 'cac', asn_direct_union_count: 40 }, { code: 'lda', asn_direct_union_count: 40 }, { code: 'ap', asn_direct_union_count: 2 }, { code: 'xx' },
] as never[]
const ok = { coleta: 'ok', total_routes: 10 }
const ctx = (code: string, over: Partial<PttCtx> = {}): PttCtx => ({
  code, date: '2026-11-22', ixp: { name: 'x', v4: ok, v6: ok }, par: 52, dir: 40, brOriginUnion: 33, estUsers: { estimated_users: 1234567 }, ...over,
} as unknown as PttCtx)

describe('posicaoEntrePtts', () => {
  it('sp tem 0 PTTs com mais; ap tem todos os outros medidos com mais; PTT sem número fica de fora da conta', () => {
    expect(posicaoEntrePtts('sp', lista)).toEqual({ mais: 0, empate: 0, de: 6 })
    expect(posicaoEntrePtts('ap', lista)).toEqual({ mais: 5, empate: 0, de: 6 })
    expect(posicaoEntrePtts('xx', lista)).toBeNull()
    expect(posicaoEntrePtts('sp', undefined)).toBeNull()
  })
  it('empate: fec, cac e lda (40 diretos) têm 2 PTTs com o mesmo número e 2 com mais', () => {
    expect(posicaoEntrePtts('fec', lista)).toEqual({ mais: 2, empate: 2, de: 6 })
  })
})

describe('sinteseIxp', () => {
  it('cadastro, posição, usuários estimados e origem, com selo, fonte e data', () => {
    const f = sinteseIxp(ctx('fec'), 'Feira de Santana', lista)
    expect(f.map((x) => x.id)).toEqual(['cadastro', 'posicao', 'usuarios', 'origem'])
    expect(f[0].texto).toBe('O IX.br Feira de Santana tem 52 ASNs no cadastro de participantes e 40 com sessão em route server (união IPv6 e IPv4).')
    expect(f[1].texto).toBe('2 PTTs do IX.br têm mais ASNs em sessão direta, entre 6 com coleta; 2 têm o mesmo número.')
    expect(f[2].selo).toBe('estimado')
    expect(f[2].texto).toContain('1,2 mi')
    for (const x of f) { expect(x.fonte).not.toBe(''); expect(x.dataRef).toBe('2026-11-22'); expect(x.texto).not.toMatch(PALAVRAS_PROIBIDAS); expect(x.texto).not.toMatch(/maior|mais importante/i) }
    expect(sinteseIxp(ctx('sp'), 'São Paulo', lista).find((x) => x.id === 'posicao')!.texto).toMatch(/^Nenhum PTT do IX\.br tem mais ASNs/)
  })

  it('família sem coleta gera a frase de coleta, nunca "0 participantes"', () => {
    const f = sinteseIxp(ctx('fec', { ixp: { v4: ok, v6: { coleta: 'vazia', total_routes: 0 } } as never }), 'Feira de Santana', lista)
    const c = f.find((x) => x.id === 'coleta')!
    expect(c.texto).toContain('não trouxe rotas IPv6')
    expect(f.every((x) => !/\b0 (ASNs|participantes)/.test(x.texto))).toBe(true)
  })

  it('sem lista de PTTs não há frase de posição; sem número nenhum a síntese some', () => {
    expect(sinteseIxp(ctx('fec'), 'x', undefined).some((x) => x.id === 'posicao')).toBe(false)
    expect(sinteseIxp(ctx('fec', { par: null, dir: null, brOriginUnion: null, estUsers: undefined }), 'x', undefined)).toEqual([])
  })
})
