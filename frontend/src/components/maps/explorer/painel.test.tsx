// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { server } from '../../../test/server'
import type { PixCobertura } from '../../../services/api'
import { Legend } from './Legenda'
import { LayerPanel } from './PainelCamadas'
import { resumirScm } from './scmSici'
import type { LayerStatus } from './PainelCamadas'
import { INITIAL, LAYERS } from './tipos'
import type { LayerId, MapState } from './tipos'
import { useCamadasDados } from './useCamadasDados'

const statusOff = Object.fromEntries(LAYERS.map(l => [l.id, { state: 'off', stale: false }])) as Record<LayerId, LayerStatus>
const envolver = (ui: React.ReactNode) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{ui}</QueryClientProvider>
)

function Painel({ statuses = statusOff, matched }: { statuses?: Record<LayerId, LayerStatus>; matched?: number }) {
  const [state, setState] = useState<MapState>(INITIAL)
  return (
    <>
      <LayerPanel state={state} onChange={setState} onClose={() => {}} statuses={statuses} matchedAsns={matched} selectedIx={null} />
      <output data-testid="estado">{JSON.stringify({ on: state.on, grupos: state.groups.map(g => g.predicates.map(p => p.kind)), colorBy: state.colorBy, scm: state.scmMode })}</output>
    </>
  )
}
const estado = () => JSON.parse(screen.getByTestId('estado').textContent!)
const caixa = (rotulo: string) => screen.getByText(rotulo).closest('label')!.querySelector('input')!

describe('painel de camadas', () => {
  it('liga e desliga camadas; só o PIX começa ligado; "Limpar tudo" só aparece com alteração', () => {
    render(envolver(<Painel />))
    expect(screen.queryByText('Limpar tudo')).toBeNull()
    expect(estado().on.pix).toBe(true)
    fireEvent.click(caixa('Sedes dos ASes'))
    expect(estado().on.asns_geo).toBe(true)
    expect(screen.getByText('Colorir por')).toBeTruthy()                           // ajuste da camada aparece ao ligar
    fireEvent.change(screen.getByDisplayValue('Cor única'), { target: { value: 'rpki' } })
    expect(estado().colorBy).toBe('rpki')
    fireEvent.click(screen.getByText('Limpar tudo'))
    expect(estado().on.asns_geo).toBe(false)
    expect(estado().colorBy).toBe('solid')
  })

  it('recorte de ASes: cria grupo com um filtro, troca o tipo, mostra o valor e remove o grupo ao tirar o último filtro', () => {
    render(envolver(<Painel matched={321} />))
    expect(screen.getByText('321 ASes')).toBeTruthy()
    expect(screen.getByText('Sem filtros: todos os ASes.')).toBeTruthy()
    fireEvent.click(screen.getByText('+ grupo de filtros'))
    expect(estado().grupos).toEqual([['is_br']])
    fireEvent.change(screen.getByDisplayValue('ASN brasileiro (LACNIC)'), { target: { value: 'ixps_direct_in' } })
    expect(estado().grupos).toEqual([['ixps_direct_in']])
    expect(screen.getByPlaceholderText('ex: sp')).toBeTruthy()
    fireEvent.click(screen.getByText('+ filtro'))
    expect(estado().grupos).toEqual([['ixps_direct_in', 'is_br']])
    fireEvent.click(screen.getAllByTitle('Remover filtro')[0])
    fireEvent.click(screen.getByTitle('Remover filtro'))
    expect(estado().grupos).toEqual([])
  })

  it('avisa quando há recorte mas nenhuma camada com funil está ligada', () => {
    render(envolver(<Painel />))
    fireEvent.click(screen.getByText('+ grupo de filtros'))
    expect(screen.getByText(/não afeta nenhuma camada ligada/)).toBeTruthy()
    fireEvent.click(caixa('Sedes dos ASes'))
    expect(screen.queryByText(/não afeta nenhuma camada ligada/)).toBeNull()
  })

  it('status da camada: contagem, erro com "tentar de novo" e CSV', () => {
    const retry = vi.fn()
    const download = vi.fn()
    const statuses = {
      ...statusOff,
      asns_geo: { state: 'done', count: 1234, stale: false, download },
      outorgas_scm: { state: 'error', stale: false, retry },
    } as Record<LayerId, LayerStatus>
    const Painel2 = () => {
      const [state, setState] = useState<MapState>({ ...INITIAL, on: { ...INITIAL.on, asns_geo: true, outorgas_scm: true } })
      return <LayerPanel state={state} onChange={setState} onClose={() => {}} statuses={statuses} selectedIx={null} />
    }
    render(envolver(<Painel2 />))
    expect(screen.getByText('1.234')).toBeTruthy()
    fireEvent.click(screen.getByTitle('Baixar CSV: Sedes dos ASes'))
    expect(download).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByText('⚠ tentar de novo'))
    expect(retry).toHaveBeenCalledOnce()
  })

  it('outorgas SCM: "Colorir por" declaração ao SICI e resumo por UF do recorte, sem juízo (PT-26 / MAPA 5.4)', () => {
    const f = (p: Record<string, unknown>): GeoJSON.Feature => ({ type: 'Feature', properties: p, geometry: { type: 'Point', coordinates: [0, 0] } })
    const resumo = resumirScm({ type: 'FeatureCollection', features: [
      f({ uf: 'SP', sici_ativo: true, sici_mes_referencia: '2026-09', has_asn: true }), f({ uf: 'SP', sici_ativo: false, sici_mes_referencia: '2026-09', has_asn: false }), f({ uf: 'AC', sici_ativo: false, sici_mes_referencia: '2026-09', has_asn: false }),
    ] })
    let ultimo: MapState | null = null
    const P = () => {
      const [state, setState] = useState<MapState>({ ...INITIAL, on: { ...INITIAL.on, outorgas_scm: true } })
      ultimo = state
      return <><LayerPanel state={state} onChange={setState} onClose={() => {}} statuses={statusOff} selectedIx={null} resumoScm={resumo} /><Legend state={state} resumoScm={resumo} /></>
    }
    render(envolver(<P />))
    expect(ultimo!.scmColorBy).toBe('asn')                                              // o padrão não muda
    expect(screen.getByText('SCM com ASN (1)')).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Colorir as outorgas SCM por'), { target: { value: 'sici' } })
    expect(ultimo!.scmColorBy).toBe('sici')
    expect(screen.getByText('SCM com acessos declarados ao SICI em 2026-09 (1)')).toBeTruthy()
    expect(screen.getByText('SCM sem acessos declarados em 2026-09 (2)')).toBeTruthy()
    const linhas = [...screen.getByTestId('resumo-scm-uf').querySelectorAll('tbody tr')].map(tr => tr.textContent)
    expect(linhas).toEqual(['AC1010', 'SP2111'])                                        // UF em ordem alfabética: outorgas, com, sem, com ASN
    const texto = screen.getByTestId('resumo-scm-uf').textContent ?? ''
    expect(texto).toMatch(/não uma avaliação de cumprimento/)
    expect(texto).not.toMatch(/irregular|infra[çc]|omiss|omitiu|pior|melhor/i)
  })

  it('PIX: o texto de cobertura vem do dado, com fonte e data, e cita os PTTs sem local (PT-25 / MAPA 5.1)', () => {
    const cobertura: PixCobertura = { locais_no_cadastro: 189, locais_com_coordenadas: 173, ptts_sem_local: ['Caxias do Sul'], fonte: 'cadastro de PIX do IX.br (config/pix.yaml)', data_cadastro: '2026-11-24', snapshot_date: '2026-11-22' }
    const P = ({ c }: { c: PixCobertura | null }) => {
      const [state, setState] = useState<MapState>(INITIAL)
      return <LayerPanel state={state} onChange={setState} onClose={() => {}} statuses={statusOff} selectedIx={null} pixCobertura={c} />
    }
    const { unmount } = render(envolver(<P c={cobertura} />))
    const t = screen.getByTestId('pix-cobertura').textContent ?? ''
    expect(t).toMatch(/173 de 189 locais do cadastro com coordenadas no mapa/)
    expect(t).toMatch(/cadastro de PIX do IX\.br \(config\/pix\.yaml\), cadastro de 2026-11-24; snapshot 2026-11-22/)
    expect(t).toMatch(/PTTs sem nenhum local no mapa: Caxias do Sul\./)
    unmount()
    render(envolver(<P c={{ ...cobertura, locais_no_cadastro: 1, locais_com_coordenadas: 1, ptts_sem_local: [], data_cadastro: null }} />))
    const u = screen.getByTestId('pix-cobertura').textContent ?? ''
    expect(u).toMatch(/1 de 1 local do cadastro/)
    expect(u).not.toMatch(/PTTs sem nenhum local|cadastro de 20/)
  })

  it('lista de PTTs vem de /ixps, sem os ausentes, em ordem alfabética', async () => {
    server.use(http.get('*/api/v1/ixps', () => HttpResponse.json({ ixps: [
      { code: 'sp', name: 'São Paulo', uf: 'SP', status: 'ok' }, { code: 'ac', name: 'Acre', uf: 'AC', status: 'ok' }, { code: 'xx', name: 'Fantasma', uf: 'XX', status: 'missing' },
    ] })))
    render(envolver(<Painel />))
    await waitFor(() => expect(screen.getAllByText('Acre, AC').length).toBeGreaterThan(0))
    const opcoes = screen.getAllByRole('option').map(o => o.textContent)
    expect(opcoes).toContain('São Paulo, SP')
    expect(opcoes).not.toContain('Fantasma, XX')
    expect(opcoes.indexOf('Acre, AC')).toBeLessThan(opcoes.indexOf('São Paulo, SP'))
  })
})

describe('busca de dados por camada', () => {
  const geo = (n: number) => ({ type: 'FeatureCollection', features: Array.from({ length: n }, (_, i) => ({ type: 'Feature', properties: { i }, geometry: { type: 'Point', coordinates: [0, 0] } })), snapshot_date: '2026-09-20', matched_asns: 7 })

  it('só busca o PIX e o que está ligado; informa contagem, snapshot e tamanho do recorte', async () => {
    const pedidos: string[] = []
    server.use(http.post('*/api/v1/map/query', async ({ request }) => {
      const corpo = (await request.json()) as { layers: string[] }
      pedidos.push(corpo.layers[0])
      return HttpResponse.json(geo(corpo.layers[0] === 'pix' ? 3 : 5))
    }))
    const exportar = vi.fn()
    const estado: MapState = { ...INITIAL, on: { ...INITIAL.on, asns_geo: true } }
    const wrapper = ({ children }: { children: React.ReactNode }) => envolver(children)
    const { result } = renderHook(() => useCamadasDados(estado, estado, '2026-09-20', exportar), { wrapper })
    await waitFor(() => expect(result.current.statuses.asns_geo.state).toBe('done'))
    expect(new Set(pedidos)).toEqual(new Set(['pix', 'asns_geo']))
    expect(result.current.statuses.asns_geo.count).toBe(5)
    expect(result.current.statuses.prefixes_v4.state).toBe('off')
    expect(result.current.matchedAsns).toBe(7)
    act(() => result.current.statuses.asns_geo.download!())
    expect(exportar).toHaveBeenCalledWith(expect.any(Array), 'asns_geo', '2026-09-20')
    expect(result.current.statuses.pix.download).toBeUndefined()                  // PIX não tem CSV
  })

  it('erro da API vira status "error" e a camada pode ser refeita', async () => {
    server.use(http.post('*/api/v1/map/query', () => new HttpResponse('boom', { status: 500 })))
    const estado: MapState = { ...INITIAL, on: { ...INITIAL.on, outorgas_scm: true } }
    const { result } = renderHook(() => useCamadasDados(estado, estado, undefined, vi.fn()), {
      wrapper: ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{children}</QueryClientProvider>),
    })
    await waitFor(() => expect(result.current.errors).toContain('outorgas_scm'), { timeout: 4000 })
    expect(result.current.statuses.outorgas_scm.state).toBe('error')
    expect(typeof result.current.statuses.outorgas_scm.retry).toBe('function')
  })
})

describe('predefinições do mapa', () => {
  it('cada predefinição liga só as suas camadas e desliga as demais', async () => {
    const { PREDEFINICOES, aplicarPredefinicao } = await import('./PainelCamadas')
    for (const pd of PREDEFINICOES) {
      const novo = aplicarPredefinicao(INITIAL, pd.camadas)
      for (const [id, ligada] of Object.entries(novo.on)) expect(ligada, `${pd.id}:${id}`).toBe(pd.camadas.includes(id as any))
      expect(novo.groups).toEqual(INITIAL.groups)
    }
  })
})
