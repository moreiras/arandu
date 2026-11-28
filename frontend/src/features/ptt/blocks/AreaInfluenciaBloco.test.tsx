// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '../../../test/server'
import { useAppStore } from '../../../store/app'
import { TONS_UM_MATIZ } from '../../../lib/areaInfluencia'
import { AREA_PTT, VISAO_ALCANCE_TODOS, VISAO_TODOS } from '../areaInfluencia.fixture'
import { AreaInfluenciaBloco } from './AreaInfluenciaBloco'

const propsMapa = vi.fn()
vi.mock('../../../components/maps/Coropletico', () => ({ Coropletico: (p: { descricao: string }) => { propsMapa(p); return <div data-testid="coropletico" aria-label={p.descricao} /> } }))
vi.mock('../../../hooks/entidades', async (original) => ({ ...(await original<object>()), useCentroides: () => ({ data: { '9900001': [-46.7, -23.6], '9900004': [-47.1, -22.9] } }) }))

beforeEach(() => { propsMapa.mockClear(); useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' }) })

function montar() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><AreaInfluenciaBloco {...({ dados: { code: 'za' }, snapshot: '2026-09-20' } as any)} /></MemoryRouter></QueryClientProvider>)
}
const servir = (corpo: object | null, status = 200) => server.use(http.get('*/api/v1/ixps/za/area-influencia', ({ request }) => {
  const u = new URL(request.url)
  expect(u.searchParams.get('opcional')).toBe('true')
  return status === 204 ? new HttpResponse(null, { status: 204 }) : HttpResponse.json(corpo as object)
}))
const ultimoCor = () => propsMapa.mock.calls[propsMapa.mock.calls.length - 1][0].cor as unknown[]

describe('bloco Área de influência observada do PTT', () => {
  it('mostra cartões, as frases que respondem às duas perguntas e a legenda de um só tom', async () => {
    servir(AREA_PTT)
    montar()
    expect(await screen.findByTestId('area-kpis')).toBeTruthy()
    const kpis = screen.getByTestId('area-kpis').textContent ?? ''
    expect(kpis).toContain('12 km')                                               // P50 dos diretos (a visão que abre)
    expect(kpis).toContain('600')                                                 // acessos atribuídos
    const texto = screen.getByTestId('resumo-em-texto').textContent ?? ''
    expect(texto).toContain('Os participantes diretamente conectados atuam, na maior parte (P50), a até 12 km; quase todos (P80), a até 80 km')
    expect(texto).toContain('Considerando também quem anuncia pelo PTT sem estar conectado, a área chega a 200 km')
    const legenda = screen.getByTestId('legenda-area')
    expect(within(legenda).getAllByRole('listitem').length).toBe(5)               // três faixas, sem acessos e o PIX
    expect(legenda.textContent).toContain('A cor só ordena as faixas')
  })

  it('o seletor troca a visão, os cartões e a cor do mapa; o PIX vai ao mapa como pontos', async () => {
    servir(AREA_PTT)
    montar()
    await screen.findByTestId('area-kpis')
    expect(screen.getByRole('button', { name: /Influência provável dos diretamente conectados/ }).getAttribute('aria-pressed')).toBe('true')
    const corDiretos = JSON.stringify(ultimoCor())
    expect(ultimoCor()).toContain(TONS_UM_MATIZ[1])
    fireEvent.click(screen.getByRole('button', { name: /Influência provável de todos que anunciam/ }))
    expect(screen.getByRole('button', { name: /Influência provável de todos que anunciam/ }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByTestId('area-kpis').textContent).toContain('20 km')        // P50 de todos
    expect(JSON.stringify(ultimoCor())).not.toBe(corDiretos)
    const p = propsMapa.mock.calls[propsMapa.mock.calls.length - 1][0]
    expect(p.pontos).toEqual([{ lat: -23.6, lon: -46.7 }, { lat: -23.5, lon: -46.6 }])
    expect(p.descricao).toContain('PIX')
  })

  it('o seletor tem quatro opções, na ordem: influência provável e alcance, dos conectados e de todos', async () => {
    servir(AREA_PTT)
    montar()
    await screen.findByTestId('area-kpis')
    const botoes = within(screen.getByTestId('seletor-visao')).getAllByRole('button').map((b) => b.textContent)
    expect(botoes).toEqual(['Influência provável dos diretamente conectados', 'Influência provável de todos que anunciam', 'Alcance dos diretamente conectados', 'Alcance de todos que anunciam'])
  })

  it('as visões de alcance trocam cartões, frases, mapa e tabelas, sem disputa entre PTTs', async () => {
    servir(AREA_PTT)
    montar()
    await screen.findByTestId('area-kpis')
    fireEvent.click(screen.getByRole('button', { name: 'Alcance dos diretamente conectados' }))
    expect(screen.getByRole('button', { name: 'Alcance dos diretamente conectados' }).getAttribute('aria-pressed')).toBe('true')
    const kpis = screen.getByTestId('area-kpis').textContent ?? ''
    expect(kpis).toContain('40 km')                                              // P50 do alcance dos diretos
    expect(kpis).toContain('Acessos no alcance')
    const texto = screen.getByTestId('resumo-em-texto').textContent ?? ''
    expect(texto).toContain('Considerando todos os municípios onde atuam as operadoras diretamente conectadas, sem descontar PTTs mais próximos, a maioria (P50) está a até 40 km; quase todos (P80), a até 300 km; o P90 é 520 km.')
    expect(texto).toContain('Considerando todos os municípios onde atuam as operadoras que anunciam pelo PTT, diretas e indiretas, sem descontar PTTs mais próximos, a maioria (P50) está a até 60 km')
    expect(texto).not.toContain('Os participantes diretamente conectados atuam')
    expect(propsMapa.mock.calls[propsMapa.mock.calls.length - 1][0].descricao).toContain('no alcance do PTT Arandurápolis')
    expect(screen.getByTestId('tabela-faixas').textContent).toContain('Acessos no alcance')
    fireEvent.click(screen.getByRole('button', { name: 'Alcance de todos que anunciam' }))
    expect(screen.getByTestId('area-kpis').textContent).toContain('60 km')
  })

  it('tabela por faixa e tabela de municípios com nomes, filtro e paginação (alternativa textual ao mapa)', async () => {
    const muitos = Object.fromEntries(Array.from({ length: 120 }, (_, i) => [String(9000000 + i), [1000 - i, (i % 3) + 1]]))
    servir({ ...AREA_PTT, visoes: { ...AREA_PTT.visoes, diretos: { ...VISAO_TODOS, municipios: 120, municipios_faixa: muitos } }, municipios_nomes: Object.fromEntries(Object.keys(muitos).map((k, i) => [k, `Cidade ${i}/SP`])) })
    montar()
    await screen.findByTestId('tabela-faixas')
    const faixas = screen.getByTestId('tabela-faixas')
    expect(within(faixas).getAllByRole('row').length).toBe(4)                     // cabeçalho e as três faixas
    expect(faixas.textContent).toContain('além de 200 km')
    const det = screen.getByTestId('tabela-municipios') as HTMLDetailsElement
    expect(det.textContent).toContain('(120)')
    const linhas = () => within(det).getAllByRole('row').length - 1
    expect(linhas()).toBe(50)
    fireEvent.click(within(det).getByRole('button', { name: /Mostrar mais 50/ }))
    expect(linhas()).toBe(100)
    fireEvent.change(within(det).getByRole('combobox'), { target: { value: '3' } })
    expect(linhas()).toBe(40)
    expect(within(det).getAllByRole('rowheader')[0].textContent).toMatch(/^Cidade \d+\/SP$/)
  })

  it('visão sem acessos atribuídos avisa, e o seletor marca "sem dados"', async () => {
    servir({ ...AREA_PTT, visoes: { diretos: null, todos: VISAO_TODOS, alcance_diretos: null, alcance_todos: VISAO_ALCANCE_TODOS } })
    montar()
    await screen.findByTestId('area-kpis')                                         // abre em "todos", a que tem dados
    fireEvent.click(screen.getByRole('button', { name: /Influência provável dos diretamente conectados \(sem dados\)/ }))
    expect(screen.getByTestId('area-sem-visao').textContent).toContain('Nenhuma operadora tem acessos atribuídos a este PTT')
    expect(screen.getByTestId('resumo-em-texto').textContent).toContain('Nenhum participante diretamente conectado com prefixo próprio visto neste PTT')
  })

  it('PIX aproximado é dito na página, com a contagem por regra', async () => {
    servir(AREA_PTT)
    montar()
    const nota = await screen.findByTestId('area-pix-aproximado')
    expect(nota.textContent).toContain('1 PIX deste PTT não tem coordenada no cadastro e teve a posição aproximada')
    expect(nota.textContent).toContain('1 pela sede do PTT')
  })

  it('o "Como ler" traz o método, as ressalvas e o selo inferido', async () => {
    servir(AREA_PTT)
    montar()
    await screen.findByTestId('area-kpis')
    const t = screen.getByText('Como ler a área de influência').closest('details')!.textContent ?? ''
    for (const parte of [/influência provável/, /alcance/, /não disputam/, /um município pode estar no alcance de vários PTTs/, /PTT mais próximo entre os que a operadora enxerga/, /linha reta/, /Não há exclusão de operadoras/, /centroide do município do endereço/, /mês 2026-08 do SICI/, /inferido/, /não é cobertura de rede/, /Nenhum acesso conta duas vezes/]) expect(t).toMatch(parte)
  })

  it('snapshot sem o artefato (204) mostra o aviso e nenhum mapa', async () => {
    servir(null, 204)
    montar()
    expect(await screen.findByText(/não foi calculada para este snapshot/)).toBeTruthy()
    await waitFor(() => expect(screen.queryByTestId('coropletico')).toBeNull())
  })

  it('o texto visível não usa travessão', async () => {
    servir(AREA_PTT)
    montar()
    await screen.findByTestId('area-kpis')
    expect(screen.getByTestId('area-influencia').textContent).not.toMatch(/[—–]/)
  })
})
