// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
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

  const mostrarTodas = async () => {
    montar(<FontesPage />)
    await screen.findByRole('list', { name: 'Fontes de dados' })
    fireEvent.click(screen.getByRole('button', { name: /Mostrar todas as fontes/ }))
    return screen.getByRole('list', { name: 'Fontes de dados' })
  }

  it('FONT-E1: o aviso de itens não verificados aparece em todo cartão cujo cadastro declara pendência', async () => {
    const lista = await mostrarTodas()
    const esperados = catalogo.fontes.filter((f) => f.nao_verificado > 0).length
    expect(esperados).toBeGreaterThan(0)
    expect(within(lista).getAllByTestId('aviso-nao-verificado')).toHaveLength(esperados)
    const alvo = catalogo.fontes.find((f) => f.nao_verificado > 0)!
    expect(within(within(lista).getByText(alvo.id).closest('li')!).getByTestId('aviso-nao-verificado').textContent).toBe(`Itens deste cadastro ainda não conferidos pelo projeto: ${alvo.nao_verificado}.`)
  })

  it('FONT-E2: licença e uso comercial legíveis, sem o token cru, e a herança de uso comercial explicada', async () => {
    const lista = await mostrarTodas()
    expect(lista.textContent).not.toMatch(/nao_verificado/)
    expect(lista.textContent).toContain('Licença: não verificada pelo projeto')
    const fac = within(lista).getByText('peeringdb_fac').closest('li')!
    expect(fac.textContent).toContain('uso comercial com condições ou restrito (ver termos)')
    expect(fac.textContent).toMatch(/por herança de: peeringdb_networks, peeringdb_ixps/)
    expect(lista.textContent).toContain('uso comercial permitido pelos termos lidos')
  })

  it('FONT-E3 e FONT-E4: estado da coleta de cada fonte, frescor com limite e data da verificação', async () => {
    server.use(http.get('*/api/v1/brasil/snapshots/:date', () => HttpResponse.json({ date: '2026-09-20', summary: null, manifest: { sources: [
      { id: 'rpki_collector', as_of: '2026-09-13', coletado_em: '2026-09-13', verificado_em: '2026-09-14', frescor: 'atrasado', limite_dias: 2 },
      { id: 'ioda_outages', as_of: null, frescor: 'ausente', ativa: false },
      { id: 'ipv4_vigia', as_of: null, frescor: 'ausente', ativa: true },
      { id: 'registro_br', as_of: '2026-09-20', frescor: 'sem_limite' }] } })))
    const lista = await mostrarTodas()
    const txt = (id: string) => within(lista).getByText(id).closest('li')!.textContent!
    await waitFor(() => expect(txt('rpki_collector')).toContain('atrasada (limite 2 dias)'))
    expect(txt('rpki_collector')).toContain('verificada em 14/09/2026')
    expect(txt('ioda_outages')).toContain('fonte desativada')
    expect(txt('ipv4_vigia')).toContain('sem versão coletada para este snapshot')
    expect(txt('registro_br')).toContain('sem limite de frescor definido')
    expect(txt('lacnic_historico')).toContain('coleta manual, fora do registro de coleta')
    expect(txt('curada_ixps')).toContain('curadoria do projeto, fora do registro de coleta')
    expect(lista.textContent).not.toMatch(/sem_limite|defasada/)
  })

  it('TRANSV-E9: snapshot sem registro por fonte mostra a faixa e nenhum cartão traz a linha de última coleta', async () => {
    server.use(http.get('*/api/v1/brasil/snapshots/:date', () => HttpResponse.json({ date: '2026-09-20', summary: null, manifest: { sources: null } })))
    montar(<FontesPage />)
    expect(await screen.findByTestId('sem-registro-coleta')).toHaveTextContent('não traz o registro de coleta por fonte')
    const lista = await screen.findByRole('list', { name: 'Fontes de dados' })
    expect(within(lista).queryAllByTestId('ultima-coleta')).toHaveLength(0)
    expect(lista.textContent).not.toMatch(/Última coleta/)
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
