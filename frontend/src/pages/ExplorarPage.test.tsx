// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { server } from '../test/server'
import { useAppStore } from '../store/app'
import { estadoInicial, paraUrl, type SchemaConsulta } from '../features/explorar/consulta'
import { ExplorarPage, detalheDoErro } from './ExplorarPage'

const schema: SchemaConsulta = {
  operators: ['eq', 'gte', 'contains', 'in', 'exists'], aggregate_functions: ['count', 'sum', 'avg'],
  recipes: [
    { pergunta: 'Operadoras grandes sem ASN', args: { collection: 'operadoras', filter: { and: [{ field: 'acessos', op: 'gte', value: 5000 }, { field: 'com_asn', op: 'eq', value: false }] }, select: ['empresa', 'cnpj', 'acessos'], sort: [{ field: 'acessos', dir: 'desc' }], limit: 50 } },
    { pergunta: 'Ferramenta sem coleção', ferramenta: 'resolve_operator' },
  ],
  collections: {
    operadoras: { key: 'cnpj', description: 'Operadoras de banda larga', geo: { lat: 'lat', lon: 'lon' }, fields: [
      { name: 'cnpj', type: 'string' }, { name: 'empresa', type: 'string', example: 'PAINSONLINE' }, { name: 'acessos', type: 'int' },
      { name: 'com_asn', type: 'bool' }, { name: 'meio', type: 'string', enum: ['Fibra', 'Rádio'] }] },
    ixps: { key: 'code', description: 'PTTs', fields: [{ name: 'code', type: 'string' }, { name: 'uf', type: 'string' }] },
  },
}
const corpos: Array<{ colecao: string; corpo: any }> = []

function Local() { const l = useLocation(); return <div data-testid="onde">{l.search}</div> }
const montar = (url = '/explorar') => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter initialEntries={[url]}><Local /><ExplorarPage /></MemoryRouter>
  </QueryClientProvider>,
)

beforeEach(() => {
  corpos.length = 0
  useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' })
  server.use(
    http.get('*/api/v1/schema', () => HttpResponse.json(schema)),
    http.post('*/api/v1/query/:colecao', async ({ params, request }) => {
      const corpo = await request.json() as any
      corpos.push({ colecao: String(params.colecao), corpo })
      if (corpo.aggregate) return HttpResponse.json({ mode: 'aggregate', matched: 10, groups: [{ key: { meio: 'Fibra' }, count: 7 }, { key: { meio: 'Rádio' }, count: 3 }], snapshot_date: '2026-09-20' })
      return HttpResponse.json({ mode: 'list', total: 2, page: 1, pages: 1, snapshot_date: '2026-09-20', items: [{ cnpj: '11111111000111', empresa: 'Fibra Vix', acessos: 12345 }, { cnpj: '22222222000122', empresa: 'Rede Sul', acessos: 800 }] })
    }),
  )
})

describe('/explorar', () => {
  it('monta uma consulta no construtor, executa, grava a URL e mostra a tabela com links', async () => {
    montar()
    await screen.findByRole('form', { name: 'Construtor de consulta' })
    fireEvent.click(screen.getByRole('button', { name: '+ condição' }))
    const cond = screen.getByRole('group', { name: 'Condição 1' })
    fireEvent.change(within(cond).getByLabelText('Campo'), { target: { value: 'acessos' } })
    fireEvent.change(within(cond).getByLabelText('Operador'), { target: { value: 'gte' } })
    fireEvent.change(within(cond).getByLabelText('Valor'), { target: { value: '5000' } })
    fireEvent.change(screen.getByLabelText('Ordenar por'), { target: { value: 'acessos' } })
    fireEvent.click(screen.getByRole('button', { name: 'Executar' }))
    expect(await screen.findByText('Fibra Vix')).toBeInTheDocument()
    expect(corpos[corpos.length - 1]).toMatchObject({ colecao: 'operadoras', corpo: { filter: { field: 'acessos', op: 'gte', value: 5000 }, sort: [{ field: 'acessos', dir: 'desc' }], limit: 25 } })
    expect(screen.getByTestId('onde').textContent).toMatch(/^\?c=operadoras&q=/)
    expect(screen.getByRole('link', { name: '11111111000111' })).toHaveAttribute('href', '/operadora/11111111000111')
    expect(screen.getByText(/2 resultados/)).toBeInTheDocument()
    expect(screen.getByLabelText('Corpo da consulta').textContent).toContain('/api/v1/query/operadoras')
  })

  it('abrir um link com a consulta na URL carrega o construtor e já executa', async () => {
    const e = estadoInicial('ixps'); e.condicoes = [{ campo: 'uf', op: 'eq', valor: 'ES' }]
    montar(`/explorar?${paraUrl(e)}`)
    await waitFor(() => expect(corpos.length).toBe(1))
    expect(corpos[0]).toMatchObject({ colecao: 'ixps', corpo: { filter: { field: 'uf', op: 'eq', value: 'ES' } } })
    expect((await screen.findByLabelText('Coleção') as HTMLSelectElement).value).toBe('ixps')
    expect(within(screen.getByRole('group', { name: 'Condição 1' })).getByLabelText('Valor')).toHaveValue('ES')
  })

  it('receita do schema vira consulta executada; receita sem coleção não aparece na lista', async () => {
    montar()
    const sel = await screen.findByLabelText('Receitas')
    expect(within(sel).queryByText('Ferramenta sem coleção')).toBeNull()
    fireEvent.change(sel, { target: { value: '0' } })
    await waitFor(() => expect(corpos.length).toBe(1))
    expect(corpos[0].corpo.filter).toEqual({ and: [{ field: 'acessos', op: 'gte', value: 5000 }, { field: 'com_asn', op: 'eq', value: false }] })
    expect(corpos[0].corpo.select).toEqual(['empresa', 'cnpj', 'acessos'])
  })

  it('valor inválido avisa na tela e NÃO chama a API', async () => {
    montar()
    await screen.findByRole('form', { name: 'Construtor de consulta' })
    fireEvent.click(screen.getByRole('button', { name: '+ condição' }))
    const cond = screen.getByRole('group', { name: 'Condição 1' })
    fireEvent.change(within(cond).getByLabelText('Campo'), { target: { value: 'acessos' } })
    fireEvent.change(within(cond).getByLabelText('Valor'), { target: { value: 'muitos' } })
    fireEvent.click(screen.getByRole('button', { name: 'Executar' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('não é um número')
    expect(corpos.length).toBe(0)
  })

  it('modo agrupar mostra os grupos', async () => {
    montar()
    await screen.findByRole('form', { name: 'Construtor de consulta' })
    fireEvent.click(screen.getByLabelText('Agrupar e calcular'))
    fireEvent.click(screen.getByLabelText('meio'))
    fireEvent.click(screen.getByRole('button', { name: 'Executar' }))
    expect(await screen.findByText(/2 grupos/)).toBeInTheDocument()
    expect(corpos[corpos.length - 1].corpo).toMatchObject({ group_by: ['meio'], aggregate: [{ fn: 'count' }] })
  })

  it('erro 400 da API aparece com o detalhe, sem o ruído técnico', async () => {
    server.use(http.post('*/api/v1/query/:colecao', () => HttpResponse.json({ detail: "campo 'fantasma' não existe" }, { status: 400 })))
    const e = estadoInicial('ixps')
    montar(`/explorar?${paraUrl(e)}`)
    expect(await screen.findByRole('alert')).toHaveTextContent("A consulta não pôde ser executada: campo 'fantasma' não existe")
  })

  it('coleção com coordenadas oferece "Perto de"; sem coordenadas, não', async () => {
    montar()
    await screen.findByRole('form', { name: 'Construtor de consulta' })
    expect(screen.getByLabelText('Lugar')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Coleção'), { target: { value: 'ixps' } })
    expect(screen.queryByLabelText('Lugar')).toBeNull()
  })

  it('trocar de coleção limpa condições e colunas da anterior', async () => {
    montar()
    await screen.findByRole('form', { name: 'Construtor de consulta' })
    fireEvent.click(screen.getByRole('button', { name: '+ condição' }))
    expect(screen.getAllByRole('group', { name: /Condição/ })).toHaveLength(1)
    fireEvent.change(screen.getByLabelText('Coleção'), { target: { value: 'ixps' } })
    expect(screen.queryAllByRole('group', { name: /Condição/ })).toHaveLength(0)
  })
})

describe('detalheDoErro', () => {
  it('extrai o detalhe de JSON, mantém texto e trata vazio', () => {
    expect(detalheDoErro(new Error('HTTP 400: {"detail":"filtro inválido"}'))).toBe('filtro inválido')
    expect(detalheDoErro(new Error('HTTP 500: boom'))).toBe('boom')
    expect(detalheDoErro(new Error('HTTP 502'))).toBe('erro desconhecido')
    expect(detalheDoErro(null)).toBe('erro desconhecido')
  })
})
