// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { MAX_LINHAS, quemAtende } from './quemAtende'
import type { Regiao, SiciOperador } from '../../types/api'

const op = (cnpj: string, empresa: string, acessos: number, asns: number[] = []): SiciOperador => ({ cnpj, empresa, acessos, share: 0, asns })
const prov = (asn: number, diretos: string[], indiretos: string[] = [], nome = `Nome AS${asn}`) =>
  ({ asn, nome, vinculos: ['sici' as const], acessos_fixo: 0, acessos_movel: 0, prefixos_geo: 0, ptts_diretos: diretos, ptts_indiretos: indiretos })
const regiao = (provedores: ReturnType<typeof prov>[], total = provedores.length) => ({ provedores, provedores_total: total, ptts_nomes: {} }) as unknown as Regiao

// Parintins sintético: soma 9.658
const OPS = [
  op('3', 'COELHO TECNOLOGIA', 1239, [264525, 264526]),
  op('1', 'CLICK IP', 6076),
  op('2', 'STARLINK', 1633),
  op('4', 'Nenhum Informado', 365, [265052]),
  op('5', 'TELEFONICA', 5, [10, 11, 12]),
  op('6', 'Pequena A', 137),
  op('7', 'Pequena B', 200),
  op('8', 'Mínima', 3),
]
const REG = regiao([
  prov(264525, ['bel', 'ce'], ['pr']), prov(264526, ['sp', 'df'], ['rj', 'ce']), prov(265052, [], ['ba', 'ce'], 'RN TELECOM LTDA'),
  prov(10, []), prov(11, []), prov(12, []),
])

describe('quemAtende (PT-26, município 5.2)', () => {
  it('ordena por acessos, a soma das linhas e do Demais fecha com o total e cada CNPJ aparece uma vez', () => {
    const q = quemAtende(OPS, REG)
    expect(q.total).toBe(9658)
    const nominais = q.linhas.map((l) => l.cnpj)
    expect(nominais).toEqual(['1', '2', '3', '4', '7', '6'])
    expect(q.demais!.n).toBe(2)
    expect(q.linhas.reduce((t, l) => t + l.acessos, 0) + q.demais!.acessos).toBe(9658)
    expect(q.linhas.reduce((t, l) => t + l.share, 0) + q.demais!.share).toBeCloseTo(100, 6)
    expect(new Set(q.linhas.map((l) => l.cnpj)).size).toBe(q.linhas.length)
  })

  it('operadora de vários ASNs soma os PTTs uma vez e a parcela é do CNPJ', () => {
    const q = quemAtende(OPS, REG)
    const coelho = q.linhas.find((l) => l.cnpj === '3')!
    expect(coelho.asns).toEqual([264525, 264526])
    expect(coelho.diretos).toEqual(['bel', 'ce', 'df', 'sp'])
    // 'ce' é direto em um ASN e indireto no outro: não repete como indireto
    expect(coelho.indiretos).toEqual(['pr', 'rj'])
    expect(coelho.situacao).toBe('direta')
    expect(q.linhas.filter((l) => l.cnpj === '3')).toHaveLength(1)
  })

  it('CNPJ sem ASN aparece, com situação própria e sem leitura de PTT', () => {
    const q = quemAtende(OPS, REG)
    const click = q.linhas[0]
    expect(click.nome).toBe('CLICK IP')
    expect(click.asns).toEqual([])
    expect(click.situacao).toBe('sem_asn')
    expect(click.share).toBeCloseTo((6076 / 9658) * 100, 6)
  })

  it('"Nenhum Informado" usa o nome do ASN; sem ASN, mostra que não há nome', () => {
    const q = quemAtende([...OPS, op('9', 'nenhum informado', 50), op('8', '', 40)], REG)
    const rn = q.linhas.find((l) => l.cnpj === '4')!
    expect(rn.nome).toBe('RN TELECOM LTDA')
    expect(rn.nomeDoAsn).toBe(true)
    expect(rn.situacao).toBe('so_indireta')
    const sem = [...q.linhas, ...(q.demais?.linhas ?? [])].find((l) => l.cnpj === '9')!
    expect(sem.semNome).toBe(true)
    expect(sem.nome).toBe('')
  })

  it('indicadores: ASN ligado contém sessão direta e só indireto; operadora com ASN e sem PTT fica na diferença', () => {
    const q = quemAtende(OPS, REG)
    expect(q.pctComAsn).toBeCloseTo(((1239 + 365 + 5) / 9658) * 100, 6)
    expect(q.pctDireta).toBeCloseTo((1239 / 9658) * 100, 6)
    expect(q.pctSoIndireta).toBeCloseTo((365 / 9658) * 100, 6)
    expect(q.pctDireta + q.pctSoIndireta).toBeLessThan(q.pctComAsn)
    expect(q.demais!.linhas.map((l) => l.cnpj)).toContain('5')
  })

  it('operadoras pequenas viram "Demais (N)" e a soma ainda fecha', () => {
    const muitas = [op('1', 'Grande', 10000, [1]), ...Array.from({ length: 12 }, (_, i) => op(`1${i}`, `Pequena ${i}`, 10 + i, i % 2 ? [100 + i] : []))]
    const reg = regiao(muitas.slice(1).filter((o) => o.asns.length).map((o) => prov(o.asns[0], ['sp'])))
    const q = quemAtende(muitas, reg)
    expect(q.linhas.map((l) => l.cnpj)).toEqual(['1'])
    expect(q.demais!.n).toBe(12)
    expect(q.demais!.acessos + q.linhas.reduce((t, l) => t + l.acessos, 0)).toBe(q.total)
    expect(q.demais!.share + q.linhas.reduce((t, l) => t + l.share, 0)).toBeCloseTo(100, 6)
    expect(q.demais!.comAsn).toBe(6)
    expect(q.demais!.comSessaoDireta).toBe(6)
    expect(q.demais!.linhas).toHaveLength(12)
  })

  it('no máximo MAX_LINHAS nominais, mesmo com todas acima do corte', () => {
    const ops = Array.from({ length: MAX_LINHAS + 3 }, (_, i) => op(`${i}`, `Op ${i}`, 100 - i))
    const q = quemAtende(ops, REG)
    expect(q.linhas).toHaveLength(MAX_LINHAS)
    expect(q.demais!.n).toBe(3)
  })

  it('uma única operadora abaixo do corte aparece com o nome, sem "Demais (1)"', () => {
    const q = quemAtende([op('1', 'Grande', 10000), op('2', 'Mínima', 1)], REG)
    expect(q.demais).toBeNull()
    expect(q.linhas.map((l) => l.cnpj)).toEqual(['1', '2'])
  })

  it('município com uma operadora e operadora com ASN e nenhum PTT', () => {
    const q = quemAtende([op('1', 'Única', 7, [10])], REG)
    expect(q.linhas).toHaveLength(1)
    expect(q.linhas[0].situacao).toBe('sem_ptt')
    expect(q.pctComAsn).toBe(100)
    expect(q.pctDireta).toBe(0)
    expect(q.pctSoIndireta).toBe(0)
  })

  it('lista de provedores cortada: ASN fora dela é "indeterminada", não "sem PTT"', () => {
    const q = quemAtende([op('1', 'X', 10, [999])], regiao([prov(10, [])], 300))
    expect(q.linhas[0].situacao).toBe('indeterminada')
    expect(q.listaCortada).toBe(true)
    expect(q.indeterminadas).toBe(1)
  })

  it('sem operadores ou sem a região, não quebra', () => {
    expect(quemAtende([], REG).total).toBe(0)
    expect(quemAtende([], REG).pctComAsn).toBe(0)
    expect(quemAtende([op('1', 'X', 5, [10])], null).linhas[0].situacao).toBe('indeterminada')
  })

  it('marca só quando o CNPJ está numa mudança de CNPJ provável', () => {
    const q = quemAtende([op('1', 'Ligga', 100), op('2', 'Ligga S.A.', 90), op('3', 'Outra', 80)], REG, [{ marca: 'Ligga', de_cnpj: '1', para_cnpj: '2' }])
    expect(q.linhas.map((l) => l.marca)).toEqual(['Ligga', 'Ligga', undefined])
  })
})
