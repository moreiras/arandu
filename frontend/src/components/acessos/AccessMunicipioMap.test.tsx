// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { render, screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

// MapLibre falso (jsdom não tem WebGL): o componente monta sem desenhar
vi.mock('maplibre-gl', () => {
  class Ctl { }
  class Map { addControl() {} on() {} once() {} isStyleLoaded() { return false } remove() {} resize() {} getSource() { return undefined } getCanvas() { return { style: {} } } }
  return { Popup: Ctl, addProtocol: () => {}, setWorkerUrl: () => {}, NavigationControl: Ctl, ScaleControl: Ctl, AttributionControl: Ctl, Marker: Ctl, Map }
})

import { server } from '../../test/server'
import { AccessMunicipioMap } from './AccessMunicipioMap'
import { GrupoPrefixosGeoMap } from '../socios/GrupoPrefixosGeoMap'
import type { GrupoPrefixoGeoFeature } from '../../services/api'

beforeAll(() => { vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} unobserve() {} }) })
beforeEach(() => {
  server.use(
    http.get('*/municipios-centroides.json', () => HttpResponse.json({})),
    http.get('*/br-states.geojson', () => HttpResponse.json({ type: 'FeatureCollection', features: [] })),
  )
})

const abrir = (el: HTMLElement) => { (el as HTMLDetailsElement).open = true; return el }

describe('mapas com alternativa textual (OPERADORA-E3)', () => {
  it('mapa de acessos por município: grupo rotulado e tabela com os municípios, maiores primeiro, com a parcela quando houver', () => {
    const m = (ibge: string, nome: string, acessos: number, share?: number) => ({ ibge, nome, uf: 'ES', acessos, pf: acessos, pj: 0, share })
    render(<AccessMunicipioMap municipios={[m('3200102', 'Afonso Cláudio', 120, 12.5), m('3205309', 'Vitória', 900, 3.1)]} />)
    expect(screen.getByRole('group', { name: /acessos declarados em 2 municípios/ })).toBeInTheDocument()
    const ver = abrir(screen.getByTestId('ver-dados'))
    const tabela = within(ver).getByRole('table', { name: 'Ver dados (tabela dos municípios)' })
    expect(within(tabela).getAllByRole('columnheader').map((th) => th.textContent?.replace(/[▲▼↕]/g, '').trim())).toEqual(['Município', 'UF', 'Acessos', 'Parcela no município (%)'])
    const linhas = within(tabela).getAllByRole('row').slice(1)
    expect(linhas.map((l) => l.querySelector('td')?.textContent)).toEqual(['Vitória', 'Afonso Cláudio'])
    expect(linhas[1]).toHaveTextContent('12,5')
  })

  it('mapa de blocos do grupo: tabela por cidade com IPv6 antes de IPv4', () => {
    const f = (afi: 'v4' | 'v6', city: string, block_count: number): GrupoPrefixoGeoFeature => ({ type: 'Feature', geometry: { type: 'Point', coordinates: [-40, -20] }, properties: { afi, city, uf: 'ES', block_count } })
    render(<GrupoPrefixosGeoMap features={[f('v4', 'Vitória', 3), f('v6', 'Vitória', 2), f('v4', 'Serra', 1)]} />)
    expect(screen.getByRole('group', { name: /blocos IP geolocalizados dos ASNs do grupo em 2 localidades/ })).toBeInTheDocument()
    const tabela = within(abrir(screen.getByTestId('ver-dados'))).getByRole('table')
    expect(within(tabela).getAllByRole('columnheader').map((th) => th.textContent?.replace(/[▲▼↕]/g, '').trim())).toEqual(['Cidade', 'UF', 'Blocos IPv6', 'Blocos IPv4'])
    const [vitoria] = within(tabela).getAllByRole('row').slice(1)
    expect([...vitoria.querySelectorAll('td')].map((td) => td.textContent)).toEqual(['Vitória', 'ES', '2', '3'])
  })
})
