// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import type { PerfilMunicipio } from '../../types/api'
import { agregarMunicipios } from './agregado'

const op = (cnpj: string, empresa: string, acessos: number, asns: number[] = []) => ({ cnpj, empresa, acessos, asns, share: 0 })
const perfil = (ibge: string, nome: string, extra: Partial<PerfilMunicipio> = {}): PerfilMunicipio => ({ snapshot_date: '2026-11-02', ibge, nome, uf: 'ES', ...extra })
const fixoDe = (operadores: ReturnType<typeof op>[], extra = {}) => {
  const acessos = operadores.reduce((t, o) => t + o.acessos, 0)
  return { mes_referencia: '2026-09', acessos, pf: Math.round(acessos * 0.8), pj: acessos - Math.round(acessos * 0.8), capacidade_mbps: 1, operadores, operadores_count: operadores.length, hhi: 0, share_maior: 0, ...extra }
}

describe('agregarMunicipios', () => {
  const a = perfil('1', 'Alfa', { fixo: fixoDe([op('A', 'Fibra A', 600, [65001]), op('B', 'Rede B', 400)], { fibra: 500 }), territorio: { populacao: 1000, domicilios: 400, domicilios_projetados: 400, acessos: 1000, acessos_pf: 800, nao_visto: 0, nao_visto_pct: 0 } as never })
  const b = perfil('2', 'Beta', { fixo: fixoDe([op('A', 'Fibra A', 100, [65001, 65002]), op('C', 'Rede C', 300)], { fibra: 100 }), territorio: { populacao: 500, domicilios: 200, domicilios_projetados: 200, acessos: 400, acessos_pf: 320, nao_visto: 50, nao_visto_pct: 0.25 } as never })

  it('soma os acessos e junta as operadoras por CNPJ com a participação sobre o total do conjunto', () => {
    const r = agregarMunicipios([a, b])!
    expect(r.fixo!.acessos).toBe(1400)
    expect(r.fixo!.pf).toBe(1120)
    expect(r.fixo!.nome).toBe('2 municípios')
    expect(r.fixo!.operadores.map((o) => [o.cnpj, o.acessos, o.share])).toEqual([['A', 700, 50], ['B', 400, 28.6], ['C', 300, 21.4]])
    expect(r.fixo!.operadores[0].asns).toEqual([65001, 65002])
    expect(r.fixo!.operadores_count).toBe(3)
    expect(r.fixo!.share_maior).toBe(50)
    // HHI do mercado junto: 50² + 28,57² + 21,43² = 3775,5
    expect(r.fixo!.hhi).toBe(3776)
    expect(r.fixo!.fibra).toBe(600)
    expect(r.fixo!.fibra_pct).toBe(42.9)
  })

  it('penetração, não visto e população são refeitos sobre o conjunto, sem distância ao PTT', () => {
    const t = agregarMunicipios([a, b])!.territorio!
    expect(t.populacao).toBe(1500)
    expect(t.domicilios_projetados).toBe(600)
    expect(t.penetracao).toBeCloseTo(1400 / 600, 9)      // razão das somas, não a média das razões
    expect(t.nao_visto).toBe(50)
    expect(t.nao_visto_pct).toBeCloseTo(50 / 600, 9)
    expect(t.km_ptt).toBeUndefined()
    expect(t.nome).toBe('2 municípios')
  })

  it('município sem perfil não contribui e o rótulo conta só os que contribuem', () => {
    const r = agregarMunicipios([a, null, undefined])!
    expect(r.fixo!.acessos).toBe(1000)
    expect(r.fixo!.nome).toBe('1 município')
    expect(agregarMunicipios([null, undefined])).toBeNull()
  })

  it('móvel soma e junta operadoras; sem móvel em nenhum, fica ausente', () => {
    const m1 = perfil('1', 'Alfa', { movel: { mes_referencia: '2026-09', acessos: 10, pf: 8, pj: 2, operadores: [op('M', 'Móvel', 10)], operadores_count: 1, hhi: 10000, share_maior: 100 } })
    const m2 = perfil('2', 'Beta', { movel: { mes_referencia: '2026-09', acessos: 30, pf: 20, pj: 10, operadores: [op('M', 'Móvel', 20), op('N', 'Outra', 10)], operadores_count: 2, hhi: 0, share_maior: 0 } })
    const r = agregarMunicipios([m1, m2])!
    expect(r.movel!.acessos).toBe(40)
    expect(r.movel!.operadores.map((o) => [o.cnpj, o.share])).toEqual([['M', 75], ['N', 25]])
    expect(agregarMunicipios([a])!.movel).toBeUndefined()
  })

  it('variação do conjunto é refeita pelos acessos de antes, não pela média das variações', () => {
    const ind = (acessos: number, var_aa_pct: number | null) => ({ mes_referencia: '2026-09', metodologia: 'm', acessos, n_operadoras: 1, hhi: 0, var_mm_pct: null, var_aa_pct })
    const i1 = perfil('1', 'Alfa', { ...a, indicadores: ind(1100, 10) })    // antes: 1000
    const i2 = perfil('2', 'Beta', { ...b, indicadores: ind(100, -50) })    // antes: 200
    const r = agregarMunicipios([i1, i2])!.indicadores!
    expect(r.acessos).toBe(1200)
    expect(r.var_aa_pct).toBe(0)                                            // 1200 contra 1200
    expect(r.var_mm_pct).toBeNull()
    expect(r.ganho_aa).toBeUndefined()
  })

  it('estações e FUST somam; por 10 mil habitantes só com população de todos; sem comparação com a UF', () => {
    const e = (estacoes: number, marca: string) => ({ natureza: 'n', fonte: 'f', data_arquivo: null, limites: 'l', snapshot_date: 's', estacoes, geracoes: { '2G': 0, '3G': 1, '4G': estacoes - 1, '5G': 0 }, por_10mil_hab: null, operadoras: [{ cnpj: null, marca, estacoes }], uf: 'ES', comparacao_uf: null, brasil: {} as never })
    const f = (compromissos: number) => ({ natureza: 'n', fonte: 'f', data_arquivo: null, limites: 'l', snapshot_date: 's', compromissos, atendidos: compromissos, a_vencer: 0, em_apuracao: 0, investimento: compromissos * 1000, programas: { P1: compromissos }, tipos: {}, uf: 'ES', comparacao_uf: null, programas_nomes: { P1: 'Programa' } })
    const r = agregarMunicipios([{ ...a, erbs: e(10, 'Vivo'), fust: f(2) }, { ...b, erbs: e(5, 'Vivo') }])!
    expect(r.erbs!.estacoes).toBe(15)
    expect(r.erbs!.geracoes['3G']).toBe(2)
    expect(r.erbs!.operadoras).toEqual([{ cnpj: null, marca: 'Vivo', estacoes: 15 }])
    expect(r.erbs!.por_10mil_hab).toBe(100)                                  // 15 estações para 1.500 habitantes
    expect(r.erbs!.comparacao_uf).toBeNull()
    expect(r.fust!.compromissos).toBe(2)
    expect(r.fust!.investimento).toBe(2000)
    expect(r.fust!.programas).toEqual({ P1: 2 })
    const semPop = agregarMunicipios([{ ...a, erbs: e(10, 'Vivo') }, perfil('3', 'Gama', { erbs: e(5, 'Vivo') })])!
    expect(semPop.erbs!.por_10mil_hab).toBeNull()
  })
})
