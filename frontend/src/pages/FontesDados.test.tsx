// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { server } from '../test/server'
import { useAppStore } from '../store/app'
import { descreverCadencia, rotuloTipo, type Catalogo } from '../features/fontes/catalogo'
import { DadosPage } from './DadosPage'
import { FontesPage } from './FontesPage'

// o arquivo REAL gerado do catálogo: o teste prova a cobertura de 100% das fontes
const catalogo: Catalogo = JSON.parse(readFileSync(resolve(__dirname, '../../public/catalogo.json'), 'utf-8'))
const fontesDocs: { fontes: { id: string }[] } = JSON.parse(readFileSync(resolve(__dirname, '../../../docs/fontes.json'), 'utf-8'))

const montar = (el: JSX.Element) => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter>{el}</MemoryRouter>
  </QueryClientProvider>,
)

beforeEach(() => {
  useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' })
  server.use(
    http.get('*/catalogo.json', () => HttpResponse.json(catalogo)),
    http.get('*/api/v1/brasil/snapshots/:date', () => HttpResponse.json({ date: '2026-09-20', summary: null, manifest: { sources: [
      { id: 'anatel_sici', as_of: '2026-08', coletado_em: '2026-09-20', frescor: 'ok' }] } })),
  )
})

describe('catálogo público', () => {
  it('cobre 100% das fontes do catálogo e nenhum campo sensível', () => {
    expect(catalogo.fontes.map((f) => f.id).sort()).toEqual(fontesDocs.fontes.map((f) => f.id).sort())
    expect(catalogo.fontes.length).toBeGreaterThanOrEqual(40)
    expect(JSON.stringify(catalogo)).not.toMatch(/"sensivel"/)
  })
  it('rótulos', () => {
    expect(rotuloTipo('bruta')).toBe('Coletada')
    expect(descreverCadencia({ fonte_atualiza: 'mensal', coleta_atual: 'semanal' })).toBe('a fonte atualiza: mensal · coletamos: semanal')
    expect(descreverCadencia({})).toBe('—')
  })
})

describe('/fontes', () => {
  it('mostra as primeiras fontes em cartões, com a licença e a última coleta vinda do manifesto, e as demais sob demanda', async () => {
    montar(<FontesPage />)
    expect(await screen.findByRole('heading', { level: 2, name: new RegExp(`Fontes \\(${catalogo.fontes.length} de ${catalogo.fontes.length}\\)`) })).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Fontes de dados' })).toBeNull()
    const lista = screen.getByRole('list', { name: 'Fontes de dados' })
    expect(within(lista).getAllByRole('listitem').length).toBe(Math.min(catalogo.fontes.length, 18))
    if (catalogo.fontes.length > 18) {
      fireEvent.click(screen.getByRole('button', { name: /Mostrar todas as fontes/ }))
      expect(within(lista).getAllByRole('listitem').length).toBe(catalogo.fontes.length)
    }
    const cartao = within(lista).getByText('anatel_sici').closest('li')!
    expect(within(cartao).getByText(/ref\. 08\/2026/)).toBeInTheDocument()
    expect(within(cartao).getByText(/uso comercial/)).toBeInTheDocument()
  })

  it('busca filtra e o detalhe abre com os campos e a origem', async () => {
    montar(<FontesPage />)
    await screen.findByRole('list', { name: 'Fontes de dados' })
    fireEvent.change(screen.getByLabelText('Buscar fonte'), { target: { value: 'anatel_sici' } })
    const lista = screen.getByRole('list', { name: 'Fontes de dados' })
    expect(within(lista).getAllByRole('listitem').length).toBeGreaterThanOrEqual(1)
    fireEvent.click(within(lista).getAllByText(/Detalhes e campos/)[0])
    expect(screen.getAllByText('Campo').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Origem:/).length).toBeGreaterThan(0)
  })

  it('lista os produtos (recolhidos) com limites e campos', async () => {
    montar(<FontesPage />)
    expect(await screen.findByRole('heading', { level: 2, name: new RegExp(`Produtos e indicadores \\(${catalogo.produtos.length}\\)`) })).toBeInTheDocument()
    expect(document.querySelectorAll('section[aria-labelledby="produtos-titulo"] details details').length).toBe(catalogo.produtos.length)
  })

  it('catálogo ausente: estado de erro explicado', async () => {
    server.use(http.get('*/catalogo.json', () => new HttpResponse('nada', { status: 404 })))
    montar(<FontesPage />)
    expect(await screen.findByText(/Catálogo indisponível/)).toBeInTheDocument()
  })
})

describe('/dados', () => {
  it('traz curl, a configuração do MCP e os links para a documentação e o catálogo', () => {
    montar(<DadosPage />)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('API e MCP')
    expect(screen.getByLabelText('Exemplo: snapshots disponíveis').textContent).toContain('/api/v1/brasil/snapshots')
    expect(screen.getByLabelText('Exemplo: adicionar ao Claude Code').textContent).toContain('claude mcp add --transport http arandurape')
    expect(screen.getByLabelText('Exemplo: configuração JSON de um cliente MCP').textContent).toContain('/mcp')
    expect(screen.getByRole('link', { name: '/api/v1/docs' })).toHaveAttribute('href', '/api/v1/docs')
    expect(screen.getAllByRole('link', { name: /Fontes de dados|fontes/ })[0]).toHaveAttribute('href', '/fontes')
  })
})
