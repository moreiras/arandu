// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { DemandaOfertaUfBloco } from './DemandaOfertaUfBloco'
import type { UfCtx } from '../contexto'
import type { DemandaOfertaLinha, DemandaOfertaUf } from '../../../types/api'

const linha = (o: Partial<DemandaOfertaLinha>): DemandaOfertaLinha => ({
  classe: 'oferta_abaixo_da_demanda', domicilios_projetados: 1000000, demanda_domicilios: 600000, demanda_margem: 39200, oferta_acessos_pf: 300000,
  razao: 0.5, razao_min: 0.47, razao_max: 0.53, nao_visto: 300000, ...o,
})
const d: DemandaOfertaUf = {
  natureza: 'estimativa_arandurape', fonte: 'TIC Domicílios', tic_edicao: 2025, mes_referencia_sici: '2026-08', pnad_ano: '2025', intervalo: '95%',
  limites: 'Estimativa do Arandurapé. Acesso não é domicílio.', snapshot_date: '2026-11-01', uf: 'AL', regiao: 'Nordeste',
  demanda_oferta: linha({}), comparacao: { regiao: linha({ classe: 'compativel', razao: 0.9, razao_min: 0.85, razao_max: 0.95 }), brasil: linha({ classe: 'indeterminado', motivo: 'precisão baixa' }) },
}

describe('bloco demanda × oferta da UF', () => {
  it('mostra razão com intervalo, a leitura e o rótulo de estimativa do Arandurapé', () => {
    render(<MemoryRouter><DemandaOfertaUfBloco dados={{ uf: 'AL', demandaOferta: d } as UfCtx} snapshot={null} /></MemoryRouter>)
    expect(screen.getByText('oferta abaixo da demanda')).toBeTruthy()
    expect(screen.getByText('compatível')).toBeTruthy()
    expect(screen.getByText('indeterminado').getAttribute('title')).toBe('precisão baixa')
    expect(screen.getByText('Região Nordeste')).toBeTruthy()
    expect(screen.getAllByText(/0,47 a 0,53/).length).toBe(2)
    expect(screen.getByText(/Estimativa do Arandurapé · TIC Domicílios 2025/)).toBeTruthy()
  })

  it('não renderiza nada sem o cruzamento', () => {
    const { container } = render(<MemoryRouter><DemandaOfertaUfBloco dados={{ uf: 'AL' } as UfCtx} snapshot={null} /></MemoryRouter>)
    expect(container.innerHTML).toBe('')
  })
})
