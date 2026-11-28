// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** UF 5.5: "Usuários estimados" saiu do painel do topo e mora na aba Rede, com a parcela do Brasil e o aviso de que conta na UF da sede. */
import type { ReactElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { server } from '../../../test/server'
import { useAppStore } from '../../../store/app'
import type { UfCtx } from '../contexto'
import { UsuariosSedeUfBloco } from './UsuariosSedeUfBloco'
import { PainelBloco } from './PainelBloco'

const dados = { uf: 'AM', ixps: [], municipios: [], semCentroides: true, totais: { municipios: 62, acessos: 724373, fibra_pct: 66.9, asns: 110, usuarios: 1000, municipios_sem_ptt: 0, acessos_sem_ptt: 0, raio_sem_ptt_km: 100 },
  operadoras: [], operadorasTotal: 0, operadorasPresentes: [], operadorasPresentesTotal: 0 } as unknown as UfCtx

const montar = (ui: ReactElement) => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>)

beforeEach(() => {
  useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' })
  server.use(http.get('*/api/v1/ufs', () => HttpResponse.json({ snapshot_date: '2026-09-20', total: 2, items: [
    { uf: 'AM', ptts: 1, municipios: 62, acessos: 1, fibra_pct: 1, asns: 110, usuarios: 1000, municipios_sem_ptt: 0 },
    { uf: 'SP', ptts: 9, municipios: 600, acessos: 1, fibra_pct: 1, asns: 900, usuarios: 3000, municipios_sem_ptt: 0 },
  ] })))
})

describe('usuários estimados na aba Rede', () => {
  it('mostra o número, a parcela das 27 UFs e que conta na UF da sede, não na população conectada', async () => {
    montar(<UsuariosSedeUfBloco dados={dados} snapshot="2026-09-20" />)
    expect(screen.getByText('Usuários estimados em ASNs sediados na UF')).toBeInTheDocument()
    expect(await screen.findByText(/25% do total das 27 UFs \(4\.000\)/)).toBeInTheDocument()
    expect(screen.getByText(/Conta na UF da sede do ASN; não é a população conectada/)).toBeInTheDocument()
  })
  it('o painel do topo não tem mais o cartão de usuários estimados', () => {
    montar(<PainelBloco dados={dados} snapshot="2026-09-20" />)
    expect(screen.queryByText(/Usuários estimados/)).toBeNull()
    expect(screen.getByText('Acessos fixos')).toBeInTheDocument()
  })
})
