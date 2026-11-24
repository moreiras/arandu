// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeAll, describe, expect, it, vi } from 'vitest'

vi.mock('maplibre-gl', () => {
  class Ctl { }
  class Map { addControl() {} on() {} once() {} isStyleLoaded() { return false } remove() {} resize() {} getSource() { return undefined } getCanvas() { return { style: {} } } }
  return { Popup: Ctl, addProtocol: () => {}, setWorkerUrl: () => {}, NavigationControl: Ctl, ScaleControl: Ctl, AttributionControl: Ctl, Marker: Ctl, Map }
})

import { server } from '../../test/server'
import { MapaSede } from './MapaSede'
import type { Servico } from './servicos'

beforeAll(() => {
  vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} unobserve() {} })
  server.use(http.get('*/br-states.geojson', () => HttpResponse.json({ type: 'FeatureCollection', features: [] })))
})

describe('mapa de sedes (OPERADORA-E3)', () => {
  it('tem rótulo que aponta a lista como alternativa e legenda com marcadores decorativos', () => {
    const servico = { id: 'stfc', rotulo: 'STFC', mapa: async () => ({ type: 'FeatureCollection', features: [] }) } as unknown as Servico
    const { container } = render(
      <QueryClientProvider client={new QueryClient()}><MapaSede servico={servico} comAsn={false} moldura /></QueryClientProvider>,
    )
    expect(screen.getByRole('group', { name: /Mapa das sedes das outorgadas STFC.*a lista da página traz as mesmas empresas/ })).toBeInTheDocument()
    expect(screen.getByText(/STFC sem AS/)).toBeInTheDocument()
    expect(container.querySelectorAll('span.rounded-full[aria-hidden="true"]')).toHaveLength(2)
  })
})
