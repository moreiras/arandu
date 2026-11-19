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
import { UsoInternetPage } from './UsoInternetPage'

vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ anon: null, loading: false }) }))

const meta = {
  pesquisa: 'TIC Domicílios', edicao: 2025, fonte: 'Cetic.br|NIC.br, TIC Domicílios 2025 (tabelas)', licenca: 'CC BY 4.0', pagina: 'https://cetic.br/pt/pesquisa/domicilios/microdados/',
  coletado_em: '2026-11-01T00:00:00Z', snapshot_date: '2026-11-01', aviso: 'Estimativas amostrais publicadas pelo Cetic.br|NIC.br (não são contagens).',
}
const linha = (recorte: string, dimensao: string, resposta: string, proporcao: number, total: number) =>
  ({ tabela: 'A1', titulo_tabela: 'Domicílios com computador', dimensao, recorte, item: '', resposta, proporcao, margem_proporcao: 1.3, total, margem_total: 5000 })

const montar = () => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><UsoInternetPage /></MemoryRouter></QueryClientProvider>,
)

describe('página Uso da Internet', () => {
  it('mostra a tabela oficial com a margem de erro, a edição e a citação, sem alterar os números', async () => {
    let pedido = ''
    server.use(
      http.get('*/api/v1/cetic/tabelas', ({ request }) => { pedido = new URL(request.url).searchParams.get('pesquisa') ?? ''; return HttpResponse.json({ ...meta, total: 1, items: [{ tabela: 'A1', codigo: 'A1', titulo: 'Domicílios com computador', universo: 'Total de domicílios', notas: ['¹ Considera-se um domicílio com computador...'] }] }) }),
      http.get('*/api/v1/cetic/estimativas', () => HttpResponse.json({
        natureza: 'estimativa_arandurape', pesquisa: 'TIC Domicílios', edicao: 2025, fonte: 'Estimativa do Arandurapé', licenca: 'CC BY 4.0', pagina: meta.pagina, coletado_em: null, snapshot_date: '2026-11-01',
        aviso: 'Estimativa do Arandurapé, não é número do Cetic.br.', metodo: { replicas: 200, supressao_n_minimo: 30, precisao_baixa_cv: 0.3 },
        validacao: { comparados: 12, diferenca_max_proporcao_pp: 0.003, razao_margem_oficial_min: 1.077, razao_margem_oficial_max: 1.143 },
        indicadores: { internet: { rotulo: 'Domicílios com acesso à Internet', definicao: 'A4' } }, total: 2,
        items: [{ grupo: 'SP', tipo: 'uf', n: 1068, domicilios: 100, indicadores: { internet: { proporcao: 88.5, margem: 3.9, total: 12345678 } } },
                { grupo: 'AP', tipo: 'uf', n: 12, domicilios: 10, indicadores: { internet: { suprimido: 'menos de 30 domicílios entrevistados' } } }],
      })),
      http.get('*/api/v1/cetic/indicadores', () => HttpResponse.json({ ...meta, filtros: {}, total: 4, items: [linha('Total', 'Total', 'Sim', 31.68, 24981993), linha('Total', 'Total', 'Não', 68.32, 53879033), linha('Norte', 'Região', 'Sim', 25.39, 1200000), linha('Norte', 'Região', 'Não', 74.61, 3600000)] })),
    )
    montar()
    await waitFor(() => expect(screen.getByText(/A1 — Domicílios com computador/, { selector: 'h2' })).toBeTruthy())
    expect(pedido).toBe('domicilios')
    await waitFor(() => expect(screen.getByText('31,7')).toBeTruthy())
    expect(screen.getByText('25,4')).toBeTruthy()
    expect(screen.getAllByText('±1,3').length).toBeGreaterThan(0)
    expect(screen.getByText(/Fonte: Cetic.br\|NIC.br, TIC Domicílios 2025/)).toBeTruthy()
    expect(screen.getByText(/licença CC BY 4.0/)).toBeTruthy()
    expect(screen.getByText(/não são contagens/)).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Mostrar'), { target: { value: 'total' } })
    expect(screen.getAllByText('24.981.993').length).toBe(2)                          // na tabela e no gráfico por recorte
    expect(screen.getByTestId('barras-recorte')).toBeTruthy()
    await waitFor(() => expect(screen.getByText(/derivada dos microdados, não é número do Cetic.br/)).toBeTruthy())
    expect(screen.getByText('88,5')).toBeTruthy()
    expect(screen.getByText(/suprimido \(menos de 30/)).toBeTruthy()
    expect(screen.getByText(/margem oficial é de 1,077 a 1,143 vez/)).toBeTruthy()
  })

  it('diz que as tabelas não estão publicadas quando a API devolve 404', async () => {
    server.use(http.get('*/api/v1/cetic/tabelas', () => HttpResponse.json({ detail: 'x' }, { status: 404 })))
    montar()
    await waitFor(() => expect(screen.getByText(/não estão publicadas neste snapshot/)).toBeTruthy())
  })
})
