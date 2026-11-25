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
import { REGIOES, UFS } from '../lib/ufs'
import { vi } from 'vitest'
import { EstadosPage } from './EstadosPage'

// O mapa dos municípios usa MapLibre (WebGL), que o jsdom não tem: ele tem teste próprio, com o mapa trocado por um duplo.
vi.mock('../features/estados/MapaMunicipios', () => ({ default: () => <div data-testid="mapa-municipios-duplo" /> }))

const montar = () => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter><EstadosPage /></MemoryRouter>
  </QueryClientProvider>,
)

beforeEach(() => {
  useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' })
  const linha = (uf: string, ptts: number, acessos: number, fibra: number | null, usuarios: number) =>
    ({ uf, ptts, municipios: 10, acessos, fibra_pct: fibra, asns: 5, usuarios, municipios_sem_ptt: 0 })
  server.use(http.get('*/api/v1/ufs', () => HttpResponse.json({ snapshot_date: '2026-09-20', mes_referencia: '2026-08', total: 3, items: [
    linha('SP', 2, 9_000_000, 82.4, 40_000_000), linha('ES', 1, 1_200_000, 70, 3_000_000), linha('AC', 0, 90_000, null, 500_000),
  ] })))
})

describe('regiões', () => {
  it('cobrem as 27 UFs, cada uma uma vez', () => {
    const todas = REGIOES.flatMap((r) => r.ufs)
    expect(todas).toHaveLength(27)
    expect(new Set(todas)).toEqual(new Set(Object.keys(UFS)))
  })
})

describe('página Estados', () => {
  it('lista as 27 UFs com link para /uf/<sigla> e o número de PTTs', async () => {
    montar()
    expect(screen.getByRole('heading', { level: 1, name: 'Estados' })).toBeInTheDocument()
    expect(screen.getAllByRole('link')).toHaveLength(27)      // o cartograma é decorativo (aria-hidden): a lista é o caminho por teclado
    const sp = screen.getByRole('link', { name: /São Paulo/ })
    expect(sp).toHaveAttribute('href', '/uf/SP')
    expect(await within(sp).findByText('2 PTTs')).toBeInTheDocument()
    expect(within(sp).getByText(/9\.000\.000 acessos fixos · 40\.000\.000 usuários est\./)).toBeInTheDocument()
    expect(within(sp).getByText('82% fibra')).toBeInTheDocument()
    expect(within(screen.getByRole('link', { name: /Espírito Santo/ })).getByText('1 PTT')).toBeInTheDocument()
    expect(within(screen.getByRole('link', { name: /Acre/ })).getByText('nenhum PTT do IX.br na UF')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Sudeste' })).toBeInTheDocument()
  })

  it('erro na lista de PTTs não derruba a grade', async () => {
    server.use(http.get('*/api/v1/ufs', () => new HttpResponse('boom', { status: 500 })))
    montar()
    expect(await within(screen.getByRole('link', { name: /Bahia/ })).findByText('—')).toBeInTheDocument()
    expect(screen.getAllByRole('link')).toHaveLength(27)
  })
})

describe('PTT sem coleta e snapshot sem SICI (EST-E1, EST-E2)', () => {
  it('PTT sem coleta conta na UF com a ressalva; sem SICI não vira "0 acessos fixos"', async () => {
    server.use(http.get('*/api/v1/ufs', () => HttpResponse.json({ snapshot_date: '2026-08-30', mes_referencia: null, total: 1, items: [
      { uf: 'AP', ptts: 1, ptts_com_coleta: 0, municipios: null, acessos: null, fibra_pct: null, asns: 30, usuarios: 400_000, municipios_sem_ptt: null },
    ] })))
    montar()
    const ap = screen.getByRole('link', { name: /Amapá/ })
    expect(await within(ap).findByText('1 PTT (0 com coleta neste snapshot)')).toBeInTheDocument()
    expect(within(ap).getByText(/sem SICI neste snapshot · 400\.000 usuários est\./)).toBeInTheDocument()
    expect(within(ap).queryByText(/0 acessos fixos/)).toBeNull()
    expect(screen.queryByText('sem PTT na UF')).toBeNull()
  })
})

describe('cartograma', () => {
  it('uma célula por UF, trocar a métrica muda o rótulo das células', async () => {
    montar()
    const grade = await screen.findByTestId('cartograma')
    expect(grade.querySelectorAll('a')).toHaveLength(27)
    expect(within(grade).getByTitle(/^SP: 9 mi/)).toBeInTheDocument()
    screen.getByRole('button', { name: '% de fibra' }).click()
    expect(await within(grade).findByTitle(/^SP: 82%/)).toBeInTheDocument()
  })
})

describe('mapa dos municípios sob demanda', () => {
  it('não carrega o mapa até a pessoa pedir; depois de pedir, mostra', async () => {
    montar()
    expect(screen.queryByTestId('mapa-municipios-duplo')).toBeNull()
    expect(screen.getByRole('heading', { name: 'Mapa dos municípios' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Mostrar o mapa' }))
    expect(await screen.findByTestId('mapa-municipios-duplo')).toBeInTheDocument()
  })
})

describe('alternativa textual do cartograma (EST-E7)', () => {
  it('"Ver dados" traz uma linha por UF com todas as métricas, ordenável', async () => {
    montar()
    const ver = await screen.findByTestId('ver-dados')
    ;(ver as HTMLDetailsElement).open = true
    const tabela = within(ver).getByRole('table', { name: 'Ver dados (tabela das UFs)' })
    const cab = within(tabela).getAllByRole('columnheader').map((th) => th.textContent?.replace(/[▲▼↕]/g, '').trim())
    expect(cab).toEqual(['UF', 'Nome', 'Acessos fixos (SICI)', 'Fibra (% dos acessos)', 'Usuários estimados em ASNs sediados na UF (APNIC)', 'PTTs (IX.br)',
      'Acessos / 100 domicílios', 'Municípios longe de PTT (%)', 'Municípios com acessos', 'ASNs'])
    const linhas = within(tabela).getAllByRole('row').slice(1)
    expect(linhas.map((l) => l.querySelector('td')?.textContent)).toEqual(['AC', 'ES', 'SP'])
    expect(linhas[2]).toHaveTextContent('São Paulo')
    expect(linhas[2]).toHaveTextContent('9.000.000')
    expect(linhas[2]).toHaveTextContent('82,4')
    fireEvent.click(within(tabela).getByRole('button', { name: 'Acessos fixos (SICI)' }))
    expect(within(tabela).getByRole('columnheader', { name: /Acessos fixos \(SICI\)/ })).toHaveAttribute('aria-sort', expect.stringMatching(/ascending|descending/))
  })
})
