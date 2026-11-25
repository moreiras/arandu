// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { fixtures, server } from '../test/server'
import { useAppStore } from '../store/app'
import { blocosDe } from '../features/entidade/registry'
import '../features/prefixo'
import { PrefixoPage } from './PrefixoPage'
import { SearchBar } from '../components/layout/SearchBar'
import { MOAS_INDISPONIVEL } from '../features/prefixo/blocks/MoasBloco'

const roa = (asn: number, autoriza: boolean | null) => ({ prefix: '198.18.0.0/24', asn, maxLength: 24, ta: 'lacnic', autoriza_origem: autoriza })
// formato do cenário 1 do sintético: o Registro.br associa 198.18.0.0/24 a 64497, a tabela global vê 64496, que tem o ROA
const info = { prefix: '198.18.0.0/24', ip_version: 4, origin_asn: 64497, escopo: 'alocacao_registro_br', alocacao_registro_br: '198.18.0.0/24',
  registro_asn: 64497, registro_asn_nome: 'Provedor 02 Telecom Ltda', observed_origin_asn: 64496, observed_origin_nome: 'Provedor 01 Telecom Ltda',
  observed_origin_fonte: 'tabela_global', rpki_observado: { estado: 'valid', motivo: null, asn: 64496, roas_que_cobrem: [roa(64496, true)] },
  uf: 'ES', country: 'BR', geo_confidence: 'city_centroid', geo_source: 'dbip-lite-2026-09',
  snapshot_date: '2026-09-20', geo_org: { name: 'Provedor 02 Telecom Ltda', cnpj: '90000001000100' } }
// formato do caso real 2801:80:3e80::/48: detentor com ROA, outra origem observada, inválido
const invalido = { ...info, prefix: '2001:db8:3e80::/48', ip_version: 6, alocacao_registro_br: '2001:db8:3e80::/48', registro_asn: 64510, origin_asn: 64510,
  registro_asn_nome: 'Universidade Exemplo', observed_origin_asn: 64511, observed_origin_nome: 'Rede Exemplo de Pesquisa',
  rpki_observado: { estado: 'invalid', motivo: 'origem_diferente', asn: 64511, roas_que_cobrem: [{ ...roa(64510, false), prefix: '2001:db8:3e80::/48', maxLength: 128 }] } }
const fora = { ...info, prefix: '100.64.0.0/24', escopo: 'fora_do_registro_br', alocacao_registro_br: null, registro_asn: null, origin_asn: null,
  registro_asn_nome: null, observed_origin_asn: 4200000100, observed_origin_nome: 'Foreign Net 1 Inc', uf: null, country: null, geo_org: null,
  rpki_observado: { estado: 'not_found', motivo: 'sem_roa', asn: 4200000100, roas_que_cobrem: [] } }
const respostas: Record<string, object> = { '198.18.0.0/24': info, '2001:db8:3e80::/48': invalido, '100.64.0.0/24': fora }

const analiseComMoas = {
  snapshot_date: '2026-09-20',
  moas: [{ prefix: '198.18.0.0/24', afi: 'v4', origins: [64496, 64497], br_origins: [64496, 64497], is_prefix_br: true, origens: [
    { asn: 64496, name: 'Provedor 01 Telecom Ltda', coletores: 2, coletores_nomes: ['rvT', 'rvU'], asn_br: true },
    { asn: 64497, name: 'Provedor 02 Telecom Ltda', coletores: 1, coletores_nomes: ['rvU'], asn_br: true }] }],
  moas_resumo: { prefixos: { v6: { global: 1, br: 1 }, v4: { global: 2, br: 1 } }, coletores: { v6: ['rvT', 'rvU'], v4: ['rvT', 'rvU'] },
    lista: 'prefixos brasileiros', lista_truncada: false, lista_limite: 2000, definicao: 'Prefixo com mais de um AS de origem.',
    como_ler: 'É fato observado; a causa não é medida. Hipóteses, a conferir caso a caso.', limites: 'Visão de poucos coletores.' },
}

function montar(caminho: string) {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[caminho]}><Routes><Route path="/prefixo/*" element={<PrefixoPage />} /></Routes></MemoryRouter>
    </QueryClientProvider>,
  )
}

let pedidos: string[] = []

beforeEach(() => {
  pedidos = []
  useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' })
  server.use(
    http.get('*/api/v1/brasil/snapshots/:date', () => HttpResponse.json({ date: '2026-09-20', summary: null, manifest: { sources: [{ id: 'rpki_collector', as_of: '2026-09-20', frescor: 'ok' }] } })),
    http.get('*/api/v1/prefixes/*', ({ request }) => {
      const p = decodeURIComponent(new URL(request.url).pathname.replace('/api/v1/prefixes/', ''))
      pedidos.push(p)
      if (p === '198.51.100.0/24') return new HttpResponse('falha', { status: 500 })
      return respostas[p] ? HttpResponse.json(respostas[p]) : new HttpResponse('nada', { status: 404 })
    }),
  )
})

describe('página de prefixo', () => {
  it('blocos na ordem do plano', () => {
    expect(blocosDe('prefixo').map((b) => b.id)).toEqual(['origem', 'rpki', 'ptts', 'registro', 'geo', 'moas', 'ciclo-de-vida'])
  })

  it('separa detentor e origem observada; RPKI, PTTs e Registro.br pela origem observada (PFX-E1)', async () => {
    montar('/prefixo/198.18.0.0/24')
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent('198.18.0.0/24')
    expect(screen.getByText('Alocação do Registro.br')).toBeInTheDocument()                    // selo de escopo
    expect(screen.getByTestId('detentor')).toHaveTextContent('AS64497')
    expect(screen.getByTestId('origem-observada')).toHaveTextContent('AS64496')
    expect(screen.getByTestId('origem-observada')).toHaveTextContent('diferente do AS do Registro.br')
    expect(screen.getByTestId('frase-detentor')).toHaveTextContent('Alocado pelo Registro.br ao AS64497')
    expect(screen.getByTestId('frase-origem')).toHaveTextContent('com origem AS64496')
    expect(screen.getByTestId('rpki-estado')).toHaveTextContent('válido')
    expect(await screen.findByText('lacnic')).toBeInTheDocument()                                // o ROA que cobre o prefixo, com o TA
    expect(await screen.findByRole('link', { name: 'ZA' })).toHaveAttribute('href', '/ixp/za')  // PTT onde aparece (documento da origem)
    expect(screen.getByText(/Alocação do Registro.br:/)).toBeInTheDocument()
    expect(screen.getByText('centro do município')).toBeInTheDocument()
    expect(screen.getAllByTestId('proveniencia').length).toBeGreaterThanOrEqual(5)
  })

  it('inválido por ROA de outro AS: a coluna "AS autorizado" é o AS do ROA, não o da página (PFX-E4)', async () => {
    montar('/prefixo/2001:db8:3e80::/48')
    expect(await screen.findByTestId('rpki-estado')).toHaveTextContent('inválido')
    const tabela = screen.getByRole('table', { name: /ROAs que cobrem/ })
    expect(tabela).toHaveTextContent('AS64510')
    expect(tabela).not.toHaveTextContent('AS64511')
    expect(tabela).toHaveTextContent('não')
    expect(screen.getByTestId('rpki-diagnostico')).toHaveTextContent('autorizam AS64510; a origem observada é AS64511')
    expect(screen.queryByText(/Nenhum ROA/)).toBeNull()
  })

  it('rota observada fora do Registro.br abre, sem detentor (PFX-E5)', async () => {
    montar('/prefixo/100.64.0.0/24')
    expect(await screen.findByText('Rota anunciada, fora das alocações do Registro.br')).toBeInTheDocument()
    expect(screen.getByTestId('detentor')).toHaveTextContent('não consta das alocações do Registro.br')
    expect(screen.getByTestId('origem-observada')).toHaveTextContent('AS4200000100')
  })

  it('grafia não canônica redireciona para a canônica e avisa, sem pedir a grafia antiga à API (PFX-E5)', async () => {
    montar('/prefixo/198.18.0.5/24')
    expect(await screen.findByTestId('aviso-canonico')).toHaveTextContent('Mostrando 198.18.0.0/24, a forma canônica de “198.18.0.5/24”.')
    montar('/prefixo/2001:0DB8:3E80:0000::/48')
    await waitFor(() => expect(screen.getAllByTestId('aviso-canonico')).toHaveLength(2))
    expect(pedidos).not.toContain('198.18.0.5/24')
    expect(pedidos).toContain('2001:db8:3e80::/48')
  })

  it('prefixo malformado explica sem chamar a API, com exemplos que abrem', async () => {
    montar('/prefixo/abc')
    expect(await screen.findByText('Prefixo inválido')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '2804::/32' })).toHaveAttribute('href', '/prefixo/2804::/32')
    expect(screen.queryByRole('link', { name: '177.75.0.0/16' })).toBeNull()
    expect(pedidos).toEqual([])
  })

  it('prefixo ausente: "não encontrado" com o limite da coleta; falha da API não vira "não encontrado"', async () => {
    montar('/prefixo/203.0.113.0/24')
    expect(await screen.findByText('Prefixo não encontrado')).toBeInTheDocument()
    expect(screen.getByText(/isso não prova que não seja anunciado/)).toBeInTheDocument()
    montar('/prefixo/198.51.100.0/24')
    expect(await screen.findByText('Falha ao carregar')).toBeInTheDocument()
    expect(screen.getAllByText('Prefixo não encontrado')).toHaveLength(1)
  })

  it('MOAS: só baixa a análise (14 MB) quando o usuário pede e lista as origens com os coletores (PFX-E3)', async () => {
    let chamadas = 0
    server.use(http.get('*/api/v1/routing-analysis', () => { chamadas += 1; return HttpResponse.json(analiseComMoas) }))
    montar('/prefixo/198.18.0.0/24')
    const botao = await screen.findByRole('button', { name: /Verificar na análise de roteamento/ })
    expect(chamadas).toBe(0)
    fireEvent.click(botao)
    const bloco = await screen.findByTestId('moas-observado')
    expect(bloco.textContent).toMatch(/2 ASes de origem/)
    expect(bloco.textContent).toMatch(/vista em 2 coletores \(rvT, rvU\)/)
    // o AS64497 também aparece como detentor (PT-07); aqui interessa o link dentro do bloco de MOAS
    expect(within(bloco).getByRole('link', { name: 'AS64497' })).toHaveAttribute('href', '/asn/64497?date=2026-09-20')
    expect(bloco.textContent).not.toMatch(/sequestro|hijack/i)
    expect(chamadas).toBe(1)
  })

  it('MOAS medido sem o prefixo: "nenhuma observada", com o número de coletores', async () => {
    server.use(http.get('*/api/v1/routing-analysis', () => HttpResponse.json({ ...analiseComMoas, moas: [] })))
    montar('/prefixo/198.18.0.0/24')
    fireEvent.click(await screen.findByRole('button', { name: /Verificar na análise de roteamento/ }))
    expect((await screen.findByTestId('moas-nenhum')).textContent).toMatch(/Nenhuma origem múltipla \(MOAS\) observada para este prefixo exato neste snapshot, entre 2 coletores/)
  })

  it('MOAS não medido no snapshot: aviso de limite da coleta, sem afirmar ausência', async () => {
    server.use(http.get('*/api/v1/routing-analysis', () => HttpResponse.json({ moas: null, moas_resumo: null, moas_indisponivel: MOAS_INDISPONIVEL })))
    montar('/prefixo/198.18.0.0/24')
    fireEvent.click(await screen.findByRole('button', { name: /Verificar na análise de roteamento/ }))
    const aviso = await screen.findByTestId('moas-indisponivel')
    expect(aviso.textContent).toMatch(/não medida neste snapshot/)
    expect(aviso.textContent).toMatch(/limite da coleta, não ausência de eventos/)
    expect(document.body.textContent).not.toMatch(/Nenhuma origem múltipla/)
  })

  it('MOAS com falha da API: EstadoDados, nunca "nenhuma"', async () => {
    server.use(http.get('*/api/v1/routing-analysis', () => new HttpResponse('erro', { status: 500 })))
    montar('/prefixo/198.18.0.0/24')
    fireEvent.click(await screen.findByRole('button', { name: /Verificar na análise de roteamento/ }))
    const falha = await screen.findByText(/Não foi possível carregar a análise de roteamento/)
    expect(falha.closest('[data-estado]')).toHaveAttribute('data-estado', 'falha')
    expect(document.body.textContent).not.toMatch(/Nenhuma origem múltipla/)
  })
})

describe('busca global aceita prefixo', () => {
  it('Enter com um CIDR leva à página do prefixo', async () => {
    let destino = ''
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={['/']}>
          <SearchBar />
          <Routes><Route path="/prefixo/*" element={<div data-testid="alvo">{(destino = 'ok')}</div>} /><Route path="*" element={null} /></Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    const campo = screen.getByPlaceholderText(/prefixo/)
    fireEvent.change(campo, { target: { value: '177.75.0.0/16' } })
    fireEvent.keyDown(campo, { key: 'Enter' })
    expect(await screen.findByTestId('alvo')).toBeInTheDocument()
    expect(destino).toBe('ok')
  })
})
