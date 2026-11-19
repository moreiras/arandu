// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'

function Onde() { const l = useLocation(); return <div data-testid="onde">{l.pathname}{l.search}</div> }
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../test/server'
import { RankingsPage, RankingsSici } from './RankingsPage'

vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ anon: { id: 'x' }, loading: false }) }))

const meta = { snapshot_date: '2026-10-31', mes_referencia: '2026-08', fonte: 'Anatel/SICI', metodologia: '/fontes', escopo: { pais: 'BR' } }
// o conteúdo mora em outras páginas; `/rankings` só redireciona
const montar = (aba: 'operadoras' | 'omissao' | 'route-servers' = 'operadoras') => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><RankingsSici abaFixa={aba} /></MemoryRouter></QueryClientProvider>,
)

describe('página Rankings do SICI', () => {
  it('mostra critério, mês de referência e a lista de operadoras, e avisa a quem não tem login', async () => {
    server.use(http.get('*/api/v1/ranking/operadoras', () => HttpResponse.json({
      ...meta, criterio: 'Acessos declarados (decrescente)', total: 90,
      items: [{ posicao: 1, cnpj: '02558157000162', empresa: 'VIVO', uf_sede: 'SP', acessos: 8542210, share: 14.755, meses_declinio: 0, em_declinio: false, var_aa_pct: 9.46 }],
    })))
    montar()
    await waitFor(() => expect(screen.getByText('VIVO').getAttribute('href')).toBe('/operadora/02558157000162'))
    expect(screen.getByTestId('rotulo-ranking').textContent).toContain('Critério: Acessos declarados (decrescente)')
    expect(screen.getByTestId('rotulo-ranking').textContent).toContain('2026-08')
    expect(screen.getByText(/Sem login você vê os 25 primeiros/)).toBeTruthy()
    expect(screen.getByText(/Não indica causa nem intenção/i)).toBeTruthy()
  })

  it('na aba de omissão descreve o fato, com usuários estimados e a marca do grupo, sem juízo', async () => {
    server.use(http.get('*/api/v1/omissao-sici', () => HttpResponse.json({
      ...meta, criterio: 'Usuários estimados (APNIC) dos ASNs do CNPJ (decrescente)', tipo: 'outorga_sem_declaracao', total: 1, parametros: { usuarios_min: 100 },
      items: [{ posicao: 1, cnpj: '39565567000140', razao_social: 'BTT TELECOMUNICACOES S.A.', uf: 'MG', usuarios_apnic: 367660, classe: 'com_usuarios_apnic', grupo_declara: true, asns: [28656] }],
    })))
    montar('omissao')
    await waitFor(() => expect(screen.getByText('BTT TELECOMUNICACOES S.A.')).toBeTruthy())
    expect(screen.getByText('367.660')).toBeTruthy()
    expect(screen.getByText('com usuários estimados (APNIC)', { selector: 'td' })).toBeTruthy()
    expect(screen.getByText('outro CNPJ do grupo declarou')).toBeTruthy()
    const corpo = document.body.textContent ?? ''
    expect(corpo).not.toMatch(/sonegou|omitiu|irregular/i)
  })

  it('as abas territoriais viraram a lista de municípios: o link antigo redireciona com a lente certa (alias)', async () => {
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter initialEntries={['/rankings?aba=penetracao&uf=SP']}>
      <Routes><Route path="/rankings" element={<RankingsPage />} /><Route path="/municipios" element={<Onde />} /></Routes></MemoryRouter></QueryClientProvider>)
    expect(await screen.findByTestId('onde')).toHaveTextContent('/municipios?uf=SP&lente=penetracao')
  })

  it('os links antigos de operadoras, omissão e route servers redirecionam para o lugar novo (alias)', async () => {
    const ir = async (url: string) => {
      const { unmount } = render(<QueryClientProvider client={new QueryClient()}><MemoryRouter initialEntries={[url]}>
        <Routes><Route path="/rankings" element={<RankingsPage />} /><Route path="*" element={<Onde />} /></Routes></MemoryRouter></QueryClientProvider>)
      const t = (await screen.findByTestId('onde')).textContent; unmount(); return t
    }
    expect(await ir('/rankings')).toBe('/operadoras?visao=ranking')
    expect(await ir('/rankings?aba=omissao&uf=MG')).toBe('/operadoras?visao=omissao&uf=MG')
    expect(await ir('/rankings?aba=route-servers&ixp=sp')).toBe('/ixps?visao=route-servers&ixp=sp')
  })

  it('na aba Route servers lista o número medido, sem adjetivo, com o PTT, a data da coleta e o aviso do route server incerto', async () => {
    let pedido = ''
    server.use(http.get('*/api/v1/ranking/route-servers', ({ request }) => {
      pedido = new URL(request.url).search
      return HttpResponse.json({ snapshot_date: '2026-10-31', coletado_em: '2026-10-31T22:54:20Z', fonte: 'x', versao_alice: '6.1.0', parametros: { dias_down: 7, uso_limite: 0.8, idade_max_vizinhos_h: 24 },
        limites: 'Estado do route server no instante da coleta.', criterio: 'sessões down no route server (número absoluto), com o total de sessões do membro ao lado (decrescente)',
        escopo: { pais: 'BR' }, filtros: { apenas_down: false }, total: 1,
        items: [{ posicao: 1, ixp: 'sp', asn: 64496, nome: 'REDE EXEMPLO A', sessoes: 4, up: 1, down: 3, down_certo: 1, max_dias_down: 205, max_uso_limite: null, membro_down: false, rs_incerto: 1 }] })
    }))
    montar('route-servers')
    await waitFor(() => expect(screen.getByText('AS64496').getAttribute('href')).toBe('/asn/64496'))
    expect(screen.getByText('SP').getAttribute('href')).toBe('/ixp/sp')
    expect(screen.getByText('1 de 4')).toBeTruthy()
    expect(screen.getByTestId('rotulo-ranking').textContent).toContain('Route servers do IX.br, coletado em 2026-10-31')
    expect(screen.getByText(/\(\+2 em RS sem frescor confirmado\)/)).toBeTruthy()
    expect(pedido).toContain('criterio=sessoes_down')
    expect(document.body.textContent).not.toMatch(/pior|melhor|culpa|irregular/i)
  })
})
