// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { server } from '../test/server'
import { useAppStore } from '../store/app'
import { OperadorasPage, RedirecionaServico } from './OperadorasPage'
import { DICAS_COLUNA, ORDEM_SERVICOS, SERVICOS, servicoDe } from '../features/operadoras/servicos'

// jsdom não tem WebGL: os mapas são testados no E2E
vi.mock('../features/operadoras/MapaSede', () => ({ MapaSede: () => <div data-testid="mapa-sede" /> }))
vi.mock('../features/operadoras/MapaAcessos', () => ({ MapaAcessos: () => <div data-testid="mapa-acessos" /> }))

const stats = { snapshot_date: '2026-09-20', total: 1234, unique_cnpjs: 1000, geolocated: 900, cnpjs_with_asn: 800 }
const linha = {
  cnpj: '90000000000180', razao_social: 'Prov Ltda', nome_fantasia: 'Prov', municipio: 'Vitória', uf: 'ES', data_outorga: '01/01/2020',
  data_outorga_por_servico: { SCM: '01/01/2020', STFC: '02/02/2021' }, servicos: ['SCM', 'STFC'], outorgas: 2, asns: [65551],
  ativo: true, acessos: 5000, acessos_fixo: 5000, acessos_movel: 0, pj_fixo: 100, pj_movel: 0, municipios_fixo: 3, municipios_movel: 0, tecnologia_fixo: 'FTTH', porte: 'Pequeno Porte',
}
const pagina = (items: unknown[]) => ({ items, total: items.length, page: 1, pages: 1, limit: 50 })
const vistos: string[] = []

beforeEach(() => {
  vistos.length = 0
  useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' })
  server.use(
    http.get('*/api/v1/outorgas/stats', () => HttpResponse.json(stats)),
    http.get('*/api/v1/outorgas', ({ request }) => {
      const url = new URL(request.url)
      vistos.push('outorgas ' + url.search)
      const sv = url.searchParams.get('servico')
      if (sv === 'STFC') return HttpResponse.json(pagina([{ ...linha, razao_social: 'Tel Ltda', nome_fantasia: '', uf: 'MG', municipio: 'BH', servicos: ['STFC'], acessos_fixo: 0 }]))
      return HttpResponse.json(pagina([linha]))
    }),
    http.get('*/api/v1/acessos/operadoras', ({ request }) => { vistos.push('moveis ' + new URL(request.url).search); return HttpResponse.json(pagina([{ cnpj: '90001001000143', empresa: 'Escala', uf_sede: 'RJ', ativo: true, acessos: 15000, acessos_pj: 0, municipios: 2, asns: [] }])) }),
  )
})

function montar(inicial: string) {
  const Local = () => <div data-testid="onde">{useLocation().pathname + useLocation().search}</div>
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[inicial]}>
        <Local />
        <Routes>
          <Route path="/operadoras" element={<OperadorasPage />} />
          <Route path="/scms" element={<RedirecionaServico servico="scm" />} />
          <Route path="/stfcs" element={<RedirecionaServico servico="stfc" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('configuração dos serviços', () => {
  it('quatro serviços e a aba que os combina, na ordem das abas; padrões das páginas antigas', () => {
    expect(ORDEM_SERVICOS).toEqual(['scm', 'smp', 'stfc', 'seac', 'todas'])
    expect(SERVICOS.scm.ordenacaoPadrao).toEqual({ campo: 'acessos_fixo', desc: true })
    expect(SERVICOS.scm.soAtivosPadrao).toBe(false)
    expect(SERVICOS.smp.soAtivosPadrao).toBe(true)
    expect(SERVICOS.smp.ordenacaoPadrao).toEqual({ campo: 'acessos', desc: true })
    expect(SERVICOS.stfc.temSici).toBe(false)
    expect(SERVICOS.seac.ordenacaoPadrao).toEqual({ campo: 'razao_social', desc: false })
  })

  it('serviço desconhecido ou ausente cai em SCM', () => {
    expect(servicoDe(null).id).toBe('scm')
    expect(servicoDe('xyz').id).toBe('scm')
    expect(servicoDe('SMP').id).toBe('smp')
  })

  it('colunas: as mesmas das páginas antigas', () => {
    expect(SERVICOS.scm.colunas.map((c) => c.label)).toEqual(['CNPJ', 'Razão Social / Nome Fantasia', 'Município / UF', 'Data no cadastro', 'Acessos', 'B2B', 'Munic.', 'ASN(s)'])
    expect(SERVICOS.smp.colunas.map((c) => c.label)).toEqual(['Operadora', 'UF sede', 'Acessos', 'B2B', 'Munic.', 'Geração', 'ASN(s)', 'Rede virtual'])
    expect(SERVICOS.stfc.colunas.map((c) => c.label)).toEqual(['Prestadora', 'UF', 'Município', 'Data no cadastro', 'ASN(s)'])
    expect(SERVICOS.smp.colunas.filter((c) => !c.ordenavel).map((c) => c.key)).toEqual(['geracao', 'asns', 'rede_virtual'])
  })

  it('a data da coluna é a do cadastro da Anatel, não a da outorga original', () => {
    expect(DICAS_COLUNA.data_outorga).toMatch(/cadastro de outorgas da Anatel/)
    expect(DICAS_COLUNA.data_outorga).not.toMatch(/^Data da outorga/)
  })
})

describe('página /operadoras', () => {
  it('sem parâmetro mostra SCM, com estatísticas, tabela e o contador de resultados', async () => {
    montar('/operadoras')
    expect(await screen.findByRole('heading', { level: 1, name: 'Outorgas SCM' })).toBeInTheDocument()
    expect(await screen.findByText('1.234')).toBeInTheDocument()
    expect(await screen.findByText('Prov')).toBeInTheDocument()
    expect(vistos.some((v) => v.includes('servico=SCM'))).toBe(true)      // contrato unificado, não /scms
    expect(screen.getByText('1 resultado')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'SCM' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByTestId('mapa-acessos')).toBeInTheDocument()   // SCM abre na aba de acessos (SICI)
  })

  it('alternância Sede/Acessos com aria-pressed e explicação do filtro fora do title (OPERADORA-E4, OPERADORA-E5)', async () => {
    montar('/operadoras?servico=scm')
    await screen.findByText('Prov')
    const camada = screen.getByRole('group', { name: 'Camada do mapa' })
    const sede = within(camada).getByRole('button', { name: 'Sede' })
    const acessos = within(camada).getByRole('button', { name: 'Acessos (SICI)' })
    expect(acessos).toHaveAttribute('aria-pressed', 'true')
    expect(sede).toHaveAttribute('aria-pressed', 'false')
    fireEvent.click(sede)
    expect(sede).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByTestId('mapa-sede')).toBeInTheDocument()
    expect(screen.getByLabelText('Apenas em operação').closest('label')).not.toHaveAttribute('title')
    expect(screen.getByRole('button', { name: 'Sobre: Apenas em operação' })).toBeInTheDocument()
    // o mapa de acessos é MapLibre (sem jsdom): o "×" do painel precisa de nome acessível
    expect(readFileSync(resolve(__dirname, '../features/operadoras/MapaAcessos.tsx'), 'utf-8')).toMatch(/<button type="button" aria-label="Fechar painel"/)
  })

  it('?servico=stfc mostra a lista de STFC, sem filtro de operação e só com o mapa de sede', async () => {
    montar('/operadoras?servico=stfc')
    expect(await screen.findByRole('heading', { level: 1, name: 'Outorgas STFC' })).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Tel Ltda' })).toBeInTheDocument()
    expect(screen.queryByLabelText('Apenas em operação')).toBeNull()
    expect(screen.getByTestId('mapa-sede')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'STFC' })).toHaveAttribute('aria-selected', 'true')
  })

  it('clicar na aba troca o serviço (e a URL)', async () => {
    montar('/operadoras?servico=scm')
    await screen.findByText('Prov')
    fireEvent.click(screen.getByRole('tab', { name: 'SMP' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Operadoras SMP' })).toBeInTheDocument()
    expect(screen.getByTestId('onde')).toHaveTextContent('/operadoras?servico=smp')
    expect(await screen.findByText('Escala')).toBeInTheDocument()
    expect(screen.getByLabelText('Apenas em operação')).toBeChecked()   // SMP abre só com quem opera
  })

  it('filtros vão para a URL e para a chamada à API; valor padrão sai da URL', async () => {
    montar('/operadoras?servico=scm')
    await screen.findByText('Prov')
    fireEvent.change(screen.getByLabelText('UF'), { target: { value: 'ES' } })
    await waitFor(() => expect(screen.getByTestId('onde')).toHaveTextContent('uf=ES'))
    await waitFor(() => expect(vistos.some((v) => v.includes('uf=ES'))).toBe(true))
    fireEvent.click(screen.getByLabelText('Apenas com AS identificado'))
    await waitFor(() => expect(screen.getByTestId('onde')).toHaveTextContent('com_asn=1'))
    fireEvent.click(screen.getByLabelText('Apenas em operação'))      // SCM começa desmarcado → marcar grava ativo=1
    await waitFor(() => expect(screen.getByTestId('onde')).toHaveTextContent('ativo=1'))
    fireEvent.click(screen.getByLabelText('Apenas em operação'))      // voltar ao padrão tira da URL
    await waitFor(() => expect(screen.getByTestId('onde')).not.toHaveTextContent('ativo'))
  })

  it('rotas antigas redirecionam para a aba certa preservando a query', async () => {
    montar('/scms?q=prov&uf=ES')
    await waitFor(() => expect(screen.getByTestId('onde').textContent).toMatch(/^\/operadoras\?/))
    const onde = screen.getByTestId('onde').textContent!
    expect(onde).toContain('servico=scm')
    expect(onde).toContain('q=prov')
    expect(onde).toContain('uf=ES')
  })

  it('/stfcs redireciona para servico=stfc', async () => {
    montar('/stfcs')
    await waitFor(() => expect(screen.getByTestId('onde')).toHaveTextContent('/operadoras?servico=stfc'))
    expect(await screen.findByRole('heading', { level: 1, name: 'Outorgas STFC' })).toBeInTheDocument()
    expect(within(screen.getByRole('tablist')).getAllByRole('tab')).toHaveLength(5)
  })
})

describe('aba "Combinar serviços"', () => {
  it('serviços marcados vão juntos à API; "Ter todos" só aparece com 2 ou mais; porte e linha com os serviços do CNPJ', async () => {
    montar('/operadoras?servico=todas')
    expect(await screen.findByRole('heading', { level: 1, name: 'Outorgas por serviço, combinadas' })).toBeInTheDocument()
    expect(await screen.findByText('Prov')).toBeInTheDocument()
    expect(screen.queryByTestId('mapa-sede')).toBeNull()                  // sem mapa nem totais nesta aba
    expect(screen.getByText('STFC', { selector: 'span' })).toBeInTheDocument()   // badge dos serviços do CNPJ
    expect(screen.queryByLabelText('Ter todos')).toBeNull()
    fireEvent.click(screen.getByLabelText('SCM'))
    fireEvent.click(screen.getByLabelText('SMP'))
    await waitFor(() => expect(screen.getByTestId('onde')).toHaveTextContent('servicos=SCM%2CSMP'))
    fireEvent.click(await screen.findByLabelText('Ter todos'))
    fireEvent.change(screen.getByLabelText('Porte'), { target: { value: 'Grande Porte' } })
    await waitFor(() => expect(vistos.some((v) => v.includes('servico=SCM%2CSMP') && v.includes('todos=true') && v.includes('porte=Grande+Porte'))).toBe(true))
  })
})
