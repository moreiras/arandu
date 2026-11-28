// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render } from '@testing-library/react'
import type { LonLat } from '../../lib/geo'
import { conjuntoNoRaio, filtroPorIbge, filtrosDoConjunto } from './raio'

type Fn = (...a: unknown[]) => unknown
const h = vi.hoisted(() => ({ instancias: [] as Array<{ filtros: Record<string, unknown>; camadas: string[]; onLoad?: Fn }>, setData: vi.fn() }))

vi.mock('maplibre-gl', () => {
  class Mapa {
    filtros: Record<string, unknown> = {}
    camadas: string[] = []
    onLoad?: Fn
    constructor() { h.instancias.push(this as never) }
    on(ev: string, fn: Fn) { if (ev === 'load') this.onLoad = fn }
    addControl() {}
    addSource() {}
    addLayer(l: { id: string }) { this.camadas.push(l.id) }
    getLayer(id: string) { return this.camadas.includes(id) ? {} : undefined }
    getSource() { return { setData: h.setData } }
    setFilter(id: string, f: unknown) { this.filtros[id] = f }
    fitBounds() {}
    jumpTo() {}
    resize() {}
    remove() {}
    getCanvas() { return { style: {} } }
  }
  class Popup { setLngLat() { return this } setHTML() { return this } addTo() { return this } remove() {} }
  return { Map: Mapa, Popup, addProtocol: () => {}, default: {} }
})
vi.mock('../../components/maps/mapTheme', () => ({
  MAP_COLORS: { v4Strong: '#1d4ed8' }, STATE_OUTLINE_PAINT: {}, MAP_DEFAULT_CENTER: [0, 0], MAP_DEFAULT_ZOOM: 3,
  bearingInicial: () => 0, createBaseMapStyle: () => ({ version: 8, sources: {}, layers: [] }), addStandardControls: () => {},
}))
vi.mock('../../components/maps/Coropletico', () => ({ URL_MALHA: '/malha-municipal.pmtiles' }))

import { MapaRaio } from './MapaRaio'

vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} unobserve() {} })

const centroides: Record<string, LonLat> = { '1': [0, 0], '2': [0.1, 0], '3': [0.2, 0], '4': [5, 0] }

describe('filtros do mapa do raio', () => {
  it('filtroPorIbge casa a propriedade ibge (texto) com a lista; lista vazia não casa', () => {
    expect(filtroPorIbge(['2933307', '2900108'])).toEqual(['in', ['get', 'ibge'], ['literal', ['2933307', '2900108']]])
    expect(filtroPorIbge([])).toEqual(['in', ['get', 'ibge'], ['literal', []]])
  })
  it('filtrosDoConjunto separa somados, central e os cortados pelo teto', () => {
    const c = conjuntoNoRaio('1', centroides, 30, 2)!      // teto de 2: o central e o mais próximo; o '3' passa do teto
    const f = filtrosDoConjunto(c)
    expect(f.somados).toEqual(filtroPorIbge(['1', '2']))
    expect(f.central).toEqual(filtroPorIbge(['1']))
    expect(f.fora).toEqual(filtroPorIbge(['3']))
  })
})

describe('MapaRaio', () => {
  beforeEach(() => { h.instancias.length = 0; h.setData.mockClear() })

  it('aplica o filtro de IBGE nas camadas e, ao mudar o raio, só troca o filtro: o mapa não é recriado', () => {
    const c0 = conjuntoNoRaio('1', centroides, 0)!
    const { rerender, unmount } = render(<MapaRaio conjunto={c0} centroides={centroides} nomes={{}} />)
    expect(h.instancias).toHaveLength(1)
    const m = h.instancias[0]
    m.onLoad!()
    expect(m.camadas).toEqual(expect.arrayContaining(['mun-somados-fill', 'mun-somados-linha', 'mun-central-fill', 'mun-central-linha', 'mun-fora-linha']))
    expect(m.filtros['mun-somados-fill']).toEqual(filtroPorIbge(['1']))
    expect(m.filtros['mun-central-linha']).toEqual(filtroPorIbge(['1']))
    const c1 = conjuntoNoRaio('1', centroides, 30)!
    rerender(<MapaRaio conjunto={c1} centroides={centroides} nomes={{}} />)
    expect(h.instancias).toHaveLength(1)                                           // mesma instância
    expect(m.filtros['mun-somados-fill']).toEqual(filtroPorIbge(['1', '2', '3']))
    expect(m.filtros['mun-somados-linha']).toEqual(filtroPorIbge(['1', '2', '3']))
    expect(m.filtros['mun-central-fill']).toEqual(filtroPorIbge(['1']))
    expect(m.filtros['mun-fora-linha']).toEqual(filtroPorIbge([]))
    unmount()
  })

  it('o aria-label descreve o mapa e aponta a lista', () => {
    const c = conjuntoNoRaio('1', centroides, 30)!
    const { getByTestId } = render(<MapaRaio conjunto={c} centroides={centroides} nomes={{}} />)
    expect(getByTestId('mapa-raio')).toHaveAttribute('aria-label', expect.stringContaining('3 municípios'))
  })
})
