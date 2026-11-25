// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../test/server'
import { CommunitiesPage } from './CommunitiesPage'

const resp = (items: any[]) => ({
  snapshot_date: '2026-11-05', coletado_nivel2: null, coletado_nivel3: '2026-11-06T22:10:00Z', fonte: 'https://lg.ix.br (Alice-LG)', versao_alice: '6.1.0',
  parametros: { amostra_prefixos: 5, min_rotas_perfil: 10, fracao_seletivo: 0.1, fracao_restritivo: 0.5, alvos_restritivo: 50 }, limites: 'Só das rotas recebidas coletadas.',
  filtros: { q: null, ixp: null, classe: null }, total: items.length, por_classe: { nao_exportar_para: items.length }, items,
})
const item = { community: '65000:64510', classe: 'nao_exportar_para', rotulo: 'No export to AS64510', forma: 'equivalente_padrao', alvo: 64510, asns_total: 2, rotas_total: 60,
  ixps: { df: { asns: 2, rotas: 60, top: [{ asn: 64499, rotas: 30 }] } } }
const montar = () => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><CommunitiesPage /></MemoryRouter></QueryClientProvider>)

describe('explorador de communities', () => {
  it('mostra significado, classe, quem usa e o aviso de equivalência; a busca vai para a API', async () => {
    const pedidos: string[] = []
    server.use(http.get('*/api/v1/communities', ({ request }) => { pedidos.push(new URL(request.url).search); return HttpResponse.json(resp([item])) }))
    montar()
    await waitFor(() => expect(screen.getByText('65000:64510')).toBeTruthy())
    expect(screen.getByText(/No export to AS64510/)).toBeTruthy()
    expect(screen.getByText('AS64499').getAttribute('href')).toBe('/asn/64499')
    expect(screen.getByTestId('resumo-communities').textContent).toContain('1 communities')
    expect(document.body.textContent).toMatch(/equivalência assumida pela forma/)
    fireEvent.change(screen.getByPlaceholderText(/ex\.: 65000:0:13335/), { target: { value: '64510' } })
    await waitFor(() => expect(pedidos.some((p) => p.includes('q=64510'))).toBe(true))
  })

  it('COMM-E1: mostra membros distintos e PTTs, e rotula as rotas como soma por PTT', async () => {
    const multi = { ...item, community: '65000:6939', asns_total: 1, asns_soma_ptts: 2, ptts: 2, rotas_total: 84,
      ixps: { sp: { asns: 1, rotas: 42, top: [{ asn: 262901, rotas: 42 }] }, ce: { asns: 1, rotas: 42, top: [{ asn: 262901, rotas: 42 }] } } }
    server.use(http.get('*/api/v1/communities', () => HttpResponse.json(resp([multi]))))
    montar()
    await waitFor(() => expect(screen.getByText('65000:6939')).toBeTruthy())
    expect(screen.getByText('Membros')).toBeTruthy()
    expect(screen.getByText('Rotas (soma por PTT)')).toBeTruthy()
    const linha = screen.getByText('65000:6939').closest('tr') as HTMLElement
    const celulas = Array.from(linha.querySelectorAll('td')).map((td) => td.textContent)
    expect(celulas.slice(2, 5)).toEqual(['1', '2', '84'])
  })

  it('sem resultado diz que não achou nas rotas coletadas; erro da API vira aviso, não erro cru', async () => {
    server.use(http.get('*/api/v1/communities', () => HttpResponse.json(resp([]))))
    montar()
    await waitFor(() => expect(screen.getByText(/Nenhuma community encontrada nas rotas coletadas/)).toBeTruthy())
  })

  it('404 do artefato ausente mostra mensagem amigável', async () => {
    server.use(http.get('*/api/v1/communities', () => HttpResponse.json({ detail: 'x' }, { status: 404 })))
    montar()
    await waitFor(() => expect(screen.getByText(/ainda não estão disponíveis neste snapshot/)).toBeTruthy())
  })

  it('COMM-E4: mostra a cobertura do rodízio (lidos, herdados, sem leitura, idade) e avisa quando o snapshot não a registrou', async () => {
    const cobertura = { elegiveis: 5472, coletados: 2645, herdados: 2800, lidos_na_rodada: 2645, sem_leitura: 27, idade_max_dias: 29, pulados_lentos: 0 }
    server.use(http.get('*/api/v1/communities', () => HttpResponse.json({ ...resp([item]), cobertura_total_nivel3: cobertura })))
    const { unmount } = montar()
    await waitFor(() => expect(screen.getByTestId('cobertura-communities')).toBeTruthy())
    expect(screen.getByTestId('cobertura-communities').textContent).toContain('2.645 de 5.472 vizinhos lidos nesta rodada, 2.800 mantidos de rodadas anteriores, 27 sem leitura (leitura mais antiga com 29 dias)')
    unmount()
    server.use(http.get('*/api/v1/communities', () => HttpResponse.json(resp([item]))))
    montar()
    await waitFor(() => expect(screen.getByTestId('cobertura-communities')).toBeTruthy())
    expect(screen.getByTestId('cobertura-communities').textContent).toContain('não foi registrada neste snapshot')
  })
})
