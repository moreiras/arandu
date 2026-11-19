// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../test/server'
import { QualidadePage } from './QualidadePage'
import { ConsumidorMunicipioBloco, ConsumidorOperadoraBloco, ConsumidorUfBloco } from '../features/qualidade/consumidor'
import type { ConsJanela, ConsMetricas, ConsumidorMunicipio, ConsumidorOperadora } from '../types/api'

vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ anon: null, loading: false }) }))

const janela: ConsJanela = { de: '2025-11', ate: '2026-10', meses: 12, meses_com_dado: 10, meses_ausentes: ['2026-05', '2026-06'], aviso: 'sem dado em 2026-05, 2026-06: o arquivo do mês não pôde ser lido; os totais da janela cobrem 10 de 12 meses' }
const meta = { natureza: 'declarado_por_consumidores', fonte: 'Consumidor.gov.br', url_fonte: null, limites: 'Reclamação não é prova de falha.', minimos: { base_para_media: 30, reclamacoes_por_celula: 5 }, snapshot_date: '2026-11-05' }
const cheia: ConsMetricas = { n: 1200, respondidas: 1190, avaliadas: 400, resolvidas: 300, pct_respondidas: 99.2, indice_solucao: 75, tempo_medio_dias: 7.5, nota_media: 3.61 }
const rala: ConsMetricas = { n: 12, respondidas: 12, avaliadas: 5, resolvidas: 3, pct_respondidas: null, indice_solucao: null, tempo_medio_dias: null, nota_media: null }

describe('Consumidor.gov.br', () => {
  it('aba: setor por mês, cobertura da ligação, filtro por UF e empresa sem CNPJ; base insuficiente aparece como traço, não como zero', async () => {
    let uf: string | null = 'x'
    server.use(
      http.get('*/api/v1/consumidor/resumo', () => HttpResponse.json({
        ...meta, janela, setor_por_mes: [{ mes: '2026-10', ...cheia }],
        casamento: { reclamacoes_janela: 252255, por_metodo: { curada: 90 }, pct_com_cnpj: 93.8, automaticas_descartadas_por_uf: [], marcas: 28, marcas_com_cnpj: 18, tabela_curada: { versao: 2, curada_em: '2026-11-07', fonte: 'x', marcas: 30, apelidos_consumidor_gov: 13 } },
        cidades: { reclamacoes_janela: 252255, sem_codigo_ibge: 1000, casadas_com_interrogacao: 231, pct_com_codigo_ibge: 99.6, maiores_sem_codigo: [] },
        leitura: { meses: 24, mes_inicial: '2024-11', mes_final: '2026-10', baixados: 0, reclamacoes_telecom: 462687, meses_indisponiveis: ['2026-05', '2026-06'] },
      })),
      http.get('*/api/v1/consumidor/marcas', ({ request }) => {
        uf = new URL(request.url).searchParams.get('uf')
        return HttpResponse.json({ ...meta, janela, uf, ordem: 'empresa (alfabética; sem ranking)', total: 2, limit: 25, offset: 0, items: [
          { marca: 'Alfa Fibra', raizes: ['11111111'], cnpjs_matriz: ['11111111000111'], casamento: 'curada', ...cheia },
          { marca: 'Sem Dono', raizes: [], cnpjs_matriz: [], casamento: null, ...rala }] })
      }),
    )
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={['/qualidade?aba=consumidor']}><QualidadePage /></MemoryRouter></QueryClientProvider>)
    await waitFor(() => expect(screen.getByText('Alfa Fibra')).toBeTruthy())
    expect(screen.getByText(/93,8% com CNPJ ligado/)).toBeTruthy()
    expect(screen.getByText('11111111').getAttribute('href')).toBe('/operadora/11111111000111')
    expect(screen.getByText('sem CNPJ ligado')).toBeTruthy()
    expect(screen.getByText(/os totais da janela cobrem 10 de 12 meses/)).toBeTruthy()
    expect(screen.getByText(/Sem ranking: a lista é alfabética/)).toBeTruthy()
    expect(screen.getAllByText('75,0%').length).toBeGreaterThan(0)
    expect(screen.getAllByTitle('base insuficiente (menos de 30 casos)').length).toBeGreaterThanOrEqual(4)       // a empresa pequena: índice, tempo, nota e % respondidas
    fireEvent.change(screen.getAllByRole('combobox')[0], { target: { value: 'SP' } })
    await waitFor(() => expect(uf).toBe('SP'))
  })

  it('operadora: empresas ligadas ao CNPJ, janela, série mensal e assuntos', () => {
    const c: ConsumidorOperadora = {
      ...meta, raiz: '11111111', janela, marcas: [{ marca: 'Alfa Fibra', casamento: 'curada', base_casamento: 'apelido', janela: cheia, por_mes: [{ mes: '2026-10', ...cheia }] }],
      assuntos: [{ marca: 'Alfa Fibra', assunto: 'Internet Fixa', n: 700 }], grupos: [], setor_por_mes: [],
    }
    render(<MemoryRouter><ConsumidorOperadoraBloco dados={{ consumidor: c } as never} snapshot="2026-11-05" /></MemoryRouter>)
    expect(screen.getByText(/Empresas do Consumidor.gov.br ligadas a este CNPJ: Alfa Fibra \(curada\)/)).toBeTruthy()
    expect(screen.getAllByText('3,61').length).toBeGreaterThan(0)
    expect(screen.getByText(/Alfa Fibra: série mensal \(1 meses\)/)).toBeTruthy()
    expect(screen.getByText(/cobrem 10 de 12 meses/)).toBeTruthy()
  })

  it('município: total e empresas em ordem alfabética; só aparece com dado', () => {
    const c: ConsumidorMunicipio = { ...meta, ibge: '1', nome: 'Alfa', uf: 'RO', populacao: 1000, janela, total: cheia, itens: [{ marca: 'Zeta', raizes: [], ...cheia }, { marca: 'Alfa Fibra', raizes: [], ...cheia }] }
    const { container } = render(<MemoryRouter><ConsumidorMunicipioBloco dados={{ consumidor: c } as never} snapshot="2026-11-05" /></MemoryRouter>)
    const linhas = [...container.querySelectorAll('tbody tr')].map((tr) => tr.querySelector('td')?.textContent)
    expect(linhas).toEqual(['Todas as operadoras', 'Alfa Fibra', 'Zeta'])
    expect(screen.getByText(/pelo menos 5 reclamações no município/)).toBeTruthy()
    const vazio = render(<MemoryRouter><ConsumidorMunicipioBloco dados={{ consumidor: null } as never} snapshot="2026-11-05" /></MemoryRouter>)
    expect(vazio.container.textContent).toBe('')
  })

  it('UF: empresas da UF', () => {
    render(<MemoryRouter><ConsumidorUfBloco dados={{ consumidor: { ...meta, uf: 'SP', janela, itens: [{ marca: 'Alfa Fibra', raizes: [], ...cheia }] } } as never} snapshot="2026-11-05" /></MemoryRouter>)
    expect(screen.getByText('Alfa Fibra')).toBeTruthy()
    expect(screen.getByText('1.200')).toBeTruthy()
  })
})
