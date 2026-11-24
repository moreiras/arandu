// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

// MapLibre falso: registra o que o código manda fazer (jsdom não tem WebGL)
const reg = vi.hoisted(() => ({ popups: [] as { html: string }[] }))
vi.mock('maplibre-gl', () => {
  class Popup {
    r = { html: '' }
    constructor() { reg.popups.push(this.r) }
    setLngLat() { return this }
    setHTML(h: string) { this.r.html = h; return this }
    addTo() { return this }
    remove() {}
  }
  class Ctl { }
  return { Popup, addProtocol: () => {}, setWorkerUrl: () => {}, NavigationControl: Ctl, ScaleControl: Ctl, AttributionControl: Ctl, Marker: Ctl, Map: Ctl }
})

import { featuresBolhas, featuresPix, featuresScm, featuresSedes, featuresSici } from './balloes'
import type { GrupoCoord } from './calculos'
import { adicionarCamadas, ligarInteracoes } from './useMapaLocalizador'
import { PainelControles } from './PainelControles'
import { PainelEntidades } from './PainelEntidades'
import type { AsnDot, Bubble, Entity, InfoAsn, ScmGeoFeature } from './tipos'

const CNPJ = '12345678000190'
const dot = (asn: number, lon = -46.63, lat = -23.55, extra: Partial<AsnDot> = {}): AsnDot => ({ lat, lon, asn, name: `AS ${asn}`, city: 'São Paulo', uf: 'SP', ...extra })
const scm = (cnpj: string, asns: number[] | string = [], extra: Partial<ScmGeoFeature['properties']> = {}): ScmGeoFeature =>
  ({ geometry: { coordinates: [-46.63, -23.55] }, properties: { cnpj, razao_social: `Prov ${cnpj}`, municipio: 'São Paulo', uf: 'SP', has_asn: parseInt(String(asns).replace(/\D/g, '') || '0') > 0, asns, ...extra } })
const bolha = (asn: number, count: number, afi = 4, own = true, lon = -46.63, lat = -23.55): Bubble =>
  ({ lat, lon, asn, name: `AS ${asn}`, afi, own, city: 'São Paulo', uf: 'SP', count })
const nomes = new Map<number, InfoAsn>([[1, { name: 'AS 1', cnpj: CNPJ, razao_social: 'Razão Um', nome_fantasia: 'Fantasia Um' }]])
const prop = (f: GeoJSON.Feature) => f.properties as Record<string, unknown>

afterEach(() => { reg.popups.length = 0; vi.unstubAllGlobals() })

describe('feições do Localizador', () => {
  it('bolhas: um AS por coordenada mostra detalhes; vários viram modal; cor pela família dominante', () => {
    const [um] = featuresBolhas([bolha(1, 1)], nomes, new Map())
    expect(prop(um)).toMatchObject({ count: 1, entityCount: 1 })
    expect(prop(um).tip).toContain('<b>AS1</b>')
    expect(prop(um).tip).toContain('12.345.678/0001-90')
    expect(prop(um).tip).toContain('Anatel: Razão Um')
    expect(prop(um).tip).toContain('1 prefixo')                         // só a contagem: nenhum prefixo é identificado
    expect(prop(um).tip).toContain('IPv4 · sede na região')
    const [varios] = featuresBolhas([bolha(1, 500), bolha(2, 30, 6, false)], nomes, new Map())
    expect(prop(varios)).toMatchObject({ count: 530, entityCount: 2, modalTitle: '2 ASes · São Paulo/SP' })
    expect(prop(varios).modalHtml).toContain('500 prefixos')
    expect(prop(varios).modalHtml).toContain('IPv6 · sede fora')
    expect(prop(varios).color).toBe(featuresBolhas([bolha(1, 1)], nomes, new Map()).map(f => prop(f).color)[0])    // dominante é o IPv4 próprio
    expect(String(prop(varios).tip)).toContain('clique para ver todos')
    expect(featuresBolhas([bolha(1, 1, 4, true, -40, -20), bolha(2, 1)], nomes, new Map())).toHaveLength(2)        // coordenadas distintas
  })

  it('sedes: SCM do mesmo ponto sai da camada de sedes; vários ASes na coordenada viram modal', () => {
    const grupos = new Map<string, GrupoCoord>([['-46.63,-23.55', { lon: -46.63, lat: -23.55, asns: [dot(1)], scms: [scm(CNPJ, [1])] }]])
    expect(featuresSedes([dot(1)], true, grupos, new Map())).toHaveLength(0)
    const f = featuresSedes([dot(1), dot(2), dot(3, -40, -20)], false, new Map(), new Map([[1, CNPJ]]))
    expect(f).toHaveLength(2)
    const multi = f.find(x => prop(x).entityCount === 2)!
    expect(prop(multi)).toMatchObject({ radius: 8, modalTitle: '2 sedes de AS · São Paulo, SP' })
    expect(prop(multi).modalHtml).toContain('>SCM</span>')              // o AS 1 tem outorga
    const um = f.find(x => prop(x).entityCount === 1)!
    expect(prop(um)).toMatchObject({ radius: 6 })
    expect(prop(um).tip).toContain('sede</span>')
  })

  it('PIX: nome e IX', () => {
    expect(prop(featuresPix([{ lat: 1, lon: 2, name: 'PIX A', ixpName: 'Vitória' }])[0]).tip).toBe('<b>PIX A</b><br/>IX Vitória')
    expect(prop(featuresPix([{ lat: 1, lon: 2, name: 'PIX A', ixpName: '' }])[0]).tip).toBe('<b>PIX A</b>')
  })

  it('SCM: único sem AS, único AS com outorga e vários operadores no mesmo ponto', () => {
    const asns = new Map<number, string>([[1, CNPJ]])
    const g = (asnsDoGrupo: AsnDot[], scms: ScmGeoFeature[]) => new Map<string, GrupoCoord>([['k', { lon: -46.63, lat: -23.55, asns: asnsDoGrupo, scms }]])
    const so = featuresScm(g([], [scm('999')]), asns, nomes)
    expect(so).toHaveLength(1)
    expect(prop(so[0])).toMatchObject({ entityCount: 1, radius: 6, strokeWidth: 1 })        // sem AS: roxo, traço fino
    expect(prop(so[0]).tip).toContain('Prov 999')
    const comAs = featuresScm(g([dot(1, -46.63, -23.55, { cnpj: CNPJ })], [scm(CNPJ, [1])]), asns, nomes)
    expect(prop(comAs[0])).toMatchObject({ entityCount: 1, strokeWidth: 2 })
    expect(prop(comAs[0]).tip).toContain('<b>AS1</b>')
    const multi = featuresScm(g([dot(1, -46.63, -23.55, { cnpj: CNPJ }), dot(2)], [scm(CNPJ, [1]), scm('999')]), asns, nomes)
    expect(prop(multi[0])).toMatchObject({ entityCount: 3, radius: 8 })                    // AS1 (com a SCM dele), AS2 e a SCM 999
    expect(prop(multi[0]).modalTitle).toBe('3 operadores · São Paulo/SP')
    expect(featuresScm(new Map([['k', { lon: 0, lat: 0, asns: [dot(1)], scms: [] }]]), asns, nomes)).toEqual([])   // grupo sem SCM não entra
  })

  it('SICI: um operador mostra os acessos dele; vários abrem modal com o total do município', () => {
    const mun = (operadores: { cnpj: string; empresa: string; acessos: number }[]) => ({ ibge: '1', nome: 'Serra', uf: 'ES', lat: -20, lon: -40, acessos: operadores.reduce((s, o) => s + o.acessos, 0), operadores })
    const [um] = featuresSici([mun([{ cnpj: CNPJ, empresa: 'A', acessos: 1234 }])])
    expect(prop(um)).toMatchObject({ radius: 6, entityCount: 1 })
    expect(prop(um).tip).toContain('1.234 acessos declarados ao SICI')
    const [dois] = featuresSici([mun([{ cnpj: CNPJ, empresa: 'A', acessos: 10 }, { cnpj: '1', empresa: 'B', acessos: 5 }])])
    expect(prop(dois)).toMatchObject({ radius: 8, entityCount: 2, modalTitle: '2 operadores · Serra/ES' })
    expect(prop(dois).tip).toContain('15 acessos declarados no total')
    expect(prop(featuresSici([mun([])])[0]).tip).toContain('0 acessos declarados ao SICI')
  })
})

describe('mapa do Localizador', () => {
  function mapaFalso() {
    const fontes: Record<string, unknown> = {}
    const camadas: string[] = []
    const handlers: Array<{ ev: string; camada?: string; fn: (e: unknown) => void }> = []
    return {
      fontes, camadas, handlers, canvas: { style: { cursor: '' } },
      addSource: (id: string) => { fontes[id] = true },
      addLayer: (l: { id: string }) => { camadas.push(l.id) },
      getSource: () => undefined,
      getCanvas() { return this.canvas },
      on(ev: string, a: unknown, b?: unknown) { if (typeof a === 'string') handlers.push({ ev, camada: a, fn: b as never }); else handlers.push({ ev, fn: a as never }) },
      queryRenderedFeatures: vi.fn(() => [] as unknown[]),
    }
  }

  it('camadas na ordem de desenho: estados, raio, bolhas, sedes, PIX, SCM e SICI', () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ json: () => Promise.resolve({}) })))
    const m = mapaFalso()
    adicionarCamadas(m as never)
    expect(m.camadas).toEqual(['states-outline', 'radius-fill', 'radius-line', 'bubbles', 'asns', 'pix', 'scms-loc', 'sici-mun'])
    expect(Object.keys(m.fontes)).toEqual(['states', 'radius', 'bubbles', 'asns', 'pix', 'scms-loc', 'sici-mun'])
  })

  it('clique em agregado abre o modal; clique no mapa vazio move o ponto; clique em feição não move', () => {
    const m = mapaFalso()
    const abrirModal = vi.fn(), moverPonto = vi.fn()
    ligarInteracoes(m as never, { abrirModal, moverPonto })
    const ev = (properties: Record<string, unknown>) => ({ lngLat: { lng: -40, lat: -20 }, point: { x: 1, y: 2 }, features: [{ properties }] })
    m.handlers.filter(h => h.ev === 'click' && h.camada === 'asns').forEach(h => h.fn(ev({ entityCount: 1 })))
    expect(abrirModal).not.toHaveBeenCalled()                                      // um só: o balão basta
    m.handlers.filter(h => h.ev === 'click' && h.camada === 'asns').forEach(h => h.fn(ev({ entityCount: 3, modalTitle: 'T', modalHtml: '<i>x</i>' })))
    expect(abrirModal).toHaveBeenCalledWith({ title: 'T', html: '<i>x</i>' })
    const geral = m.handlers.find(h => h.ev === 'click' && !h.camada)!
    geral.fn(ev({}))
    expect(moverPonto).toHaveBeenCalledWith([-20, -40])
    m.queryRenderedFeatures.mockReturnValueOnce([{}])
    geral.fn(ev({}))
    expect(moverPonto).toHaveBeenCalledTimes(1)
  })

  it('balão mostra o HTML pronto da feição e some ao sair', () => {
    const m = mapaFalso()
    ligarInteracoes(m as never, { abrirModal: vi.fn(), moverPonto: vi.fn() })
    m.handlers.find(h => h.ev === 'mouseenter' && h.camada === 'pix')!.fn({ lngLat: {}, features: [{ properties: { tip: '<b>PIX</b>' } }] })
    expect(reg.popups[0].html).toBe('<b>PIX</b>')
    expect(m.canvas.style.cursor).toBe('pointer')
    m.handlers.find(h => h.ev === 'mouseleave' && h.camada === 'pix')!.fn({})
    expect(m.canvas.style.cursor).toBe('')
  })
})

describe('painéis do Localizador', () => {
  const base = { className: 'x', search: '', setSearch: vi.fn(), searching: false, onSearch: vi.fn(), radius: 80, setRadius: vi.fn() }

  it('controles: busca por Enter, raio, camadas e legenda condicional', () => {
    const setShow = vi.fn(), onSearch = vi.fn(), setSearch = vi.fn(), setRadius = vi.fn()
    const { rerender } = render(<PainelControles {...base} onSearch={onSearch} setSearch={setSearch} setRadius={setRadius}
      show={{ asns: true, prefixes: false, scms: false, sici: false }} setShow={setShow} />)
    fireEvent.change(screen.getByPlaceholderText('Nome do município…'), { target: { value: 'Vitória' } })
    expect(setSearch).toHaveBeenCalledWith('Vitória')
    fireEvent.keyDown(screen.getByPlaceholderText('Nome do município…'), { key: 'Enter' })
    expect(onSearch).toHaveBeenCalledOnce()
    fireEvent.change(screen.getByRole('slider'), { target: { value: '200' } })
    expect(setRadius).toHaveBeenCalledWith(200)
    fireEvent.click(screen.getByLabelText('Prefixos geolocalizados'))
    expect(setShow).toHaveBeenCalledWith({ prefixes: true })
    fireEvent.click(screen.getByLabelText('Usuários informados no SICI (Anatel)'))
    expect(setShow).toHaveBeenCalledWith({ sici: true })
    expect(screen.queryByText('IPv4 · sede aqui')).toBeNull()
    rerender(<PainelControles {...base} show={{ asns: true, prefixes: true, scms: true, sici: true }} setShow={setShow} />)
    expect(screen.getByText('IPv4 · sede aqui')).toBeTruthy()
    expect(screen.getByText('SCM sem AS')).toBeTruthy()
    expect(screen.getByText(/centróide do IBGE/)).toBeTruthy()
  })

  const ent = (extra: Partial<Entity>): Entity => ({ key: 'k', asns: [], name: '', fromHq: false, v4: false, v6: false, scm: false, scmHq: false, ...extra })
  const propsEnt = (entities: Entity[], extra = {}) => ({
    className: 'y', entities, entityCounts: { asns: entities.filter(e => e.asns.length).length, scms: entities.filter(e => e.scm).length },
    markerPos: [-23.55, -46.63] as [number, number], stats: { sedesAsn: 1, asnsComPrefixo: 0, sedesScm: 0, scmsComUsuarios: 0 },
    filteredAsnsCount: 1, nearestIx: 'sp', ixLabel: (c: string) => `IX ${c.toUpperCase()}`,
    ixCounts: { nearMember: 1, nearOrigin: 0, anyMember: 1, otherNotNear: 0 }, copied: false, onCopy: vi.fn(), onCsv: vi.fn(), temPresenca: true,
    tagsDoAs: () => [{ code: 'sp', label: 'IX SP', kind: 'near' as const }], ...extra,
  })

  it('lista: AS com link, CNPJ, tags de IX, badges e resumo; só-SCM leva à operadora', () => {
    render(<MemoryRouter><PainelEntidades {...propsEnt([
      ent({ key: 'a', asns: [64500, 64501], cnpj: CNPJ, name: 'Prov A', city: 'Serra', uf: 'ES', fromHq: true, v4: true, scm: true, sici: { acessos: 1500, municipios: 2 } }),
      ent({ key: 'b', asns: [], cnpj: '999', name: 'Só SCM', scm: true }),
    ])} /></MemoryRouter>)
    expect(screen.getByText('2 entidades')).toBeTruthy()
    expect(screen.getByText('1 AS, 2 SCMs')).toBeTruthy()
    expect(screen.getByText('AS64500, AS64501').closest('a')!.getAttribute('href')).toBe('/asn/64500')
    expect(screen.getByText('Só SCM').closest('a')!.getAttribute('href')).toBe('/operadora/999')
    expect(screen.getAllByText('IX SP').length).toBeGreaterThanOrEqual(1)      // a tag da entidade (e o resumo, que cita o IX mais próximo)
    expect(screen.getByText('1.500 acessos · 2 municípios no raio')).toBeTruthy()
    expect(screen.getByTitle('Prefixos IPv4 na região')).toBeTruthy()
    expect(screen.getAllByText(/participam de/).length).toBeGreaterThan(0)
    expect(screen.getByText(/têm prefixos vistos nos route servers de/)).toBeTruthy()      // originação vista, não anúncio próprio
    expect(document.body.textContent).not.toMatch(/anunciam prefixos em/)
  })

  it('copiar e CSV chamam os callbacks; sem ponto de referência mostra a orientação', () => {
    const p = propsEnt([ent({ key: 'a', asns: [1], name: 'X' })])
    render(<MemoryRouter><PainelEntidades {...p} /></MemoryRouter>)
    fireEvent.click(screen.getByText('Copiar'))
    fireEvent.click(screen.getByText('CSV'))
    expect(p.onCopy).toHaveBeenCalledOnce()
    expect(p.onCsv).toHaveBeenCalledOnce()
    render(<MemoryRouter><PainelEntidades {...propsEnt([], { markerPos: null })} /></MemoryRouter>)
    expect(screen.getByText(/Clique no mapa ou busque por nome de município/)).toBeTruthy()
    render(<MemoryRouter><PainelEntidades {...propsEnt([])} /></MemoryRouter>)
    expect(screen.getByText('Nenhuma entidade encontrada neste raio.')).toBeTruthy()
  })
})
