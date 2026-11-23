// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurapé.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { BgpStabilityCarga } from '../../types/bgpStability'
import { CargaBgpSemanas, faixaCarga } from './CargaBgpSemanas'

const semana = (date: string, inicio: string, ultimo: string, extra = {}) => ({
  date, inicio, ultimo_dia: ultimo, dias: 7, coletor: 'rrc-x', arquivos_faltando: 0, sobreposicao_dias: 0, lacuna_dias: 0,
  total_v6: 1000, total_v4: 2000, ...extra,
})
const dados: BgpStabilityCarga = {
  snapshot_date: '2026-09-20', weeks: 2, top: 10, coletor: 'rrc-x',
  semanas: [semana('2026-09-13', '2026-09-06', '2026-09-12'), semana('2026-09-20', '2026-09-11', '2026-09-19', { sobreposicao_dias: 2 })],
  v6: { total: 2000, total_top: 1500, parcela_top_pct: 75, parcela_top_semana_pct: [50, 100],
        ases: [{ asn: 64500, nome: 'Rede Exemplo', total: 1500, semanas: [500, 1000], prefixos: [3, 4] }] },
  v4: { total: 4000, total_top: 0, parcela_top_pct: 0, parcela_top_semana_pct: [0, 0], ases: [] },
}

describe('faixaCarga', () => {
  it('zero fica sem cor; o maior valor cai na faixa mais escura', () => {
    expect(faixaCarga(0, 100)).toBeNull()
    expect(faixaCarga(100, 100)).toBe(4)
    expect(faixaCarga(1, 1_000_000)).toBe(0)
  })
})

describe('CargaBgpSemanas', () => {
  it('mostra IPv6 antes de IPv4, as semanas com a janela real, a nota de sobreposição e a parcela no total', () => {
    render(<MemoryRouter><CargaBgpSemanas data={dados} /></MemoryRouter>)
    const titulos = screen.getAllByRole('heading', { level: 4 }).map((h) => h.textContent)
    expect(titulos).toEqual(['IPv6'])                                                  // IPv4 sem ASes: só o aviso
    expect(screen.getByText(/Nenhum update IPv4 visto/)).toBeInTheDocument()
    const tabela = screen.getByRole('table')
    expect(within(tabela).getByRole('link', { name: 'AS64500' })).toHaveAttribute('href', '/asn/64500')
    expect(within(tabela).getByText('06/09–12/09')).toBeInTheDocument()
    expect(within(tabela).getByTitle('1.000 updates · 4 prefixos com update')).toHaveTextContent('1 mil')
    expect(within(tabela).getByText('75%')).toBeInTheDocument()
    expect(screen.getByText(/2 dia\(s\) em comum com a semana anterior/)).toBeInTheDocument()
    expect(screen.getByText(/coletor rrc-x/)).toBeInTheDocument()
  })
})
