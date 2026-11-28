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
  const linha = (uf: string, ptts: number, acessos: number, fibra: number | null, usuarios: number, extra: Record<string, unknown> = {}) =>
    ({ uf, ptts, municipios: 10, acessos, fibra_pct: fibra, asns: 5, usuarios, municipios_sem_ptt: 0, ...extra })
  const rede = (o: Record<string, number | null>) => ({ ipv6_pct: null, ipv6_cobertura: null, rov_pct: null, rov_cobertura: null, transito_unico_pct: null, transito_unico_cobertura: null,
    hhi_transito: null, hhi_transito_n: null, prontidao_mediana: null, prontidao_n: null, ...o })
  server.use(http.get('*/api/v1/ufs', () => HttpResponse.json({ snapshot_date: '2026-09-20', mes_referencia: '2026-08', total: 3, items: [
    linha('SP', 2, 9_000_000, 82.4, 40_000_000, { rede: rede({ prontidao_mediana: 50.7, prontidao_n: 1863, hhi_transito: 157, hhi_transito_n: 1992, ipv6_pct: 41.2, rov_pct: 63, transito_unico_pct: 30 }), territorio: { nao_visto: 4_000_000, nao_visto_por_100_dom: 16.4 } }),
    linha('ES', 1, 1_200_000, 70, 3_000_000, { rede: rede({ prontidao_mediana: 61.7, prontidao_n: 77, hhi_transito: 1938, hhi_transito_n: 19 }), territorio: { nao_visto: 300_000, nao_visto_por_100_dom: 22 } }),
    linha('AC', 0, 90_000, null, 500_000, { rede: null, territorio: null }),
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

describe('camada de rede e mercado não visto no cartograma (estados 5.4)', () => {
  const botoes = () => within(screen.getByRole('group', { name: 'Infraestrutura e rede' })).getAllByRole('button').map((b) => b.textContent)

  it('os botões ficam nos grupos Mercado e Infraestrutura e rede, com o selo no nome, e IPv6 vem como indicador de rede', async () => {
    montar()
    await screen.findByTestId('cartograma')
    expect(botoes()).toEqual(expect.arrayContaining([
      '% de acessos com um só provedor de trânsito (inferido)', '% de acessos em IPv6 (estimado)', '% de usuários atrás de ROV (estimado)',
      'Prontidão em segurança de roteamento (mediana)', 'HHI do trânsito']))
    expect(within(screen.getByRole('group', { name: 'Mercado' })).getByRole('button', { name: 'Mercado não visto por 100 domicílios (estimado)' })).toBeInTheDocument()
  })

  it('prontidão e HHI abertos, com o n na célula e no título, e sem borda tracejada nem regra de base pequena', async () => {
    montar()
    const grade = await screen.findByTestId('cartograma')
    fireEvent.click(screen.getByRole('button', { name: 'Prontidão em segurança de roteamento (mediana)' }))
    expect(within(grade).getByTitle(/^SP: 50,7; n=1\.863/)).toBeInTheDocument()
    expect(within(grade).getByTitle(/^ES: 61,7; n=77/)).toBeInTheDocument()      // base de 77: aparece como as outras, só com o n
    expect(within(grade).getByTitle(/^AC: sem dado/)).toBeInTheDocument()
    expect(grade.innerHTML).not.toMatch(/dashed|base pequena/)
    fireEvent.click(screen.getByRole('button', { name: 'HHI do trânsito' }))
    expect(within(grade).getByTitle(/^SP: 157; n=1\.992/)).toBeInTheDocument()
    expect(within(grade).getByTitle(/^ES: 1\.938; n=19/)).toBeInTheDocument()
  })

  it('o aviso de que não é veredito nem ranking fica visível, sem expandir nada', async () => {
    montar()
    await screen.findByTestId('cartograma')
    const aviso = screen.getByTestId('aviso-rede-ufs')
    expect(aviso).toBeVisible()
    expect(aviso.closest('details')).toBeNull()
    expect(aviso).toHaveTextContent(/não são veredito sobre a segurança nem sobre o mercado de um estado e não devem ser lidos como ranking/)
    expect(aviso).toHaveTextContent(/a UF é a da sede das redes/)
  })

  it('a tabela traz as colunas de prontidão e HHI com o n ao lado, e o mercado não visto', async () => {
    montar()
    const ver = await screen.findByTestId('ver-dados')
    ;(ver as HTMLDetailsElement).open = true
    const tabela = within(ver).getByRole('table', { name: 'Ver dados (tabela das UFs)' })
    const sp = within(tabela).getAllByRole('row').find((l) => l.querySelector('td')?.textContent === 'SP')!
    expect(sp).toHaveTextContent('50,7')
    expect(sp).toHaveTextContent('1.863')
    expect(sp).toHaveTextContent('157')
    expect(sp).toHaveTextContent('1.992')
    expect(sp).toHaveTextContent('16,4')
    const ac = within(tabela).getAllByRole('row').find((l) => l.querySelector('td')?.textContent === 'AC')!
    expect(within(ac).getAllByText('—').length).toBeGreaterThanOrEqual(7)        // UF sem linha de rede: ausência, nunca zero
  })

  it('sem posição ordinal: nenhum ranking nem "posição" nos indicadores de rede', async () => {
    montar()
    await screen.findByTestId('cartograma')
    fireEvent.click(screen.getByRole('button', { name: 'HHI do trânsito' }))
    expect(screen.queryByText(/posição \d|\d+º de/i)).toBeNull()
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
      'Acessos / 100 domicílios', 'Municípios longe de PTT (%)', 'Municípios com acessos', 'ASNs',
      'Acessos com um só provedor de trânsito (% inferido)', 'Acessos em IPv6 (% estimado)', 'Usuários atrás de ROV (% estimado)',
      'Prontidão (mediana do índice dos ASNs)', 'n da prontidão (ASNs com índice)', 'HHI do trânsito (0 a 10.000)', 'n do HHI (ASNs com provedor inferido)',
      'Mercado não visto / 100 domicílios (estimado)'])
    const linhas = within(tabela).getAllByRole('row').slice(1)
    expect(linhas.map((l) => l.querySelector('td')?.textContent)).toEqual(['AC', 'ES', 'SP'])
    expect(linhas[2]).toHaveTextContent('São Paulo')
    expect(linhas[2]).toHaveTextContent('9.000.000')
    expect(linhas[2]).toHaveTextContent('82,4')
    fireEvent.click(within(tabela).getByRole('button', { name: 'Acessos fixos (SICI)' }))
    expect(within(tabela).getByRole('columnheader', { name: /Acessos fixos \(SICI\)/ })).toHaveAttribute('aria-sort', expect.stringMatching(/ascending|descending/))
  })
})
