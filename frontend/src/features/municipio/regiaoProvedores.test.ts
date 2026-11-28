// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { agruparProvedores, avisoLimiteRegiao } from './regiaoProvedores'
import type { RegiaoProvedor } from '../../types/api'

const prov = (asn: number, o: Partial<RegiaoProvedor> = {}): RegiaoProvedor => ({
  asn, nome: `Nome AS${asn}`, cnpj: null, vinculos: ['sici'], acessos_fixo: 0, acessos_movel: 0, prefixos_geo: 0, ptts_diretos: [], ptts_indiretos: [], ...o,
})
const fmtKm = (k: number) => `${Math.round(k)} km`
const fmt = (n: number) => n.toLocaleString('pt-BR')

describe('agruparProvedores', () => {
  const telefonica = Array.from({ length: 13 }, (_, i) => prov(1000 + i, { cnpj: 'T', nome: 'TELEFONICA BRASIL S.A', acessos_fixo: 300000, acessos_movel: 89385, ptts_diretos: i === 0 ? ['sp'] : [], ptts_indiretos: i === 1 ? ['rj', 'sp'] : [] }))
  const todos = [
    ...telefonica,
    prov(2000, { cnpj: 'C', nome: 'CLARO S.A.', acessos_fixo: 485130, ptts_diretos: ['sp'] }),
    prov(2001, { cnpj: 'C', nome: 'Claro S.A. Embratel', acessos_fixo: 485130, vinculos: ['sici', 'geo'], prefixos_geo: 4, ptts_diretos: ['rj'] }),
    prov(2002, { cnpj: 'C', nome: 'CLARO S.A.', acessos_fixo: 485130, vinculos: ['geo'], prefixos_geo: 3 }),
    prov(3000, { nome: 'Sem CNPJ', vinculos: ['geo'], prefixos_geo: 10 }),
    prov(3001, { nome: 'Empresário individual (AS3001, CNPJ 12.345.678/****-**)', acessos_fixo: 50 }),
  ]
  const ag = agruparProvedores(todos)

  it('uma linha por CNPJ, com os acessos contados uma vez e todos os ASNs listados', () => {
    const t = ag.linhas.find((l) => l.cnpj === 'T')!
    expect(t.asns).toHaveLength(13)
    expect(t.acessos).toBe(389385)                                  // não 13 x 389385
    expect(ag.linhas.filter((l) => l.cnpj === 'T')).toHaveLength(1)
    expect(ag.linhas.reduce((n, l) => n + l.asns.length, 0)).toBe(todos.length)
    expect(ag.asns).toBe(18)
    expect(ag.operadoras).toBe(2)
    expect(ag.linhas).toHaveLength(2 + 2)
  })

  it('agrega as demais colunas: vínculo e PTT por união, prefixos por soma, indireto sem repetir o direto', () => {
    const c = ag.linhas.find((l) => l.cnpj === 'C')!
    expect(c.vinculos).toEqual(['sici', 'geo'])
    expect(c.prefixos).toBe(7)
    expect(c.diretos).toEqual(['rj', 'sp'])
    expect(c.acessos).toBe(485130)
    const t = ag.linhas.find((l) => l.cnpj === 'T')!
    expect(t.diretos).toEqual(['sp'])
    expect(t.indiretos).toEqual(['rj'])                              // 'sp' é direto em outro ASN da operadora
  })

  it('nome mais frequente entre os ASNs; empate fica com o do menor ASN', () => {
    expect(ag.linhas.find((l) => l.cnpj === 'C')!.nome).toBe('CLARO S.A.')
    const empate = agruparProvedores([prov(5, { cnpj: 'X', nome: 'B' }), prov(4, { cnpj: 'X', nome: 'A' })])
    expect(empate.linhas[0].nome).toBe('A')
  })

  it('ASN sem CNPJ e pessoa natural (sem cnpj na API) ficam em linha própria, sem juntar entre si', () => {
    const sem = ag.linhas.filter((l) => !l.cnpj)
    expect(sem.map((l) => l.asns[0].asn).sort()).toEqual([3000, 3001])
    expect(sem.every((l) => l.asns.length === 1)).toBe(true)
    expect(sem.find((l) => l.asns[0].asn === 3001)!.nome).toMatch(/^Empresário individual/)
  })

  it('ordena como a API: acessos, vínculos, prefixos, menor ASN', () => {
    expect(ag.linhas.map((l) => l.asns[0].asn)).toEqual([2000, 1000, 3001, 3000])
  })
})

describe('avisoLimiteRegiao', () => {
  it('diz que a região foi limitada quando o raio tem mais municípios que o teto', () => {
    const t = avisoLimiteRegiao({ cortado: true, dentroDoRaio: 202, raioKm: 245, raioEfetivoKm: 127.9, n: 50 }, fmtKm, fmt)!
    expect(t).toContain('245 km tem 202 municípios')
    expect(t).toContain('limitada aos 50 mais próximos, até 128 km')
  })
  it('sem corte (ou sem raio) não há aviso', () => {
    expect(avisoLimiteRegiao({ cortado: false, n: 30 }, fmtKm, fmt)).toBeNull()
    expect(avisoLimiteRegiao(undefined, fmtKm, fmt)).toBeNull()
  })
})
