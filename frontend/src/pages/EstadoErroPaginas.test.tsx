// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { server } from '../test/server'
import { AFIRMA_AUSENCIA, ESPERADO, apiInteiraCom, type CasoErro } from '../test/respostasErro'
import { useAppStore } from '../store/app'
import { ASNPage } from './ASNPage'
import { OperadoraPage } from './OperadoraPage'
import { MunicipioPage } from './MunicipioPage'
import { UFPage } from './UFPage'
import { FacilityPage } from './FacilityPage'
import { RelatorioPage } from './RelatorioPage'
import { CDNCapPage } from './CDNCapPage'
import { EstadosPage } from './EstadosPage'
import { MudancasPage } from './MudancasPage'
import { MercadoIpv4Page } from './MercadoIpv4Page'
import { CompararEntidades } from '../features/comparar/CompararEntidades'
import { ComparaDatas } from '../features/comparar/ComparaDatas'
import { MercadoIpv4 } from '../features/panorama/AbaFamilia'

vi.mock('../features/municipio/MapaRaio', () => ({ MapaRaio: () => <div /> }))
vi.mock('../features/estados/MapaMunicipios', () => ({ default: () => <div /> }))
// fora do AuthProvider o contexto fica "carregando" para sempre; as páginas que esperam /auth/me (mudanças) precisam de um visitante pronto
vi.mock('../auth/AuthContext', async (original) => ({
  ...(await original<typeof import('../auth/AuthContext')>()),
  useAuth: () => ({ user: null, anon: null, loading: false, loginPrompt: null, requireLogin: () => true, closeLoginPrompt: () => {} }),
}))

/** PT-01: com a API respondendo 401, 403/429 de orçamento, 429 de taxa, 500 ou sem rede, nenhuma página afirma que o dado não
 *  existe nem mostra zero: mostra a causa e a ação. */
const CASOS: CasoErro[] = ['login', 'orcamento403', 'orcamento429', 'taxaComEspera', 'taxaSemEspera', 'falha500', 'rede']

function montar(rota: string, caminho: string, el: JSX.Element) {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[caminho]}><Routes><Route path={rota} element={el} /></Routes></MemoryRouter>
    </QueryClientProvider>,
  )
}

const PAGINAS: [string, string, string, () => JSX.Element][] = [
  ['ASN', '/asn/:asn', '/asn/64496?versao=1', () => <ASNPage />],
  ['operadora', '/operadora/:cnpj', '/operadora/66970229000167?versao=1', () => <OperadoraPage />],
  ['município', '/municipio/:ibge', '/municipio/3550308?versao=1', () => <MunicipioPage />],
  ['UF', '/uf/:uf', '/uf/SP', () => <UFPage />],
  ['instalação', '/instalacao/:id', '/instalacao/9101', () => <FacilityPage />],
  ['relatório', '/relatorio/:tipo/:id', '/relatorio/municipio/4114351', () => <RelatorioPage />],
  ['CDN', '/cdncap/:slug', '/cdncap/google', () => <CDNCapPage />],
]

beforeEach(() => {
  useAppStore.setState({ activeDate: null, latestSnapshot: '2026-11-22' })
  server.use(http.get('*/municipios-centroides.json', () => HttpResponse.json({})))
})

/** A causa aparece e nada na tela afirma ausência nem mostra um zero solto. */
async function confereEstado(caso: CasoErro) {
  const aviso = await screen.findByText(ESPERADO[caso])
  const caixa = aviso.closest('[data-estado]')!
  expect(caixa).toHaveAttribute('role', caso === 'falha500' || caso === 'rede' ? 'alert' : 'status')
  expect(document.body.textContent).not.toMatch(AFIRMA_AUSENCIA)
  expect(screen.queryAllByText(/^0$/)).toHaveLength(0)
  if (caso === 'login' || caso.startsWith('orcamento')) expect(screen.getByRole('link', { name: 'Entrar' })).toHaveAttribute('href', expect.stringContaining('/login?next='))
  if (caso === 'orcamento429') expect(caixa).toHaveTextContent('volte em 1 h')
  if (caso === 'taxaComEspera') expect(caixa).toHaveTextContent('42 s')
}

describe.each(PAGINAS)('página de %s com erro da API', (_nome, rota, caminho, el) => {
  it.each(CASOS)('%s: mostra a causa, sem "não encontrado", "sem dado" nem zero', async (caso) => {
    server.use(apiInteiraCom(caso))
    montar(rota, caminho, el())
    await confereEstado(caso)
  })
})

describe('páginas que continuam sem erro: o 404 segue dizendo "não encontrado"', () => {
  it('ASN inexistente (204 com opcional) continua 404 com a data do snapshot', async () => {
    server.use(http.get('*/api/v1/asns/:asn', () => new HttpResponse(null, { status: 204 })), http.all('*/api/v1/*', () => new HttpResponse(null, { status: 404 })))
    montar('/asn/:asn', '/asn/64500?versao=1', <ASNPage />)
    expect(await screen.findByText(/não encontrado no snapshot 2026-11-22/)).toBeInTheDocument()
  })
  it('CNPJ sem informação continua com "Não há informação"', async () => {
    server.use(http.get('*/api/v1/operadoras/:cnpj', () => new HttpResponse(null, { status: 204 })), http.all('*/api/v1/*', () => new HttpResponse(null, { status: 404 })))
    montar('/operadora/:cnpj', '/operadora/11222333000181?versao=1', <OperadoraPage />)
    expect(await screen.findByText('Não há informação para este CNPJ')).toBeInTheDocument()
  })
})

describe('listas, comparador, mudanças e mercado de IPv4', () => {
  it.each(CASOS)('Estados (%s): mensagem com a causa em vez de 27 traços mudos', async (caso) => {
    server.use(apiInteiraCom(caso))
    montar('/estados', '/estados', <EstadosPage />)
    await confereEstado(caso)
  })

  it.each(CASOS)('comparador de operadoras (%s): sem "Sem dado neste snapshot para"', async (caso) => {
    server.use(apiInteiraCom(caso))
    montar('/comparar', '/comparar?tipo=operadora&ids=66970229000167,02558157000162', <CompararEntidades tipo="operadora" />)
    await confereEstado(caso)
    expect(screen.queryByText(/Sem dado neste snapshot para/)).toBeNull()
  })

  it('comparador: uma operadora sem informação (404) entra em "sem dado", a bloqueada não', async () => {
    server.use(http.get('*/api/v1/operadoras/:cnpj', ({ params }) => params.cnpj === '66970229000167'
      ? HttpResponse.json({ detail: 'Limite', anon_limit_reached: true }, { status: 403 })
      : new HttpResponse(null, { status: 204 })))
    montar('/comparar', '/comparar?tipo=operadora&ids=66970229000167,02558157000162', <CompararEntidades tipo="operadora" />)
    expect(await screen.findByText(/Sem dado neste snapshot para: 02558157000162\./)).toBeInTheDocument()
    expect(screen.getByText(/Limite de uso sem login atingido/)).toBeInTheDocument()
    expect(screen.getByText(/Não carregados agora \(ficam fora do quadro\): 66970229000167/)).toBeInTheDocument()
  })

  it.each(CASOS)('comparação entre datas (%s): "Não há histórico" só para 404', async (caso) => {
    server.use(http.get('*/api/v1/brasil/snapshots', () => HttpResponse.json({ snapshots: ['2026-11-15', '2026-11-22'], latest: '2026-11-22' })), apiInteiraCom(caso))
    montar('/comparar', '/comparar', <ComparaDatas />)
    await confereEstado(caso)
    expect(screen.queryByText(/Não há histórico guardado/)).toBeNull()
  })

  it.each(CASOS)('mudanças (%s): causa em vez de "Não foi possível carregar as mudanças agora"', async (caso) => {
    server.use(http.get('*/api/v1/brasil/snapshots', () => HttpResponse.json({ snapshots: ['2026-11-15', '2026-11-22'], latest: '2026-11-22' })), apiInteiraCom(caso))
    montar('/mudancas', '/mudancas', <MudancasPage />)
    await confereEstado(caso)
  })

  it.each(CASOS)('mercado de IPv4, Transferências (%s): sem "0 operações · página 1 de 1"', async (caso) => {
    server.use(apiInteiraCom(caso))
    montar('/mercado-ipv4', '/mercado-ipv4', <MercadoIpv4Page />)
    await screen.findAllByText(ESPERADO[caso])
    expect(screen.queryByText(/operações · página/)).toBeNull()
    expect(document.body.textContent).not.toMatch(AFIRMA_AUSENCIA)
  })

  it('mercado de IPv4, aba Espaço com 401 mostra o pedido de login em vez de sumir', async () => {
    server.use(apiInteiraCom('login'))
    montar('/mercado-ipv4', '/mercado-ipv4?aba=espaco', <MercadoIpv4Page />)
    expect(await screen.findByText(/Entre para ver este dado/)).toBeInTheDocument()
  })

  it('panorama técnico: 429 no resumo de transferências diz o limite, não "não está publicado"', async () => {
    server.use(
      http.get('*/api/v1/ipv4/transferencias/resumo', () => HttpResponse.json({ detail: 'Limite de uso por minuto atingido para sua rede. Tente novamente em 9 s.' }, { status: 429, headers: { 'Retry-After': '9' } })),
      http.get('*/api/v1/ipv4/espaco', () => new HttpResponse(null, { status: 404 })),
    )
    montar('/', '/', <MercadoIpv4 />)
    expect(await screen.findByText(/Muitas consultas em pouco tempo/)).toBeInTheDocument()
    expect(screen.queryByText(/não está publicado/)).toBeNull()
  })

  it('panorama técnico: 404 nas duas consultas continua "não está publicado neste snapshot"', async () => {
    server.use(http.get('*/api/v1/ipv4/*', () => new HttpResponse(null, { status: 404 })))
    montar('/', '/', <MercadoIpv4 />)
    expect(await screen.findByText(/O mercado de IPv4 não está publicado neste snapshot/)).toBeInTheDocument()
  })
})
