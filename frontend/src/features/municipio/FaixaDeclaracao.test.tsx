// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { IndicadoresMunicipio } from '../../types/api'
import { FaixaDeclaracao } from './FaixaDeclaracao'

const base: IndicadoresMunicipio = { mes_referencia: '2026-09', metodologia: '/fontes', acessos: 7, n_operadoras: 1, hhi: 10000 }
const montar = (i?: IndicadoresMunicipio | null) => render(<MemoryRouter><FaixaDeclaracao indicadores={i} /></MemoryRouter>)

describe('faixa de declaração no município (PT-26 / MUN 5.1)', () => {
  it('sem evento a faixa não aparece', () => {
    expect(montar(base).container.firstChild).toBeNull()
    expect(montar(null).container.firstChild).toBeNull()
    expect(montar({ ...base, eventos: [] }).container.firstChild).toBeNull()
  })

  it('mostra o fato sem causa: sem declaração desde, último mês, acessos, primeira declaração e a norma vigente', () => {
    montar({ ...base, eventos: [
      { cnpj: '09189450000149', empresa: 'XZOON', tipo: 'sem_declaracao_desde', mes: '2026-08', ultimo_mes_declarado: '2026-07', acessos: 251, mes_acessos: '2026-07' },
      { cnpj: '11111111000111', empresa: '', tipo: 'primeira_declaracao', mes: '2026-09', acessos: 50, mes_acessos: '2026-09' },
    ] })
    const faixa = screen.getByTestId('faixa-declaracao')
    expect(faixa.textContent).toMatch(/XZOON.*sem declaração desde 2026-08; último mês declarado 2026-07; 251 acessos neste município em 2026-07/)
    expect(faixa.textContent).toMatch(/primeira declaração da série em 2026-09, com 50 acessos/)
    expect(screen.getByRole('link', { name: 'XZOON' })).toHaveAttribute('href', '/operadora/09189450000149')
    expect(screen.getByRole('link', { name: /CNPJ 11\.111\.111\/0001-11/ })).toBeTruthy()      // sem nome: o CNPJ no lugar do vazio
    expect(faixa.textContent).toMatch(/Coleta de Dados da Anatel \(antigo SICI\)/)
    expect(faixa.textContent).toMatch(/Resolução Anatel nº 774\/2025/)
    expect(faixa.textContent).toMatch(/descrevem só o que foi declarado/)
    expect(faixa.textContent).not.toMatch(/omi[s]s|irregular|infra[çc]|sonegou|migrou|incorpor/i)
  })
})
