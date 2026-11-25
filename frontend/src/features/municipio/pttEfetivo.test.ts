// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { pttsEfetivos } from './pttEfetivo'
import type { Regiao, SiciOperador } from '../../types/api'

const op = (cnpj: string, empresa: string, share: number, asns: number[]): SiciOperador => ({ cnpj, empresa, acessos: share * 100, share, asns })
const prov = (asn: number, diretos: string[]) => ({ asn, nome: `AS${asn}`, vinculos: ['sici' as const], acessos_fixo: 0, acessos_movel: 0, prefixos_geo: 0, ptts_diretos: diretos, ptts_indiretos: [] })
const regiao = (provedores: ReturnType<typeof prov>[], total = provedores.length) => ({ provedores, provedores_total: total, ptts_nomes: {} }) as unknown as Regiao

// Parintins/AM: o PTT mais próximo é mao, mas a operadora de 12,8% tem sessão em bel, ce, df e sp
const PARINTINS: [number, number] = [-56.7357, -2.6283]

describe('PTT efetivo do município (PT-25 / município 5.4)', () => {
  const operadores = [op('1', 'CLICK IP', 62.9, []), op('2', 'STARLINK', 16.9, []), op('3', 'Coelho', 12.8, [264525, 264526]), op('4', 'RN TELECOM', 3.8, [265052]), op('5', 'Womp', 0.5, [1])]
  const reg = regiao([prov(264525, ['bel', 'ce', 'df', 'sp']), prov(264526, ['sp']), prov(265052, []), prov(1, ['mao'])])

  it('só operadoras com 5% ou mais do fixo; o CNPJ com dois ASNs no mesmo PTT conta uma vez', () => {
    const r = pttsEfetivos(operadores, reg, PARINTINS)
    expect(r.linhas.map((l) => l.codigo).sort()).toEqual(['bel', 'ce', 'df', 'sp'])             // mao (Womp, 0,5%) fica de fora
    const sp = r.linhas.find((l) => l.codigo === 'sp')!
    expect(sp.operadoras).toHaveLength(1)
    expect(sp.parcelaFixo).toBeCloseTo(12.8, 9)
    expect(r.consideradas).toBe(3)
    expect(r.comSessaoDireta).toBe(1)
  })

  it('ordem pela distância em linha reta e parcela do fixo sem ASN ligado', () => {
    const r = pttsEfetivos(operadores, reg, PARINTINS)
    const kms = r.linhas.map((l) => l.km!)
    expect(kms).toEqual([...kms].sort((a, b) => a - b))
    expect(r.linhas[0].codigo).toBe('bel')
    expect(r.semAsnPct).toBeCloseTo(79.8, 9)
  })

  it('bordas: nenhuma com sessão direta; sem centróide; lista de provedores cortada', () => {
    const sem = pttsEfetivos(operadores, regiao([prov(264525, [])], 40), PARINTINS)
    expect(sem.linhas).toEqual([])
    expect(sem.listaCortada).toBe(true)
    expect(pttsEfetivos(operadores, reg, undefined).linhas.every((l) => l.km === null)).toBe(true)
    expect(pttsEfetivos([], reg, PARINTINS)).toMatchObject({ linhas: [], semAsnPct: 0, consideradas: 0 })
  })
})
