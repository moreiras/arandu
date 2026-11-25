// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { fixtures, server } from '../test/server'
import type { Limites } from '../types/api'
import { DadosPage } from './DadosPage'
import { Sobre } from './Sobre'

const montar = (el: JSX.Element) => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter>{el}</MemoryRouter>
  </QueryClientProvider>,
)

const lim = fixtures.limites as unknown as Limites
const com = (mut: (l: Limites) => void) => {
  const l: Limites = JSON.parse(JSON.stringify(lim))
  mut(l)
  server.use(http.get('*/api/v1/limites', () => HttpResponse.json(l)))
}

describe('/dados: quadro "Escolha o seu acesso" (PT-21 / TRANSV-E13)', () => {
  it('monta o quadro com os números de /api/v1/limites (nada fixo no front)', async () => {
    com((l) => {
      l.sem_conta.orcamento_diario_segundos = 1200
      l.sem_conta.custo_por_chamada_segundos = 4
      l.sem_conta.chamadas_medidas_por_dia = 300
      l.api.sem_conta = [{ janela: 'minuto', segundos: 60, limite: 77 }]
      l.mcp.chave = { ativa: true, cota_diaria: 1234, sem_teto_diario: false, contagem: 'x' }
    })
    montar(<DadosPage />)
    const quadro = await screen.findByTestId('escolha-acesso')
    expect(screen.getByRole('heading', { level: 2, name: 'Escolha o seu acesso' })).toBeInTheDocument()
    expect(quadro.querySelector('caption')).not.toBeNull()
    expect(quadro.querySelectorAll('thead th[scope="col"]')).toHaveLength(4)
    const t = quadro.textContent ?? ''
    expect(t).toContain('20 minutos')
    expect(t).toContain('4 s do orçamento de 1.200 s')
    expect(t).toContain('cerca de 300 por dia')
    expect(t).toContain('77 por minuto')
    expect(t).toContain('cota de 1.234 requisições por dia UTC')
    expect(t).not.toMatch(/\b(120 por minuto|1\.500 por hora)\b/)
  })

  it('chave desligada: nenhuma promessa de chave', async () => {
    com((l) => { l.mcp.chave = { ativa: false, cota_diaria: null, sem_teto_diario: true, contagem: 'x' } })
    montar(<DadosPage />)
    const quadro = await screen.findByTestId('escolha-acesso')
    expect(within(quadro).queryByText('MCP, com chave')).toBeNull()
    await waitFor(() => expect(document.body.textContent).not.toMatch(/chave de MCP|SUA_CHAVE|Bearer/))
  })

  it('com a chave ligada e sem teto diário, diz "sem teto diário"', async () => {
    com((l) => { l.mcp.chave = { ativa: true, cota_diaria: null, sem_teto_diario: true, contagem: 'x' } })
    montar(<DadosPage />)
    expect((await screen.findByTestId('escolha-acesso')).textContent).toContain('sem teto diário')
  })

  it('falha ao carregar: aviso com o endereço da rota, sem quadro', async () => {
    server.use(http.get('*/api/v1/limites', () => new HttpResponse('boom', { status: 500 })))
    montar(<DadosPage />)
    expect(await screen.findByText(/não pôde ser carregado agora/)).toBeInTheDocument()
    expect(screen.queryByTestId('escolha-acesso')).toBeNull()
  })

  it('DADOS-E2: o exemplo consulta acessos_municipio por UF com mês de referência, não operadoras por uf_sede', async () => {
    montar(<DadosPage />)
    const ex = screen.getByLabelText('Exemplo: operadoras com mais acessos em uma UF').textContent ?? ''
    expect(ex).toContain('/api/v1/query/acessos_municipio')
    expect(ex).toContain('"mes_referencia"')
    expect(ex).not.toMatch(/operadoras|uf_sede/)
    await screen.findByTestId('escolha-acesso')
  })
})

describe('Sobre: tetos vindos de /api/v1/limites', () => {
  it('mostra os valores da rota', async () => {
    com((l) => { l.sem_conta.orcamento_diario_segundos = 900; l.mcp.sem_chave = [{ janela: 'minuto', segundos: 60, limite: 11 }] })
    montar(<Sobre />)
    const bloco = await screen.findByTestId('tetos-de-uso')
    expect(bloco.textContent).toContain('900 s (15 minutos)')
    expect(bloco.textContent).toContain('11 por minuto')
  })
})
