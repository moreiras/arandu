// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { server } from '../test/server'
import { useAppStore } from '../store/app'
import { GruposPage } from './GruposPage'

// Mapas usam MapLibre (WebGL), que o jsdom não tem.
vi.mock('../components/acessos/AccessMunicipioMap', () => ({ AccessMunicipioMap: () => <div /> }))
vi.mock('../components/socios/GrupoPrefixosGeoMap', () => ({ GrupoPrefixosGeoMap: () => <div /> }))
vi.mock('../auth/AuthContext', async (original) => ({
  ...(await original<typeof import('../auth/AuthContext')>()),
  useAuth: () => ({ user: null, anon: null, loading: false, loginPrompt: null, requireLogin: () => true, closeLoginPrompt: () => {} }),
}))

const cnpj = (n: number, empresa: string, asns?: number[]) => ({ cnpj: `9000000${n}000129`, empresa, assinantes: 10, asns, has_scm: true })
const grupo = (id: string, nome: string, tamanho: number, assinantes: number, asns?: number[]) => ({
  grupo_id: id, classificacao: 'total', tamanho, assinantes, usuarios_apnic: 0, visibilidade_bgp: true,
  cnpjs: Array.from({ length: tamanho }, (_, i) => cnpj(i + 1, i === 0 ? nome : `${nome} ${i}`, i === 0 ? asns : undefined)), municipios: [],
})

beforeEach(() => {
  useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' })
  server.use(
    http.get('*/api/v1/grupos', () => HttpResponse.json({ snapshot_date: '2026-09-20', total: 2, grupos: [
      grupo('g1', 'ALFA TELECOM', 3, 5000, [64500, 64501]), grupo('g2', 'BETA NET', 2, 100),
    ] })),
    http.get('*/api/v1/grupos/:id/prefixos-geo', () => HttpResponse.json({ snapshot_date: '2026-09-20', grupo_id: 'g1', prefixos: [] })),
  )
})

const montar = () => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter initialEntries={['/grupos']}><GruposPage /></MemoryRouter>
  </QueryClientProvider>,
)

describe('/grupos: seleção por teclado e controles com estado (GRUPOS-E2, OPERADORA-E4, OPERADORA-E5)', () => {
  it('"Ver no mapa" é botão nativo (Enter e Espaço) que seleciona a linha, com aria-pressed e anúncio', async () => {
    montar()
    const tabela = await screen.findByRole('table', { name: 'Grupos econômicos' })
    const beta = within(tabela).getByRole('button', { name: 'Ver no mapa: BETA NET' })
    // <button type="button">: o navegador ativa com Enter e Espaço e o põe na ordem de tabulação (o <tr onClick> não tinha nada disso)
    expect(beta.tagName).toBe('BUTTON')
    expect(beta).toHaveAttribute('type', 'button')
    expect(beta).toHaveAttribute('aria-pressed', 'false')
    fireEvent.click(beta)
    expect(beta).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByTestId('grupo-selecionado')).toHaveTextContent('Grupo selecionado: BETA NET, 2 empresas')
    const alfa = within(tabela).getByRole('button', { name: 'Ver no mapa: ALFA TELECOM' })
    fireEvent.click(alfa)
    expect(alfa).toHaveAttribute('aria-pressed', 'true')
    expect(beta).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByTestId('grupo-selecionado')).toHaveTextContent('Grupo selecionado: ALFA TELECOM, 3 empresas')
  })

  it('busca com rótulo e escopo com aria-pressed', async () => {
    montar()
    await screen.findByRole('table', { name: 'Grupos econômicos' })
    expect(screen.getByRole('searchbox', { name: /Buscar/ })).toBeInTheDocument()
    const escopo = screen.getByRole('group', { name: 'Escopo da tabela' })
    const botoes = within(escopo).getAllByRole('button')
    expect(botoes.filter((b) => b.getAttribute('aria-pressed') === 'true')).toHaveLength(1)
    const outro = botoes.find((b) => b.getAttribute('aria-pressed') === 'false')!
    fireEvent.click(outro)
    expect(outro).toHaveAttribute('aria-pressed', 'true')
  })

  it('os números de "ASN ×N" ficam em texto, não só no title', async () => {
    montar()
    const tabela = await screen.findByRole('table', { name: 'Grupos econômicos' })
    expect(within(tabela).getByText(/AS64500, AS64501/)).toHaveClass('sr-only')
  })
})
