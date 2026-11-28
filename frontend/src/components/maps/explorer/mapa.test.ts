// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { afterEach, describe, expect, it, vi } from 'vitest'

// Mapa falso: registra o que o código manda o MapLibre fazer (jsdom não tem WebGL).
const chamadas = vi.hoisted(() => ({ popups: [] as { html: string; lngLat?: unknown; removido: boolean }[] }))
vi.mock('maplibre-gl', () => {
  class Popup {
    reg = { html: '', lngLat: undefined as unknown, removido: false }
    constructor() { chamadas.popups.push(this.reg) }
    setLngLat(l: unknown) { this.reg.lngLat = l; return this }
    setHTML(h: string) { this.reg.html = h; return this }
    addTo() { return this }
    remove() { this.reg.removido = true }
  }
  return { Popup, addProtocol: () => {}, setWorkerUrl: () => {}, NavigationControl: class {}, ScaleControl: class {}, AttributionControl: class {} }
})

import { adicionarCamadas } from './camadasMapa'
import { ligarInteracoes } from './interacoes'
import { FETCH_ORDER, INITIAL, MAPLIBRE_LAYERS } from './tipos'

function mapaFalso() {
  const fontes: Record<string, unknown> = {}
  const camadas: { id: string; type: string; source?: string; layout?: Record<string, unknown> }[] = []
  const handlers: Array<{ evento: string; camada: string; fn: (e: unknown) => void }> = []
  const canvas = { style: { cursor: '' } }
  return {
    fontes, camadas, handlers, canvas,
    addSource: (id: string, def: unknown) => { fontes[id] = def },
    addLayer: (l: { id: string; type: string; source?: string; layout?: Record<string, unknown> }) => { camadas.push(l) },
    getSource: (id: string) => (id in fontes ? { setData: vi.fn() } : undefined),
    on: (evento: string, camada: string, fn: (e: unknown) => void) => { handlers.push({ evento, camada, fn }) },
    getCanvas: () => canvas,
    dispara(evento: string, camada: string, e: unknown) { handlers.filter(h => h.evento === evento && h.camada === camada).forEach(h => h.fn(e)) },
  }
}

afterEach(() => { chamadas.popups.length = 0; vi.unstubAllGlobals() })

describe('camadas do mapa Explorar', () => {
  it('cria uma fonte por camada de dados, o círculo de proximidade e as camadas na ordem de desenho', () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ json: () => Promise.resolve({ type: 'FeatureCollection', features: [] }) })))
    const m = mapaFalso()
    adicionarCamadas(m as never)
    for (const id of FETCH_ORDER) expect(m.fontes[`src-${id}`], id).toBeDefined()
    expect(m.fontes['recorte-radius']).toBeDefined()
    expect(m.fontes.states).toBeDefined()
    const ids = m.camadas.map(c => c.id)
    expect(ids.slice(0, 3)).toEqual(['states-outline', 'recorte-radius-fill', 'recorte-radius-line'])
    // as camadas dos dados vêm de baixo para cima, como em MAPLIBRE_LAYERS (o PIX por último, sobre as nuvens de prefixos)
    expect(ids.slice(3)).toEqual(['explorer-erbs', 'explorer-roads-estadual', 'explorer-roads-federal', 'explorer-pref-v4', 'explorer-pref-v6',
      'explorer-pref-ix-v4', 'explorer-pref-ix-v6', 'explorer-scms', 'explorer-asns', 'explorer-pix'])
    // todas as camadas de dados começam ocultas (o efeito de visibilidade liga conforme o estado)
    for (const l of m.camadas.filter(c => c.id.startsWith('explorer-'))) expect(l.layout?.visibility, l.id).toBe('none')
    expect(MAPLIBRE_LAYERS.map(l => l.id).sort()).toEqual(ids.filter(i => i.startsWith('explorer-')).sort())
    expect(INITIAL.on.pix).toBe(true)
    // infraestrutura de fundo aberta junto com os PIX
    expect([INITIAL.on.submarine, INITIAL.on.terrestrial]).toEqual([true, true])
  })

  it('cada camada lê da fonte da sua consulta', () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ json: () => Promise.resolve({}) })))
    const m = mapaFalso()
    adicionarCamadas(m as never)
    const fonteDe = Object.fromEntries(m.camadas.map(c => [c.id, c.source]))
    for (const ml of MAPLIBRE_LAYERS) expect(fonteDe[ml.id], ml.id).toBe(`src-${ml.data}`)
  })

  it('falha ao buscar o contorno dos estados não derruba o mapa', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('rede'))))
    expect(() => adicionarCamadas(mapaFalso() as never)).not.toThrow()
    await Promise.resolve()
  })
})

describe('interações do mapa Explorar', () => {
  const ev = (properties: Record<string, unknown>) => ({ lngLat: { lng: -40, lat: -20 }, features: [{ properties }] })

  it('balão ao passar o mouse: monta o HTML da camada, troca o cursor e some ao sair', () => {
    const m = mapaFalso()
    ligarInteracoes(m as never, { navegar: vi.fn(), camadasLigadas: () => INITIAL.on, colorBy: () => 'rpki' })
    m.dispara('mouseenter', 'explorer-asns', ev({ asn: 64500, color_value: 'yes' }))
    expect(m.canvas.style.cursor).toBe('pointer')
    expect(chamadas.popups[0].html).toContain('<strong>AS64500</strong>')
    expect(chamadas.popups[0].html).toContain('Com ROA publicada')                        // usa o color_by lido na hora do evento
    m.dispara('mouseleave', 'explorer-asns', ev({}))
    expect(m.canvas.style.cursor).toBe('')
    expect(chamadas.popups[0].removido).toBe(true)
    m.dispara('mouseenter', 'explorer-pref-v4', ev({ prefix: '200.1.0.0/16' }))
    expect(m.canvas.style.cursor).toBe('crosshair')
  })

  it('infra do estilo base só mostra balão com a camada ligada (lida na hora, sem recriar o mapa)', () => {
    const m = mapaFalso()
    let ligadas = { ...INITIAL.on, submarine: false }
    ligarInteracoes(m as never, { navegar: vi.fn(), camadasLigadas: () => ligadas, colorBy: () => 'solid' })
    m.dispara('mouseenter', 'infra-submarine-cables', ev({ name: 'Monet' }))
    expect(chamadas.popups[0].html).toBe('')                                      // desligada: nada
    expect(m.canvas.style.cursor).toBe('')
    ligadas = { ...ligadas, submarine: true }
    m.dispara('mouseenter', 'infra-submarine-cables', ev({ name: 'Monet' }))
    expect(chamadas.popups[0].html).toContain('<strong>Monet</strong>')
    m.dispara('mousemove', 'infra-submarine-cables', ev({ name: 'Monet 2' }))     // acompanha o mouse nas linhas
    expect(chamadas.popups[0].html).toContain('Monet 2')
  })

  it('rodovias não dependem do liga/desliga do estilo base', () => {
    const m = mapaFalso()
    ligarInteracoes(m as never, { navegar: vi.fn(), camadasLigadas: () => INITIAL.on, colorBy: () => 'solid' })
    m.dispara('mouseenter', 'explorer-roads-federal', ev({ sigla: 'BR-101' }))
    expect(chamadas.popups[0].html).toContain('BR-101')
  })

  it('clique navega para AS, operadora e PTT; sem o campo, não navega', () => {
    const m = mapaFalso()
    const navegar = vi.fn()
    ligarInteracoes(m as never, { navegar, camadasLigadas: () => INITIAL.on, colorBy: () => 'solid' })
    m.dispara('click', 'explorer-asns', ev({ asn: 64500 }))
    m.dispara('click', 'explorer-scms', ev({ cnpj: '12345678000190' }))
    m.dispara('click', 'explorer-pix', ev({ ixp_code: 'sp' }))
    m.dispara('click', 'explorer-scms', ev({ razao_social: 'sem cnpj' }))
    expect(navegar.mock.calls.map(c => c[0])).toEqual(['/asn/64500', '/operadora/12345678000190', '/ixp/sp'])
  })

  it('evento sem feição é ignorado', () => {
    const m = mapaFalso()
    ligarInteracoes(m as never, { navegar: vi.fn(), camadasLigadas: () => INITIAL.on, colorBy: () => 'solid' })
    m.dispara('mouseenter', 'explorer-pix', { lngLat: {}, features: [] })
    expect(chamadas.popups[0].html).toBe('')
  })
})
