// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { server } from '../test/server'
import { useAppStore } from '../store/app'
import { CDNPage } from './CDNPage'

beforeEach(() => {
  useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' })
  server.use(
    http.get('*/api/v1/cdns/presence', () => HttpResponse.json({
      snapshot_date: '2026-09-20',
      cdns: [{ name: 'Exemplo CDN', categorias: ['CDN'], asns: [64500], ixbr: ['sp'], external: [], ixbr_count: 1, external_count: 0 }],
      ixbr_columns: [{ code: 'sp', name: 'São Paulo', cdn_count: 1 }, { code: 'rj', name: 'Rio de Janeiro', cdn_count: 0 }],
      external_columns: [],
    })),
    http.get('*/api/v1/external-ixps', () => HttpResponse.json({ snapshot_date: '2026-09-20', total: 0, ixps: [] })),
  )
})

const montar = () => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter><CDNPage /></MemoryRouter>
  </QueryClientProvider>,
)

describe('/cdns: grade e controles acessíveis (CDNS-E7, SEG-E1)', () => {
  it('a grade tem caption, cabeçalhos com scope e estado de cada célula em texto', async () => {
    montar()
    const tabela = await screen.findByRole('table', { name: /Estado de cada CDN/ })
    expect(tabela.querySelector('caption')).toHaveTextContent(/Estado de cada CDN/)
    for (const th of tabela.querySelectorAll('thead th')) expect(th).toHaveAttribute('scope', 'col')
    expect(within(tabela).getByRole('rowheader', { name: /Exemplo CDN/ })).toBeInTheDocument()
    expect(within(tabela).getByText('Exemplo CDN em São Paulo: membro (cadastro ou PeeringDB), sem detalhe de sessão')).toBeInTheDocument()
    expect(within(tabela).getByText('Exemplo CDN em Rio de Janeiro: não membro, sem prefixos observados')).toBeInTheDocument()
    // região e contagem fora do title
    expect(within(tabela).getByText(/IX\.br \(Brasil\) · 1 CDNs/)).toBeInTheDocument()
  })

  it('botões de filtro anunciam o estado com aria-pressed', async () => {
    montar()
    await screen.findByRole('table', { name: /Estado de cada CDN/ })
    const ixbr = screen.getByRole('button', { name: /^IX\.br/ })
    expect(ixbr).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(ixbr)
    expect(ixbr).toHaveAttribute('aria-pressed', 'false')
    const cat = screen.getByRole('button', { name: 'CDN' })
    expect(cat).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(cat)
    expect(cat).toHaveAttribute('aria-pressed', 'false')
  })
})

describe('/cdns: três estados por célula (PT-24 / CDNS-E5.1)', () => {
  const doc = {
    snapshot_date: '2026-11-22',
    cdns: [
      { name: 'Cloudflare', categorias: ['CDN'], asns: [13335], ixbr: ['sp', 'rj'], external: [], ixbr_count: 2, external_count: 0, ixbr_rs: ['sp'], ixbr_sem_rs: ['rj'], ixbr_origem: ['ba'], ixbr_sem_coleta: [], asns_sem_documento: [], sem_rs_em_nenhum_ptt: false },
      { name: 'Microsoft / Azure', categorias: ['Cloud'], asns: [8075], ixbr: ['sp'], external: [], ixbr_count: 1, external_count: 0, ixbr_rs: [], ixbr_sem_rs: ['sp'], ixbr_origem: [], ixbr_sem_coleta: [], asns_sem_documento: [], sem_rs_em_nenhum_ptt: true },
      { name: 'X / Twitter', categorias: ['Social'], asns: [13414], ixbr: [], external: [], ixbr_count: 0, external_count: 0, ixbr_rs: [], ixbr_sem_rs: [], ixbr_origem: ['sp', 'rj'], ixbr_sem_coleta: [], asns_sem_documento: [], sem_rs_em_nenhum_ptt: false },
    ],
    ixbr_columns: [{ code: 'sp', name: 'São Paulo', cdn_count: 2 }, { code: 'rj', name: 'Rio de Janeiro', cdn_count: 1 }, { code: 'ba', name: 'Salvador', cdn_count: 0 }],
    external_columns: [],
    estados_limites: 'Membro é o ASN listado como participante do PTT pelo IX.br. Sessão no route server é observada no looking glass.',
  }
  const abrir = async () => { server.use(http.get('*/api/v1/cdns/presence', () => HttpResponse.json(doc))); montar(); return within(await screen.findByRole('table', { name: /Estado de cada CDN/ })) }

  it('cada estado tem texto e forma própria e a sessão não é confundida com cadastro', async () => {
    const t = await abrir()
    expect(t.getByText('Cloudflare em São Paulo: membro, com sessão no route server')).toBeInTheDocument()
    expect(t.getByText('Cloudflare em Rio de Janeiro: membro, sem sessão no route server observada')).toBeInTheDocument()
    expect(t.getByText('Cloudflare em Salvador: não membro; prefixos vistos no PTT por outro participante')).toBeInTheDocument()
    expect(t.getByText('Microsoft / Azure em São Paulo: membro, sem sessão no route server observada')).toBeInTheDocument()
    const simbolos = Array.from(document.querySelectorAll('tbody td [aria-hidden="true"]')).map((e) => e.textContent)
    expect(new Set(simbolos.filter((x) => x !== '·'))).toEqual(new Set(['●', '◐', '◇']))          // forma distinta por estado: não depende de cor
  })

  it('"Membro", "Com route server" e "Só via outro AS" são colunas distintas e CDN sem membro (X / Twitter) tem linha visível', async () => {
    const t = await abrir()
    const cab = t.getAllByRole('columnheader').map((c) => c.textContent)
    expect(cab).toEqual(expect.arrayContaining([expect.stringMatching(/Membro/), expect.stringMatching(/Com route server/), expect.stringMatching(/Só via outro AS/)]))
    const linha = (nome: string) => t.getByRole('rowheader', { name: new RegExp(nome) }).closest('tr')!
    const ultimas = (tr: HTMLElement) => Array.from(tr.querySelectorAll('td')).slice(-3).map((td) => td.textContent)
    expect(ultimas(linha('Cloudflare'))).toEqual(['2', '1', '1'])                                  // membro 2, com RS 1, só via outro AS 1 (BA)
    expect(ultimas(linha('Microsoft'))).toEqual(['1', '0', '0'])
    expect(ultimas(linha('Twitter'))).toEqual(['0', '0', '2'])
  })

  it('o fato "sem sessão em route server em nenhum PTT" aparece sem adjetivo e a legenda traz selos e a ressalva de sessões bilaterais', async () => {
    await abrir()
    expect(screen.getByRole('rowheader', { name: /Microsoft/ }).textContent).toContain('sem sessão em route server em nenhum PTT do IX.br')
    const legenda = screen.getByTestId('legenda-estados')
    expect(legenda.textContent).toMatch(/Inferido · .*prefixos da CDN vistos no PTT/)
    expect(legenda.textContent).toMatch(/Fato · .* ref\. 2026-11-22/)
    expect(legenda.textContent).toMatch(/sessões bilaterais/)
    expect(document.body.textContent).not.toMatch(/sem peering|não troca tráfego|oportunidade/i)
  })
})
