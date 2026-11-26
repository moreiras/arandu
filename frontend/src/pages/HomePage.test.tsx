// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { server } from '../test/server'
import { useAppStore } from '../store/app'
import { CARTOES } from '../features/home/cartoes'
import { DESTAQUES, cartaoDe, consultaDoDestaque } from '../features/home/regrasDestaques'
import { PORTAS } from '../features/home/PortasPorPublico'
import { montarKpis } from '../features/home/kpisBrasilEmNumeros'
import { routeAccess } from '../auth/accessPolicy'
import { HomePage } from './HomePage'
import { SITE } from '../lib/site'

// `pct`: % dos ASes alocados que anunciam IPv6 na tabela global; `br_ipv6_pct` (alocado ou anunciado) fica bem acima e não deve ser o exibido.
const resumo = (asns: number, pct: number, ok: number) => ({ total_asns_br: asns, br_asns_ft_v6: Math.round((asns * pct) / 100), br_ipv6_pct: 97.1, ixps_ok: ok, ixps_partial: 0, br_apnic_users_total: 2241254 })
const sici = { mes_referencia: '2026-08', total_acessos: 621868, operadoras_ativas: 1142, municipios_atendidos: 12, por_meio: { Fibra: 497494 }, serie_total: [{ mes: '2026-07', acessos: 600000, cnpjs: 1100 }, { mes: '2026-08', acessos: 621868, cnpjs: 1142 }] }

const montar = () => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter><HomePage /></MemoryRouter>
  </QueryClientProvider>,
)

beforeEach(() => {
  localStorage.clear()
  useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' })
  server.use(
    http.get('*/api/v1/brasil/snapshots/:date', ({ params }) => HttpResponse.json({
      date: params.date, summary: params.date === '2026-09-20' ? resumo(1136, 67.2, 2) : resumo(1130, 66.9, 2),
      manifest: { comparado_com: params.date === '2026-09-20' ? '2026-09-13' : null, sources: [{ id: 'anatel_sici', as_of: '2026-08', frescor: 'ok' }] },
    })),
    http.get('*/api/v1/acessos/stats', () => HttpResponse.json(sici)),
    http.get('*/api/v1/brasil/indicadores', () => HttpResponse.json({ snapshot_date: '2026-09-20',
      ipv6: { usuarios: 1000, usuarios_ipv6: 412, pct_usuarios_ipv6: 41.2, asns_com_estimativa: 10, asns_com_ipv6: 7, fonte: 'APNIC', nota: '' },
      dnssec: { asns: 5, media_ponderada_pct: 39.7 }, rov: { asns: 5, media_ponderada_pct: 7.9 },
      prontidao: { agregado: { asns: 10, classes: {}, asns_com_indice: 9, media_ponderada_usuarios: 60.6, mediana: 50.7, cobertura_pilares: {}, medicoes: {} }, pilares: {} } })),
    http.get('*/api/v1/ufs', () => HttpResponse.json({ snapshot_date: '2026-09-20', total: 2, items: [
      { uf: 'SP', ptts: 3, municipios: 600, acessos: 9e6, fibra_pct: 70, asns: 900, usuarios: 3e7, municipios_sem_ptt: 30, domicilios: 1.6e7, penetracao: 0.8 },
      { uf: 'AM', ptts: 0, municipios: 60, acessos: 4e5, fibra_pct: 30, asns: 20, usuarios: 1e6, municipios_sem_ptt: 40, domicilios: 1e6, penetracao: 0.4 },
    ] })),
    http.get('*/api/v1/brasil/destaques', () => HttpResponse.json({ snapshot_date: '2026-09-20',
      destaques: { 'grandes-sem-asn': { total: 12 }, 'sem-rpki': { total: 5 }, 'monopolio-local': { total: 8 }, divergencias: { total: 3 } },
      o_que_mudou: { total: 37, de: '2026-09-13', mais_recente: '2026-10-31' } })),
    http.get('*/api/v1/query/:colecao', () => HttpResponse.json({ items: [{ asn: 64500, uf: 'PR', data: '2026-10-31' }], total: 37 })),
    http.get('*/api/v1/acessos/divergencias', () => HttpResponse.json({ items: [{ asn: 1 }], total: 3 })),
  )
})

describe('home nova', () => {
  it('tem busca grande, síntese, cinco portas por lente, números, cartograma, destaques e o que mudou', async () => {
    montar()
    expect(screen.getByRole('heading', { level: 1, name: SITE.nomeExtenso })).toBeInTheDocument()
    expect(screen.getAllByRole('combobox', { name: 'Buscar no site' }).length).toBeGreaterThan(0)
    expect(screen.getByText('Por exemplo:')).toBeInTheDocument()
    expect(PORTAS).toHaveLength(5)
    for (const p of PORTAS) expect(screen.getByTestId(`porta-${p.id}`)).toBeInTheDocument()
    expect(await screen.findByTestId('resumo-em-texto')).toBeInTheDocument()
    // 8 de rede e mercado + 4 de IPv6 e segurança
    expect(await screen.findAllByTestId('kpi')).toHaveLength(12)
    expect(await screen.findByText('41,2%')).toBeInTheDocument()
    expect(await screen.findByTestId('cartograma')).toBeInTheDocument()
    const destaques = await screen.findAllByTestId('destaque')
    expect(destaques).toHaveLength(DESTAQUES.length)
    // os totais vêm de `/brasil/destaques` (rota fixa e aberta, TRANSV-E20), um por destaque
    await waitFor(() => expect(destaques.map((d) => d.querySelector('[aria-live]')?.textContent)).toEqual(['12', '5', '8', '3']))
    await waitFor(() => expect(screen.getByTestId('o-que-mudou')).toHaveTextContent('37 ASes brasileiros novos confirmados na tabela de roteamento desde 13/09/2026, o mais recente em 31/10/2026'))
  })

  it('indicadores têm acento de cor por tipo (rede em azul, IPv6 em violeta, mercado em verde-água)', async () => {
    montar()
    const kpis = await screen.findAllByTestId('kpi')
    expect(kpis[0].className).toContain('border-l-v4-500')
    expect(kpis[1].className).toContain('border-l-v6-500')
    expect(kpis[4].className).toContain('border-l-mercado-500')
    expect(kpis.every((k) => /border-l-/.test(k.className))).toBe(true)
  })

  it('faixa de números: valor, variação sobre o snapshot anterior e fonte+data no tooltip', async () => {
    montar()
    await waitFor(() => expect(screen.getAllByTestId('kpi')[0]).toHaveTextContent('1.136'))
    const ases = screen.getAllByTestId('kpi')[0]
    expect(await within(ases).findByText(/\+6 desde o snapshot anterior/)).toBeInTheDocument()
    await waitFor(() => expect(screen.getAllByTestId('kpi')[4]).toHaveTextContent('622 mil'))
    // PT-30: fonte e data saem do cartão e ficam no bloco recolhido da seção (no DOM)
    expect(ases.textContent).not.toMatch(/delegated-extended|ref\./)
    const blocos = screen.getAllByTestId('fontes-e-datas').map((b) => b.textContent!).join(' ')
    expect(blocos).toMatch(/LACNIC.*referência: 20\/09\/2026/)
    expect(blocos).toMatch(/SICI.*referência: 08\/2026/)
  })

  it('cartograma normalizado: começa pela penetração e não oferece métricas absolutas', async () => {
    montar()
    const grade = await screen.findByTestId('cartograma')
    expect(grade).toHaveTextContent('80')       // SP: 0,8 × 100
    const grupo = screen.getByRole('group', { name: 'Métrica do cartograma' })
    expect(within(grupo).getAllByRole('button').map((b) => b.textContent)).toEqual(['Acessos por 100 domicílios', '% de fibra', '% de municípios longe de PTT'])
    expect(within(grupo).getByRole('button', { name: 'Acessos por 100 domicílios' })).toHaveAttribute('aria-pressed', 'true')
    expect(within(grupo).queryByText('Acessos fixos')).toBeNull()
    fireEvent.click(within(grupo).getByRole('button', { name: '% de fibra' }))
    expect(screen.getByTestId('cartograma')).toHaveTextContent('70%')
  })

  it('a home responde só com rotas abertas na entrada e não aponta mais para a versão anterior', () => {
    expect(routeAccess('/')).toBe('open')
    montar()
    expect(screen.queryByRole('link', { name: '/inicio-classico' })).toBeNull()
  })
})

describe('destaques e faixa (lógica)', () => {
  it('cada destaque aponta para um cartão que existe, com consulta de uma chamada e limite 1', () => {
    for (const d of DESTAQUES) {
      expect(CARTOES.some((c) => c.id === d.cartaoId)).toBe(true)
      expect(cartaoDe(d).fontes.length).toBeGreaterThan(0)
      const c = consultaDoDestaque(d)
      expect(c.tipo === 'query' ? c.corpo.limit : c.params.limit).toBe(1)
    }
    expect(DESTAQUES.length).toBeLessThanOrEqual(5)
  })
  it('cada número da home mostra selo, fonte e data de referência em texto visível (PT-14)', async () => {
    montar()
    await waitFor(() => expect(screen.getAllByTestId('kpi')[0]).toHaveTextContent('1.136'))
    await waitFor(() => expect(screen.getAllByTestId('kpi')[4]).toHaveTextContent('622 mil'))
    const kpis = screen.getAllByTestId('kpi')
    for (const k of kpis) expect(k.querySelector('[data-kpi-selo]'), k.textContent ?? '').not.toBeNull()
    expect(kpis[0].querySelector('[data-kpi-selo]')).toHaveAttribute('data-kpi-selo', 'fato')
    expect(kpis[3].querySelector('[data-kpi-selo]')).toHaveAttribute('data-kpi-selo', 'estimado')
    const itens = (await screen.findAllByTestId('fontes-e-datas')).flatMap((b) => [...b.querySelectorAll('[data-fonte-item]')].map((li) => li.textContent!))
    expect(itens.some((t) => /Fato.*LACNIC.*referência: 20\/09\/2026/.test(t))).toBe(true)
    expect(itens.some((t) => /Estimado.*APNIC.*referência: 20\/09\/2026/.test(t))).toBe(true)
    expect(itens.some((t) => /Fato.*SICI, Anatel.*referência: 08\/2026/.test(t))).toBe(true)
  })
  it('montarKpis: todo indicador tem selo e o de usuários APNIC é estimado', () => {
    const { rede, mercado } = montarKpis(resumo(1136, 67.2, 2) as never, null, sici as never, '2026-09-20')
    for (const k of [...rede, ...mercado]) expect(['fato', 'estimado', 'inferido'], k.id).toContain(k.selo)
    expect(rede.find((k) => k.id === 'usuarios')?.selo).toBe('estimado')
  })
  it('montarKpis: sem snapshot anterior não inventa variação e dado ausente vira nulo', () => {
    const k = montarKpis(resumo(1136, 67.2, 2) as never, null, null, '2026-09-20')
    expect(k.rede[0].valor).toBe('1.136')
    expect(k.rede.every((x) => x.variacao === undefined)).toBe(true)
    expect(k.mercado.every((x) => x.valor === null)).toBe(true)
    const j = montarKpis(null, null, null, null)
    expect([...j.rede, ...j.mercado].every((x) => x.valor === null)).toBe(true)
  })
  it('montarKpis: IPv6 em pontos percentuais e acessos pelo mês anterior da série', () => {
    const k = montarKpis(resumo(1136, 67.2, 2) as never, resumo(1130, 66.9, 2) as never, sici as never, '2026-09-20')
    expect(k.rede[1].valor).toBe('67,2%')
    expect(k.rede[1].variacao?.texto).toBe('+0,3 p.p. desde o snapshot anterior')
    expect(k.rede[2].variacao?.texto).toBe('sem variação')
    expect(k.mercado[0].variacao?.texto).toBe('+3,6% desde 07/2026')
    expect(k.mercado[1].valor).toBe('80%')
  })
})
