// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { server } from '../test/server'
import { useAppStore } from '../store/app'
import { blocosDe } from '../features/entidade/registry'
import '../features/municipio'
import '../features/uf'
import { MunicipioPage } from './MunicipioPage'
import { UFPage } from './UFPage'

vi.mock('../features/municipio/MapaRaio', () => ({ MapaRaio: ({ conjunto }: { conjunto: { selecionados: unknown[]; foraDoLimite: unknown[] } }) => <div data-testid="mapa-raio-falso">{conjunto.selecionados.length}+{conjunto.foraDoLimite.length}</div> }))

const operador = (cnpj: string, empresa: string, acessos: number, asns: number[]) => ({ cnpj, empresa, acessos, asns, share: 50, pf: 1, pj: 1 })
const fixo = {
  snapshot_date: '2026-09-20', mes_referencia: '2026-08', ibge: '3205309', nome: 'Vitória', uf: 'ES', acessos: 1000, pf: 800, pj: 200, capacidade_mbps: 1,
  operadores: [operador('11111111000111', 'Fibra Vix', 600, [65001]), operador('22222222000122', 'Net Sem AS', 400, [])], operadores_count: 2, hhi: 5200, share_maior: 60,
}
const movel = { snapshot_date: '2026-09-20', mes_referencia: '2026-08', ibge: '3205309', nome: 'Vitória', uf: 'ES', acessos: 5000, pf: 4000, pj: 1000, operadores: [operador('33333333000133', 'Móvel SA', 5000, [65002])], operadores_count: 1, hhi: 10000, share_maior: 100 }
const pix = { type: 'FeatureCollection', features: [
  { type: 'Feature', geometry: { type: 'Point', coordinates: [-40.3, -20.3] }, properties: { role: 'pix', ixp_code: 'vix', ixp_name: 'Vitória' } },
  { type: 'Feature', geometry: { type: 'Point', coordinates: [-46.6, -23.5] }, properties: { role: 'pix', ixp_code: 'sp', ixp_name: 'São Paulo' } },
] }
const semEnvelope = <T extends object>(d: T) => { const { snapshot_date: _a, ibge: _b, nome: _c, uf: _d, ...resto } = d as Record<string, unknown>; return resto }
/** Perfil `/municipios/{ibge}`: o que as 4 rotas antigas davam, numa resposta; PTTs com a distância já calculada pelo servidor. */
const perfil = (o: { fixo?: object | null; movel?: object | null; ibge?: string; centroide?: [number, number] | null }) => {
  const ibge = o.ibge ?? '3205309'
  const com = o.centroide !== null
  return {
    snapshot_date: '2026-09-20', ibge, nome: 'Vitória', uf: 'ES',
    fixo: o.fixo ? semEnvelope(o.fixo) : null, movel: o.movel ? semEnvelope(o.movel) : null,
    centroide: com ? (o.centroide ?? [-40.34, -20.31]) : null,
    ptts_proximos: com ? [{ codigo: 'vix', nome: 'Vitória', lon: -40.3, lat: -20.3, km: 4.8 }, { codigo: 'sp', nome: 'São Paulo', lon: -46.6, lat: -23.5, km: 680 }] : [],
  }
}
const regiao = (ibges: string[]) => ({
  snapshot_date: '2026-09-20', natureza: 'inferido', limites: 'Inferência dos três vínculos.', fontes: {}, ptts_nomes: { vix: 'Vitória', sp: 'São Paulo' }, ibges, municipios_com_dados: ibges.length,
  asns: { total: 4, por_vinculo: { sici: 3, sede: 1, geo: 2 } },
  participacao_ptts: { com_ptt_direto: 1, so_indireto: 2, sem_ptt: 1, pct_direto: 25, pct_indireto: 50, pct_sem_ptt: 25,
    ptts: [{ codigo: 'vix', direto: 1, indireto: 2, total: 3, pct_direto: 25, pct_total: 75 }] },
  transito: [{ asn: 3356, nome: 'Level 3 Parent, LLC, US', asns: 3, pct: 75, niveis: { confirmado: 1, provavel: 2, possivel: 0 }, na_regiao: false, ptts_diretos: ['sp'] }], transito_total: 1,
  carregadores: [{ asn: 65001, nome: 'Fibra Vix', asns: 2, pct: 100, na_regiao: true, ptts_diretos: ['vix'] }], carregadores_total: 1, indiretos_sem_carregador: 0,
  prontidao: { asns_no_indice: 1, regras: { versao: 1, hash: 'abc', pilares: {} }, limites: 'Não é veredito.', fontes: {},
    agregado: { asns: 1, asns_com_indice: 1, classes: { pronto: 1, em_progresso: 0, atrasado: 0, sem_dados: 0 }, media_ponderada_usuarios: 91.5, mediana: 91.5, usuarios: 100,
      cobertura_pilares: { filtragem: 1, anti_spoofing: 0, coordenacao: 1, validacao_global: 1 }, medicoes: { rov: { pilar: 'filtragem', asns: 1, media: 98, media_ponderada_usuarios: 98 }, aspa: { pilar: 'validacao_global', asns: 0, media: null, media_ponderada_usuarios: null } } },
    brasil: { asns: 9000, asns_com_indice: 8000, classes: { pronto: 1, em_progresso: 1, atrasado: 1, sem_dados: 1 }, media_ponderada_usuarios: 60, mediana: 55, usuarios: 1, cobertura_pilares: { filtragem: 1, anti_spoofing: 1, coordenacao: 1, validacao_global: 1 }, medicoes: { rov: { pilar: 'filtragem', asns: 5, media: 70, media_ponderada_usuarios: 80 } } } },
  provedores: [
    { asn: 65001, nome: 'Fibra Vix', vinculos: ['sici', 'sede'], acessos_fixo: 600, acessos_movel: 0, prefixos_geo: 3, ptts_diretos: ['vix'], ptts_indiretos: [] },
    { asn: 65099, nome: 'Só IPs Ltda', vinculos: ['geo'], acessos_fixo: 0, acessos_movel: 0, prefixos_geo: 7, ptts_diretos: [], ptts_indiretos: ['sp'] },
  ],
  provedores_total: 4,
})
const centroides = { '3205309': [-40.34, -20.31], '3203205': [-41.5, -18.5], '3205200': [-40.4, -20.3] }   // Vila Velha fica a ~6 km de Vitória; 3203205 a ~250 km

function montar(rota: string, caminho: string, el: JSX.Element) {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[caminho + (caminho.includes('?') ? '&' : '?') + 'versao=1']}><Routes><Route path={rota} element={el} /></Routes></MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' })
  server.use(
    http.get('*/api/v1/map/pix', () => HttpResponse.json(pix)),
    http.get('*/api/v1/regiao', ({ request }) => HttpResponse.json(regiao(new URL(request.url).searchParams.get('ibges')!.split(',')))),
    http.get('*/municipios-centroides.json', () => HttpResponse.json(centroides)),
    http.get('*/api/v1/brasil/snapshots/:date', () => HttpResponse.json({ date: '2026-09-20', summary: null, manifest: { sources: [{ id: 'anatel_sici', as_of: '2026-08', frescor: 'ok' }] } })),
  )
})

describe('registro de blocos de município e UF', () => {
  it('município: painel → mercado fixo → mercado móvel → rede → infraestrutura', () => {
    expect(blocosDe('municipio').map((b) => b.id)).toEqual(['painel', 'penetracao', 'semelhantes', 'mercado-fixo', 'mercado-grupos', 'serie-mercado', 'indicadores', 'mercado-movel', 'estacoes-smp', 'fust', 'qualidade', 'reclamacoes', 'consumidor', 'contratos', 'rede-territorio', 'rede', 'regiao-provedores', 'regiao-ptts', 'regiao-transito', 'regiao-carregadores', 'regiao-prontidao', 'infraestrutura'])
  })
  it('UF: síntese → painel → PTTs → municípios → sem PTT → operadoras → linha do tempo', () => {
    expect(blocosDe('uf').map((b) => b.id)).toEqual(['sintese', 'painel', 'mapa-municipios', 'posicao', 'penetracao', 'tic-domicilios', 'demanda-oferta', 'estacoes-smp', 'fust', 'empresas-telecom', 'declaracao-sici', 'qualidade', 'reclamacoes', 'consumidor', 'prontidao', 'rede-territorio', 'transito', 'radar', 'exposicao', 'ptts', 'mercado-grupos', 'municipios', 'sem-ptt', 'operadoras', 'linha-do-tempo'])
  })
})

describe('página de município', () => {
  it('mostra fixo e móvel, as ASNs, o PTT mais próximo com a distância e a proveniência', async () => {
    server.use(http.get('*/api/v1/municipios/:ibge', () => HttpResponse.json(perfil({ fixo: { ...fixo, fibra: 750, fibra_pct: 75 }, movel }))))
    montar('/municipio/:ibge', '/municipio/3205309', <MunicipioPage />)
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent('Vitória ES')
    expect(await screen.findByText('Quem oferece banda larga em Vitória')).toBeInTheDocument()
    expect(screen.getByText('Telefonia móvel em Vitória')).toBeInTheDocument()
    expect(await screen.findByText('Vitória', { selector: '.text-lg' })).toBeInTheDocument()    // KPI "PTT mais próximo"
    expect(screen.getByRole('link', { name: 'AS65001 · Fibra Vix' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'AS65002 · Móvel SA' })).toBeInTheDocument()
    const prov = screen.getAllByTestId('proveniencia')
    expect(prov.length).toBeGreaterThanOrEqual(4)
    expect(screen.getByRole('link', { name: 'ES' })).toHaveAttribute('href', '/uf/ES')
    // fibra (KPI + barra) e distâncias aos PTTs vêm do perfil
    expect(screen.getByText('Fibra')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: '75% dos acessos fixos por fibra' })).toBeInTheDocument()
    expect(screen.getByText('680 km')).toBeInTheDocument()
  })

  it('faz uma única chamada de dados à API para o município (perfil), sem as rotas antigas nem o PIX', async () => {
    const chamadas: string[] = []
    server.use(http.get('*/api/v1/municipios/:ibge', ({ request }) => { chamadas.push(new URL(request.url).pathname); return HttpResponse.json(perfil({ fixo, movel })) }))
    server.use(
      http.get('*/api/v1/acessos/municipio/:ibge', () => { chamadas.push('antiga-fixo'); return HttpResponse.json(fixo) }),
      http.get('*/api/v1/acessos-movel/municipio/:ibge', () => { chamadas.push('antiga-movel'); return HttpResponse.json(movel) }),
      http.get('*/api/v1/map/pix', () => { chamadas.push('pix'); return HttpResponse.json(pix) }),
    )
    montar('/municipio/:ibge', '/municipio/3205309', <MunicipioPage />)
    await screen.findByText('Quem oferece banda larga em Vitória')
    expect(chamadas).toEqual(['/api/v1/municipios/3205309'])           // a região é outra rota: uma chamada a mais, não uma por município
  })

  it('blocos da região: provedores com o vínculo (inclusive só por IPs), PTTs com nome, trânsito e carregadores', async () => {
    server.use(http.get('*/api/v1/municipios/:ibge', () => HttpResponse.json(perfil({ fixo, movel }))))
    montar('/municipio/:ibge', '/municipio/3205309', <MunicipioPage />)
    const prov = await screen.findByTestId('regiao-provedores')
    expect(prov).toHaveTextContent('4 ASNs ligados ao município')
    const so = within(prov).getByText('Só IPs Ltda').closest('tr')!
    expect(within(so).getByText('IPs')).toBeInTheDocument()
    expect(within(so).queryByText('SICI')).toBeNull()
    const ptts = await screen.findByTestId('regiao-ptts')
    expect(ptts).toHaveTextContent('25%')
    expect(await within(ptts).findByRole('link', { name: 'Vitória' })).toHaveAttribute('href', '/ixp/vix')
    expect(screen.getByTestId('regiao-transito')).toHaveTextContent('Level 3 Parent')
    expect(screen.getByTestId('regiao-transito')).toHaveTextContent('1 / 2 / 0')
    expect(screen.getByTestId('regiao-carregadores')).toHaveTextContent('da região')
    const pr = await screen.findByTestId('regiao-prontidao')                       // 1 ASN: vale, com o aviso de que poucos ASNs sustentam o número
    expect(pr).toHaveTextContent('1 de 1 ASNs da região com índice')
    expect(pr).toHaveTextContent('Poucos ASNs sustentam este recorte (1)')
    expect(within(pr).getByText('ROV: não alcança rota RPKI-inválida (APNIC)').closest('tr')).toHaveTextContent('98%')
    expect(within(pr).queryByText('Publica ASPA')).toBeNull()                     // sem ASN com o dado, a linha não aparece
  })

  it('só com SICI móvel (sem fixo) ainda mostra o município e o bloco móvel, sem o fixo', async () => {
    server.use(http.get('*/api/v1/municipios/:ibge', () => HttpResponse.json(perfil({ movel }))))
    montar('/municipio/:ibge', '/municipio/3205309', <MunicipioPage />)
    expect(await screen.findByText('Telefonia móvel em Vitória')).toBeInTheDocument()
    expect(screen.queryByText(/Quem oferece banda larga/)).toBeNull()
  })

  it('sem nenhum dos dois: "Município não encontrado"', async () => {
    server.use(http.get('*/api/v1/municipios/:ibge', () => new HttpResponse(null, { status: 204 })))
    montar('/municipio/:ibge', '/municipio/0000000', <MunicipioPage />)
    expect(await screen.findByText('Município não encontrado')).toBeInTheDocument()
  })

  it('sem centróide o painel avisa em vez de inventar distância', async () => {
    server.use(http.get('*/api/v1/municipios/:ibge', () => HttpResponse.json(perfil({ fixo, ibge: '9999999', centroide: null }))))
    montar('/municipio/:ibge', '/municipio/9999999', <MunicipioPage />)
    expect(await screen.findByText('centróide indisponível')).toBeInTheDocument()
    expect(screen.queryByText('Infraestrutura — PTTs próximos')).toBeNull()
  })
})

describe('página de município com raio', () => {
  const vila = { ...fixo, ibge: '3205200', nome: 'Vila Velha', acessos: 500, pf: 400, pj: 100, operadores: [operador('11111111000111', 'Fibra Vix', 300, [65001]), operador('44444444000144', 'Rede Vila', 200, [])], operadores_count: 2 }
  const chamadas: string[] = []
  const regioes: string[] = []
  beforeEach(() => {
    chamadas.length = 0
    regioes.length = 0
    server.use(http.get('*/api/v1/regiao', ({ request }) => { const q = new URL(request.url).searchParams.get('ibges')!; regioes.push(q); return HttpResponse.json(regiao(q.split(','))) }))
    server.use(http.get('*/api/v1/municipios/:ibge', ({ params }) => {
      chamadas.push(String(params.ibge))
      return HttpResponse.json(params.ibge === '3205200' ? perfil({ fixo: vila, ibge: '3205200', centroide: [-40.4, -20.3] }) : perfil({ fixo, movel }))
    }))
  })

  it('raio 0 não busca vizinhos e mostra o painel com o mapa e o resumo', async () => {
    montar('/municipio/:ibge', '/municipio/3205309', <MunicipioPage />)
    expect(await screen.findByText(/Só o município \(raio 0 km\)/)).toBeInTheDocument()
    await screen.findByText('Quem oferece banda larga em Vitória')
    expect(chamadas).toEqual(['3205309'])
    expect(screen.queryByTestId('banner-agregado')).toBeNull()
  })

  it('com ?raio= soma os municípios dentro do raio, com um perfil por município, e avisa que os blocos são a soma', async () => {
    montar('/municipio/:ibge', '/municipio/3205309?raio=30', <MunicipioPage />)
    expect(await screen.findByText('Quem oferece banda larga em 2 municípios')).toBeInTheDocument()
    expect(chamadas.sort()).toEqual(['3205200', '3205309'])                 // o distante (~250 km) não é buscado
    expect(regioes).toEqual(['3205309,3205200'])                            // a região usa os códigos do conjunto numa chamada só
    expect(screen.getByTestId('banner-agregado')).toHaveTextContent('2 municípios')
    expect(screen.getByTestId('resumo-raio')).toHaveTextContent('2 municípios num raio de 30 km')
    // Fibra Vix: 600 (Vitória) + 300 (Vila Velha) = 900 de 1.500 acessos (60%)
    const linha = screen.getByRole('link', { name: 'Fibra Vix' }).closest('tr')!
    expect(within(linha).getByText('900')).toBeInTheDocument()
    expect(within(linha).getByText('60%')).toBeInTheDocument()
    expect(screen.getByTestId('mapa-raio-falso')).toHaveTextContent('2+0')
    expect(screen.getByText('4,8 km do centróide do município central')).toBeInTheDocument()   // PTT: distância do central, não do conjunto
  })

  it('espaça as chamadas dos vizinhos (limite de taxa do nginx) e tenta de novo depois de um 429', async () => {
    let tentativasVila = 0
    server.use(http.get('*/api/v1/municipios/:ibge', ({ params }) => {
      if (params.ibge === '3205200' && ++tentativasVila === 1) return new HttpResponse('slow down', { status: 429 })
      return HttpResponse.json(params.ibge === '3205200' ? perfil({ fixo: vila, ibge: '3205200', centroide: [-40.4, -20.3] }) : perfil({ fixo, movel }))
    }))
    montar('/municipio/:ibge', '/municipio/3205309?raio=30', <MunicipioPage />)
    expect(await screen.findByText('Quem oferece banda larga em 2 municípios', {}, { timeout: 5000 })).toBeInTheDocument()
    expect(tentativasVila).toBe(2)
  })

  it('arrastar o slider leva o valor para a URL depois de uma pausa e busca os vizinhos', async () => {
    montar('/municipio/:ibge', '/municipio/3205309', <MunicipioPage />)
    const slider = await screen.findByLabelText('Raio em volta do município')
    fireEvent.change(slider, { target: { value: '30' } })
    expect(await screen.findByText('Quem oferece banda larga em 2 municípios', {}, { timeout: 3000 })).toBeInTheDocument()
    await waitFor(() => expect(chamadas).toContain('3205200'))
  })
})

const perfilUf = {
  snapshot_date: '2026-09-20', uf: 'ES', mes_referencia: '2026-08',
  totais: { municipios: 2, acessos: 9300, fibra_pct: 78.5, asns: 12, usuarios: 345678, municipios_sem_ptt: 1, acessos_sem_ptt: 300, raio_sem_ptt_km: 100 },
  ixps: [{ code: 'vix', name: 'Vitória', uf: 'ES', status: 'ok', asn_direct_union_count: 30, ixbr_members_count: 40 }],
  municipios: [
    { ibge: '3205309', nome: 'Vitória', acessos: 9000, operadores: 20, hhi: 1200, fibra_pct: 80, km_ptt: 4.8, ptt: 'Vitória', ptt_codigo: 'vix' },
    { ibge: '3203205', nome: 'Distante', acessos: 300, operadores: 3, hhi: 4000, fibra_pct: 40, km_ptt: 210, ptt: 'Vitória', ptt_codigo: 'vix' },
  ],
  operadoras: { total: 7, items: [{ cnpj: '11111111000111', empresa: 'Fibra Vix', razao_social: 'Fibra Vix Ltda', acessos: 600, municipios: 5, outorgas: 1, licenciado: true, ativo: true, acessos_pf: 1, acessos_pj: 1 }] },
}

describe('página de UF', () => {
  beforeEach(() => {
    server.use(http.get('*/api/v1/ufs/:uf', () => HttpResponse.json(perfilUf)))
  })

  it('traz PTTs, municípios, o município distante (> 100 km) e as operadoras, com indicadores', async () => {
    montar('/uf/:uf', '/uf/es', <UFPage />)
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent('Espírito Santo')
    expect(await screen.findByRole('heading', { name: 'PTTs na UF' })).toBeInTheDocument()
    expect(await screen.findByRole('region', { name: 'Municípios a mais de 100 km de um PTT' })).toBeInTheDocument()
    const semPtt = screen.getByRole('region', { name: 'Municípios a mais de 100 km de um PTT' })
    expect(within(semPtt).getByRole('link', { name: 'Distante' })).toHaveAttribute('href', '/municipio/3203205')
    expect(within(semPtt).queryByRole('link', { name: 'Vitória' })).toBeNull()      // Vitória tem PTT a poucos km
    expect(screen.getByRole('heading', { name: 'Operadoras na UF' })).toBeInTheDocument()
    expect(await screen.findByText('Usuários estimados em ASNs sediados na UF')).toBeInTheDocument()
    expect(screen.getByText('345.678')).toBeInTheDocument()
    expect(screen.getByText('78,5%')).toBeInTheDocument()
    // gráfico de faixas de distância: 9.000 acessos a até 50 km e 300 a mais de 100 km
    expect(screen.getByRole('img', { name: /até 50 km: 97%.*100–300 km: 3%/ })).toBeInTheDocument()
  })

  it('faz uma única chamada de dados à API para a UF (perfil), sem as rotas antigas nem o PIX', async () => {
    const chamadas: string[] = []
    server.use(
      http.get('*/api/v1/ufs/:uf', ({ request }) => { chamadas.push(new URL(request.url).pathname); return HttpResponse.json(perfilUf) }),
      http.get('*/api/v1/ixps', () => { chamadas.push('ixps'); return HttpResponse.json({ ixps: [] }) }),
      http.get('*/api/v1/acessos/municipios', () => { chamadas.push('municipios'); return HttpResponse.json({ items: [] }) }),
      http.get('*/api/v1/map/pix', () => { chamadas.push('pix'); return HttpResponse.json(pix) }),
    )
    montar('/uf/:uf', '/uf/es', <UFPage />)
    await screen.findByRole('heading', { name: 'Operadoras na UF' })
    expect(chamadas).toEqual(['/api/v1/ufs/ES'])
  })

  it('sigla inválida não consulta a API e explica', async () => {
    montar('/uf/:uf', '/uf/xx', <UFPage />)
    expect(await screen.findByText('UF não encontrada')).toBeInTheDocument()
  })
})
