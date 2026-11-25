// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { mercadoNoRaio, outorgasSemDeclaracaoNoRaio } from './calculos'
import { BlocoMercado } from './BlocoMercado'
import type { MunicipioSici, ScmGeoFeature } from './tipos'

const mun = (ibge: string, ops: [string, number][]): MunicipioSici => ({
  ibge, nome: `M${ibge}`, uf: 'CE', lat: 0, lon: 0, acessos: ops.reduce((t, o) => t + o[1], 0), operadores: ops.map(([cnpj, acessos]) => ({ cnpj, empresa: `E${cnpj}`, acessos })),
})
const scm = (cnpj: string, sici_ativo?: boolean): ScmGeoFeature => ({ geometry: { coordinates: [0, 0] }, properties: { cnpj, razao_social: cnpj, has_asn: false, asns: [], sici_ativo } })

describe('mercado de banda larga fixa no raio (PT-26 / localizador 5.4)', () => {
  it('participação e HHI sobre os acessos declarados nos municípios do raio; soma 100%', () => {
    const r = mercadoNoRaio([mun('1', [['A', 600], ['B', 200]]), mun('2', [['A', 100], ['C', 100]])])!
    expect(r.acessos).toBe(1000)
    expect(r.operadoras).toBe(3)
    expect(r.linhas.map(l => [l.cnpj, l.acessos, l.municipios])).toEqual([['A', 700, 2], ['B', 200, 1], ['C', 100, 1]])
    expect(r.maiorParticipacao).toBe(70)
    expect(r.hhi).toBe(Math.round(70 ** 2 + 20 ** 2 + 10 ** 2))              // 5.400
    expect(r.linhas.reduce((t, l) => t + l.participacao, 0)).toBeCloseTo(100, 9)
  })

  it('raio sem acessos declarados: nenhum número', () => {
    expect(mercadoNoRaio([])).toBeNull()
    expect(mercadoNoRaio([mun('1', [])])).toBeNull()
  })

  it('outorgas sem declaração: só conta quem traz sici_ativo falso; snapshot antigo (sem o campo) não afirma nada', () => {
    expect(outorgasSemDeclaracaoNoRaio([scm('1', false), scm('1', false), scm('2', true), scm('3')])).toEqual({ total: 4, semDeclaracao: 2, cnpjsSemDeclaracao: 1 })
  })

  it('bloco: mês e regra à vista, faixa do projeto, só contagem de sem declaração e a norma vigente', () => {
    const mercado = mercadoNoRaio([mun('1', [['A', 600], ['B', 400]])])!
    render(<MemoryRouter><BlocoMercado mercado={mercado} mesReferencia="2026-09" snapshot="2026-11-22" outorgas={{ total: 5, semDeclaracao: 2 }} /></MemoryRouter>)
    const t = screen.getByTestId('localizador-mercado').textContent ?? ''
    expect(t).toMatch(/mês 2026-09; snapshot 2026-11-22/)
    expect(t).toMatch(/Regra: participação = acessos declarados pelo CNPJ nos municípios cujo centro está no raio/)
    expect(t).toMatch(/HHI do raio5\.200 \(HHI de 2\.500 ou mais\)/)
    expect(t).toMatch(/Outorgas SCM com sede no raio: 5; sem acessos declarados em 2026-09: 2/)
    expect(t).toMatch(/Resolução Anatel nº 774\/2025/)
    expect(t).toMatch(/método do projeto/)
    expect(screen.getByRole('link', { name: 'EA' })).toHaveAttribute('href', '/operadora/A')
    expect(t).not.toMatch(/omi[s]s|irregular|infra[çc]/i)
  })
})
