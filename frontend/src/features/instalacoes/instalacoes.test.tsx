// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'

// MapLibre falso (jsdom não tem WebGL): a página monta o componente do mapa sem desenhar
vi.mock('maplibre-gl', () => {
  class Ctl { }
  class Map { addControl() {} on() {} once() {} isStyleLoaded() { return false } remove() {} resize() {} getSource() { return undefined } }
  return { Popup: Ctl, addProtocol: () => {}, setWorkerUrl: () => {}, NavigationControl: Ctl, ScaleControl: Ctl, AttributionControl: Ctl, Marker: Ctl, Map }
})

import { server } from '../../test/server'
import { InstalacoesAsnBloco } from '../asn/blocks/InstalacoesAsnBloco'
import { InstalacoesPtt } from '../ptt/blocks/InstalacoesBloco'
import { FacilitiesPage } from '../../pages/FacilitiesPage'
import { FacilityPage } from '../../pages/FacilityPage'
import { SeloCadastro, escapar, fmtMbps } from './comum'
import { paraGeoJson } from './MapaInstalacoes'
import type { FacilitiesAsn, FacilitiesLista, FacilitiesPtt, FacilityDetalhe, PeeringAsn, PortasIxp } from '../../types/api'

beforeAll(() => { vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} unobserve() {} }) })

const meta = { snapshot_date: '2026-11-05', coletado_em: '2026-11-06T23:31:08+00:00', fonte: { nome: 'PeeringDB', url: 'https://www.peeringdb.com' }, limites: 'Cadastro autodeclarado no PeeringDB, sem verificação independente.' }
const cad = (classe: 'recente' | 'parado' | 'antigo') => ({ classe, ultima_atualizacao: '2024-03-10', dias: 970, inferido: true as const })
const f1 = { id: 9101, nome: 'Datacenter Exemplo SP-1', org_nome: 'Operadora Fictícia S.A.', cidade: 'Arandurápolis', uf: 'SP', pais: 'BR', lat: -23.6, lon: -46.7, escopo: 'brasil' as const, n_redes: 6, n_ptts: 2, n_carriers: 2, cadastro: cad('recente') }
const f2 = { id: 9102, nome: 'Colo <b>Exemplo</b> RJ', org_nome: 'Colo Fictícia Ltda', cidade: 'Tupãnópolis', uf: 'RJ', pais: 'BR', lat: -22.9, lon: -43.2, escopo: 'brasil' as const, n_redes: 2, n_ptts: 1, n_carriers: 1, cadastro: cad('parado') }

describe('comum', () => {
  it('escapa HTML de nome vindo do cadastro (popup do mapa) e formata velocidade', () => {
    expect(escapar('<img src=x onerror=alert(1)> & "a"')).toBe('&lt;img src=x onerror=alert(1)&gt; &amp; &quot;a&quot;')
    expect(fmtMbps(10000)).toBe('10 Gbps')
    expect(fmtMbps(200)).toBe('200 Mbps')
    expect(fmtMbps(0)).toBe('—')
  })

  it('o selo de cadastro diz que é inferido e nunca chama a instalação de ativa ou abandonada', () => {
    render(<SeloCadastro c={cad('antigo')} />)
    const selo = screen.getByTestId('selo-cadastro')
    expect(selo.getAttribute('title')).toMatch(/Inferido/)
    expect(selo.getAttribute('title')).toMatch(/não a operação/)
    expect(document.body.textContent).not.toMatch(/abandonad|inativ|fechad|falid/i)
  })

  it('INST-E3 e P9: o selo mostra as duas datas do PeeringDB como vêm, inclusive 2025-09-26, sem explicar nem inferir a razão da data', () => {
    render(<SeloCadastro c={{ classe: 'parado', ultima_atualizacao: '2025-09-26', dias: 405, inferido: true, registro_atualizado: '2025-09-26', vinculo_atualizado: null }} />)
    const t = screen.getByTestId('selo-cadastro').textContent!
    expect(t).toBe('sem atividade no cadastro há 1 a 3 anos · registro: 2025-09-26 · último vínculo de rede: —')
    expect(document.body.textContent).not.toMatch(/lote|compartilhad|sem data própria/i)
  })

  it('só vira ponto no mapa a instalação com coordenada, e a classe do cadastro vai para a cor', () => {
    const g = paraGeoJson([f1, { ...f2, lat: undefined, lon: undefined }])
    expect(g.features).toHaveLength(1)
    expect(g.features[0].properties).toMatchObject({ id: 9101, classe: 'recente', redes: 6 })
  })
})

describe('bloco Instalações e peering do ASN', () => {
  const fac: FacilitiesAsn = { ...meta, asn: 64496, total: 2, nota: 'Instalações do Brasil em que a rede declara estar no PeeringDB.', items: [{ ...f1, ptts: ['za', 'zb'], no_vinculo_desde: '2020-01-01T00:00:00Z' }, { ...f2, ptts: [], no_vinculo_desde: '2018-01-01T00:00:00Z' }] }
  const peering: PeeringAsn = { ...meta, asn: 64496, escopo: 'Regional', ipv6: true, multicast: false, nunca_via_route_server: false, looking_glass: 'https://lg.example.org/', route_server: 'telnet://rs.example.org', criado: '2019-01-01T00:00:00Z', atualizado: '2026-05-01T00:00:00Z',
    instalacoes_declaradas: 3, instalacoes_br_observadas: 2, cadastro: cad('recente'), portas_externas: { ptts: [{ ixp: 'zx', portas: 2, velocidades_mbps: [10000, 100000], capacidade_mbps: 110000 }] } }

  it('mostra instalações com vínculo e selo inferido, atributos autodeclarados, URLs só como link se http(s) e as portas com a ressalva de capacidade', () => {
    render(<MemoryRouter><InstalacoesAsnBloco {...({ dados: { facilities: fac, peering } } as any)} /></MemoryRouter>)
    expect(screen.getByText(/2 instalações do Brasil/)).toBeTruthy()
    expect(screen.getByText('Datacenter Exemplo SP-1').getAttribute('href')).toBe('/instalacao/9101')
    expect(screen.getAllByTestId('selo-cadastro')).toHaveLength(3)                                            // 2 instalações + o registro da rede
    expect(screen.getByText('https://lg.example.org/').getAttribute('href')).toBe('https://lg.example.org/')
    expect(screen.getByText('telnet://rs.example.org').tagName).toBe('SPAN')                                  // telnet não vira link
    expect(screen.getByText(/2 portas, 10 Gbps \+ 100 Gbps \(soma 110 Gbps\)/)).toBeTruthy()
    expect(screen.getByText('Capacidade declarada, não tráfego.')).toBeTruthy()
    expect(screen.getAllByTestId('atribuicao-peeringdb').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Dado autodeclarado no/).length).toBeGreaterThan(0)
  })
})

describe('bloco Instalações do PTT', () => {
  const lista: FacilitiesPtt = { ...meta, ptt: 'za', total: 2, items: [f1, f2] }
  const portas: PortasIxp = { ...meta, ixp: 'zx', portas: 5, portas_com_velocidade: 5, membros: 5, capacidade_mbps: 50000, mediana_mbps: 10000, maior_mbps: 10000, por_velocidade: { '10000': 5 } }

  it('lista as instalações com o selo e, em PTT externo, as portas por velocidade', () => {
    render(<MemoryRouter><InstalacoesPtt facilities={lista} portas={portas} /></MemoryRouter>)
    expect(screen.getByText(/2 instalações/)).toBeTruthy()
    expect(screen.getByTestId('portas-ptt').textContent).toMatch(/5 porta\(s\) de 5 membro\(s\): mediana 10 Gbps, maior 10 Gbps, soma declarada 50 Gbps/)
    expect(screen.getByTestId('portas-ptt').textContent).toMatch(/10 Gbps: 5/)
  })
})

const montar = (ui: React.ReactElement, url: string) => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[url]}>{ui}</MemoryRouter></QueryClientProvider>,
)

describe('página de instalações', () => {
  it('lista com filtros que viram parâmetros da API e atribuição; o nome do cadastro não vira HTML', async () => {
    const chamadas: URLSearchParams[] = []
    const corpo: FacilitiesLista = { ...meta, escopo: { pais: 'BR' }, ordem: 'x', total: 2, items: [f1, f2], cobertura: { instalacoes_br: 2, com_ptt: 2, com_carrier: 2, ptts_ixbr: 40, ptts_ixbr_com_instalacao: 38, ptts_ixbr_sem_instalacao: ['ac', 'the'], ptts_externos: 5, ptts_externos_com_instalacao: 4, asns_br_no_peeringdb: 10, asns_br_com_instalacao: 4, cadastro_br: { recente: 1, parado: 1 } } }
    server.use(http.get('*/api/v1/facilities', ({ request }) => { chamadas.push(new URL(request.url).searchParams); return HttpResponse.json(corpo) }))
    const { container } = montar(<FacilitiesPage />, '/instalacoes')
    await screen.findByText('Datacenter Exemplo SP-1')
    expect(screen.getByTestId('total-instalacoes').textContent).toMatch(/2 instalações/)
    expect(screen.getByTestId('cobertura-ptts').textContent).toMatch(/38 de 40 aparecem em alguma instalação do PeeringDB/)
    expect(screen.getByTestId('cobertura-ptts').textContent).toContain('Sem instalação cadastrada no PeeringDB nesta coleta: AC, THE.')                    // INST-E2: quem falta, nomeado
    expect(container.querySelector('b')?.textContent ?? '').not.toBe('Exemplo')                              // "<b>" do nome é texto, não elemento
    expect(screen.getByText('Colo <b>Exemplo</b> RJ')).toBeTruthy()
    expect(screen.getByTestId('mapa-instalacoes')).toBeTruthy()
    expect(chamadas[0].get('limit')).toBe('100')                                                              // a prévia aberta; mais que isso exige login
    fireEvent.change(screen.getByRole('combobox', { name: /Cadastro/ }), { target: { value: 'parado' } })
    await waitFor(() => expect(chamadas.some((c) => c.get('cadastro') === 'parado')).toBe(true))
    expect(screen.getAllByText(/Dado autodeclarado no/).length).toBe(1)
  })
})

describe('página de uma instalação', () => {
  it('mostra PTTs com link conforme o tipo, carriers, campus e as redes com filtro de Brasil', async () => {
    const det: FacilityDetalhe = { ...meta, ...f1, escopo: 'brasil', n_redes_br: 1, redes_declaradas: 6, site: 'https://dc1.example.org', criado: '2012-03-01T00:00:00Z', atualizado: '2026-08-20T12:00:00Z',
      ixps: [{ ix_id: 9000, code: 'za', tipo: 'ixbr' }, { ix_id: 99001, code: 'zx', nome: 'IX Externo', tipo: 'externo' }, { ix_id: 3476, nome: 'Global Peer Exchange', tipo: 'outro' }],
      carriers: [{ id: 501, nome: 'Carrier Exemplo', org_nome: 'Carrier Fictícia S.A.' }], campus: { id: 7, nome: 'Campus Exemplo SP', cidade: 'Arandurápolis', uf: 'SP' },
      redes: [{ asn: 64496, nome: 'Rede BR', is_br: true, no_vinculo_desde: '2020-01-01T00:00:00Z' }, { asn: 15169, nome: 'Estrangeira', is_br: false }], redes_total: 2, redes_nota: 'Vínculos de redes a instalações do Brasil, como cadastrados no PeeringDB; não indicam tráfego nem contrato.' }
    server.use(http.get('*/api/v1/facilities/:id', () => HttpResponse.json(det)))
    const { Routes, Route } = await import('react-router-dom')
    montar(<Routes><Route path="/instalacao/:id" element={<FacilityPage />} /></Routes>, '/instalacao/9101')
    await screen.findByText('Datacenter Exemplo SP-1')
    expect(screen.getByText('ZA').getAttribute('href')).toBe('/ixp/za')
    expect(screen.getByText('IX Externo').getAttribute('href')).toBe('/ixp-externo/zx')
    expect(screen.getByText('Global Peer Exchange').tagName).toBe('SPAN')                                     // PTT que o Arandurapé não conhece não vira link
    expect(screen.getByText('Carrier Exemplo')).toBeTruthy()
    expect(screen.getByText(/Campus: Campus Exemplo SP/)).toBeTruthy()
    expect(screen.getByText('AS15169')).toBeTruthy()
    fireEvent.click(screen.getByRole('checkbox', { name: /só ASNs do Brasil/ }))
    expect(screen.queryByText('AS15169')).toBeNull()
    expect(screen.getByText('ver no PeeringDB').getAttribute('href')).toBe('https://www.peeringdb.com/fac/9101')
    expect(screen.getByText(/não indicam tráfego nem contrato/)).toBeTruthy()
  })

  it('instalação inexistente mostra aviso e link para a lista, sem erro cru', async () => {
    server.use(http.get('*/api/v1/facilities/:id', () => HttpResponse.json({ detail: 'não encontrada' }, { status: 404 })))
    const { Routes, Route } = await import('react-router-dom')
    montar(<Routes><Route path="/instalacao/:id" element={<FacilityPage />} /></Routes>, '/instalacao/1')
    await screen.findByText('Instalação não encontrada')
    expect(screen.getByText('Ver instalações').getAttribute('href')).toBe('/instalacoes')
  })
})

describe('cobertura de PTTs e coluna PTTs da lista (PT-24 / INST-E5.1)', () => {
  const cobertura = { instalacoes_br: 2, com_ptt: 2, com_carrier: 2, ptts_ixbr: 40, ptts_ixbr_com_instalacao: 37, ptts_ixbr_sem_instalacao: ['ac', 'the'], ptts_externos: 5, ptts_externos_com_instalacao: 4, asns_br_no_peeringdb: 10, asns_br_com_instalacao: 4,
    cadastro_br: { recente: 1 }, ptts_ixbr_nomes: { ac: 'Rio Branco', the: 'Teresina', rao: 'Ribeirão Preto', sp: 'São Paulo', ce: 'Fortaleza' }, ptts_ixbr_site: 40, ptts_ixbr_sem_mapeamento: ['rao'], ptts_ixbr_fora_do_site: [] }
  const sp4 = { ...f1, ptts_detalhe: [{ ix_id: 1, code: 'sp', tipo: 'ixbr' as const }, { ix_id: 2, code: 'decix-sp', tipo: 'externo' as const }, { ix_id: 3, code: 'equinix-sp', tipo: 'externo' as const }, { ix_id: 4, code: 'netix', tipo: 'externo' as const }, { ix_id: 3476, tipo: 'outro' as const }, { ix_id: 3478, tipo: 'outro' as const }], n_ptts: 6 }
  const so_outro = { ...f2, ptts_detalhe: [{ ix_id: 2784, tipo: 'outro' as const }], n_ptts: 1 }
  const corpo: FacilitiesLista = { ...meta, escopo: { pais: 'BR' }, ordem: 'x', total: 2, items: [sp4, so_outro], cobertura }

  it('a cobertura é nomeada: quem não tem instalação e quem o mapeamento não alcança, sem adjetivo', async () => {
    server.use(http.get('*/api/v1/facilities', () => HttpResponse.json(corpo)))
    montar(<FacilitiesPage />, '/instalacoes')
    const c = await screen.findByTestId('cobertura-ptts')
    expect(c.textContent).toContain('37 de 40 aparecem em alguma instalação do PeeringDB')
    expect(c.textContent).toContain('Sem instalação cadastrada no PeeringDB nesta coleta: Rio Branco (AC), Teresina (THE).')
    expect(c.textContent).toContain('Sem registro do PTT no PeeringDB ligado ao site: Ribeirão Preto (RAO).')
    expect(c.textContent).not.toMatch(/falha|problema|ausente/i)
  })

  it('a coluna PTTs mostra IX.br primeiro, até 3 códigos e "+n outros" com o texto acessível; só PTT não acompanhado vira "+1 outro"', async () => {
    server.use(http.get('*/api/v1/facilities', () => HttpResponse.json(corpo)))
    montar(<FacilitiesPage />, '/instalacoes')
    await screen.findByText('Datacenter Exemplo SP-1')
    const linha = screen.getByText('Datacenter Exemplo SP-1').closest('tr')!
    const celula = linha.querySelectorAll('td')[4]
    expect(Array.from(celula.querySelectorAll('a')).map((a) => a.textContent)).toEqual(['São Paulo (SP)', 'DECIX-SP', 'EQUINIX-SP'])
    expect(celula.querySelector('a')!.getAttribute('href')).toBe('/ixp/sp')
    expect(celula.querySelectorAll('a')[1].getAttribute('href')).toBe('/ixp-externo/decix-sp')
    expect(celula.textContent).toContain('+3 outros')
    expect(celula.textContent).toContain('3 PTTs a mais, 2 do PeeringDB que o site não acompanha')
    const so = screen.getByText('Colo <b>Exemplo</b> RJ').closest('tr')!.querySelectorAll('td')[4]
    expect(so.querySelectorAll('a')).toHaveLength(0)
    expect(so.textContent).toContain('+1 outro')
  })

  it('os filtros de PTT e carrier vão para a API e para a URL', async () => {
    const chamadas: URLSearchParams[] = []
    server.use(http.get('*/api/v1/facilities', ({ request }) => { chamadas.push(new URL(request.url).searchParams); return HttpResponse.json(corpo) }))
    montar(<FacilitiesPage />, '/instalacoes?ptt=sp&carrier=1&uf=SP')
    await screen.findByText('Datacenter Exemplo SP-1')
    expect(chamadas[0].get('ptt')).toBe('sp')
    expect(chamadas[0].get('com_carrier')).toBe('true')
    expect(chamadas[0].get('uf')).toBe('SP')
    expect((screen.getByRole('combobox', { name: /PTT do IX\.br/ }) as HTMLSelectElement).value).toBe('sp')
    expect(screen.getByRole('checkbox', { name: /só com carrier/ })).toBeChecked()
    fireEvent.change(screen.getByRole('combobox', { name: /PTT do IX\.br/ }), { target: { value: 'ce' } })
    await waitFor(() => expect(chamadas.some((c) => c.get('ptt') === 'ce')).toBe(true))
  })
})
