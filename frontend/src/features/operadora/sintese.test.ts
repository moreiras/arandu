// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Síntese da operadora: regras fixas, selo por frase, nada sem dado, nada de veredito. */
import { describe, expect, it } from 'vitest'
import { kpisOperadora, REGRAS_VERSAO, sinteseOperadora } from './sintese'
import { derivarOperadora, type OperadoraCtx } from './contexto'
import { servicosDaOperadora } from './servicos'

const SCM = { servicos: [{ sigla: 'SCM', tipo: 'outorga', desde: '05/01/2021', registros: 1 }] }
const base = { cnpjFinal: '90000001000129', hasScm: true, hasSici: true, hasStfc: false, hasSeac: false, b2cPct: 71.5, ...SCM } as OperadoraCtx

describe('síntese da operadora', () => {
  it('monta as frases só com o que o snapshot tem, cada uma com selo', () => {
    const ctx = { ...base,
      data: { municipios: 12, asns: [64500, 64501] } as any,
      indicadores: { mes_referencia: '2026-08', metodologia: 'm', acessos: 12345, share_br: 0.42, posicao_br: 31, var_aa: { abs: 500, pct: 4.2 } } as any }
    const f = sinteseOperadora('Provedor 01', ctx)
    expect(f.map((x) => x.id)).toEqual(['outorgas', 'acessos', 'variacao', 'municipios', 'asns'])
    expect(f.find((x) => x.id === 'acessos')!.texto).toMatch(/12\.345 acessos .* 2026-08, 0,42% .* \(31º por acessos\)/)
    expect(f.every((x) => x.selo === 'fato')).toBe(true)
    expect(REGRAS_VERSAO).toBe('sintese-operadora-2')
  })

  it('sem indicadores nem municípios, não inventa frase', () => {
    const f = sinteseOperadora('X', { ...base, hasScm: false, hasSici: false, servicos: [] } as OperadoraCtx)
    expect(f.map((x) => x.id)).toEqual(['sem-outorga', 'asns'])
    expect(f[0].texto).toBe('Sem outorga registrada na Anatel neste snapshot.')
    expect(f[1].texto).toMatch(/Não tem ASN próprio/)
  })

  it('empresa com outorga SCM sem declaração diz só o fato e o mês', () => {
    const f = sinteseOperadora('X', { ...base, indicadores: { mes_referencia: '2026-08', metodologia: 'm', sem_declaracao: { razao_social: 'X', uf: 'SP', n_outorgas: 1, desde: null, asns: [], usuarios_apnic: null, classe: 'sem_usuarios' } } as any } as OperadoraCtx)
    expect(f.find((x) => x.id === 'sem-declaracao')!.texto).toBe('Tem outorga SCM, mas não declarou acessos ao SICI em 2026-08.')
  })

  it('indicadores sem valor não viram KPI vazio na ficha', () => {
    expect(kpisOperadora({ ...base } as OperadoraCtx).filter((k) => k.valor != null).map((k) => k.id)).toEqual(['asns'])
  })
})

/** Respostas do perfil como a API devolve (`/operadoras/{cnpj}`), reduzidas ao que a regra lê. */
const smpProprio = { cnpj: '1', razao_social: 'Movel SA', data_outorga: '10/03/2008', situacao: '' }
const smpCredenciada = { cnpj: '2', razao_social: 'MVNO SA', data_outorga: '', situacao: 'Credenciada de Rede Virtual (sem outorga SMP própria)',
  rede_virtual: { papel: 'credenciada' as const, prestadora_origem_cnpj: '07870094000184', prestadora_origem_nome: 'SURF TELECOM SA' } }
const scmRec = { cnpj: '2', razao_social: 'X', data_outorga: '05/01/2021' }
const frases = (f: Parameters<typeof derivarOperadora>[0], extra: Partial<OperadoraCtx> = {}) =>
  sinteseOperadora('Empresa', { cnpjFinal: '1', ...f, ...derivarOperadora(f), ...extra } as OperadoraCtx)

describe('servicosDaOperadora e sintese-operadora-2 (OPERADORA-E8, OPERADORA-E9, REL-E1, REL-E2, REL-E3)', () => {
  it('CNPJ só com ASN (documento móvel sem outorga): sem SMP na frase, no selo e no bloco (caso Vogel)', () => {
    const f = { data: { outorgas_scm: [scmRec] as any, acessos: 100, pf: 90 }, dataMovel: { asns: [64500, 64501, 64502], outorgas_smp: [] } }
    const d = derivarOperadora(f)
    expect(d.hasSmp).toBe(false)
    expect(d.servicos.map((s) => s.sigla)).toEqual(['SCM'])
    const out = frases(f).find((x) => x.id === 'outorgas')!.texto
    expect(out).toBe('Empresa tem outorga da Anatel para SCM.')
    expect(out).not.toMatch(/SMP/)
  })

  it('credenciada de rede virtual não tem outorga SMP: rótulo próprio com a prestadora de origem (casos Oi e Ampernet)', () => {
    const f = { data: { outorgas_scm: [scmRec] as any, acessos: 131209, pf: 121697 }, dataMovel: { asns: [], outorgas_smp: [smpCredenciada] as any }, dataStfc: { outorgas: [{ cnpj: '2' }] as any } }
    const d = derivarOperadora(f)
    expect(d.hasSmp).toBe(false)
    expect(d.servicos.find((s) => s.sigla === 'SMP')).toMatchObject({ tipo: 'credenciada', registros: 0, origem: { nome: 'SURF TELECOM SA' } })
    const fs = frases(f)
    expect(fs.find((x) => x.id === 'outorgas')!.texto).toBe('Empresa tem outorga da Anatel para SCM e STFC.')
    expect(fs.find((x) => x.id === 'rede-virtual')!.texto).toBe('No SMP, é credenciada de rede virtual de SURF TELECOM SA (sem outorga SMP própria).')
  })

  it('outorga SMP própria continua SMP, mesmo quando a empresa também é credenciada de outra (caso Algar)', () => {
    const s = servicosDaOperadora({ dataMovel: { outorgas_smp: [{ ...smpProprio, rede_virtual: smpCredenciada.rede_virtual }, { ...smpProprio, data_outorga: '01/02/1999' }] as any } })
    expect(s).toEqual([{ sigla: 'SMP', tipo: 'outorga', desde: '01/02/1999', registros: 2, origem: { cnpj: '07870094000184', nome: 'SURF TELECOM SA' } }])
  })

  it('objeto SCM presente sem registro de outorga não afirma outorga (caso Unilink)', () => {
    const f = { data: { outorgas_scm: [], acessos: 50, pf: 50 }, dataMovel: { asns: [64500], outorgas_smp: [] } }
    expect(derivarOperadora(f).hasScm).toBe(false)
    const fs = frases(f)
    expect(fs.find((x) => x.id === 'outorgas')).toBeUndefined()
    expect(fs.find((x) => x.id === 'sem-outorga')!.texto).toBe('Sem outorga registrada na Anatel neste snapshot.')
  })

  it('bordas: só SMP e só STFC', () => {
    expect(frases({ dataMovel: { outorgas_smp: [smpProprio] as any } }).find((x) => x.id === 'outorgas')!.texto).toBe('Empresa tem outorga da Anatel para SMP.')
    expect(frases({ dataStfc: { outorgas: [{ cnpj: '1' }] as any } }).find((x) => x.id === 'outorgas')!.texto).toBe('Empresa tem outorga da Anatel para STFC.')
  })

  it('B2C do relatório sai dos acessos declarados, não fixo em 0 (caso Ampernet: 121.697 de 131.209 = 92,75%, arredondado a uma casa)', () => {
    const f = { data: { outorgas_scm: [scmRec] as any, acessos: 131209, pf: 121697, municipios: 3 } }
    expect(derivarOperadora(f).b2cPct).toBeCloseTo(92.75, 2)
    expect(frases(f, { data: f.data as any }).find((x) => x.id === 'municipios')!.texto).toMatch(/92,8% dos acessos são de pessoa física/)
    expect(derivarOperadora({ data: { outorgas_scm: [], acessos: null } }).b2cPct).toBe(0)
  })
})
