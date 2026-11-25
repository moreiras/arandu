// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { server } from '../../test/server'
import { useAppStore } from '../../store/app'
import { Ipv6Apnic } from './IndicadoresBrasil'
import { RpkiPublicacao } from './AbaSeguranca'
import { VisibilidadeGlobal } from './AbaFamilia'
import { ABA_GRUPOS_MOVIDA, ABAS_MERCADO, PanoramaMercado } from '../../pages/PanoramaMercado'
import { ABAS_TECNICO, ALIASES_TECNICO } from '../../pages/PanoramaTecnico'
import { AliasPanorama } from './AliasPanorama'
import { ALIAS, DESTINOS, PAGINAS_DE_DETALHE } from './destinos'
import { PaginaPanorama } from './PaginaPanorama'

const ids = (abas: { id: string }[]) => abas.map((a) => a.id)
const PANORAMAS: Record<string, string[]> = {
  '/panorama/tecnico': ABAS_TECNICO.map((a) => a.id), '/panorama/mercado': ABAS_MERCADO.map((a) => a.id),
}

describe('onde foi parar cada bloco das páginas dissolvidas', () => {
  it('a lista conferida: 5 blocos da Visão geral e 10 de Estatísticas, todos com lugar novo', () => {
    expect(DESTINOS.filter((d) => d.de === 'visao-geral')).toHaveLength(5)
    expect(DESTINOS.filter((d) => d.de === 'estatisticas')).toHaveLength(10)
    expect(new Set(DESTINOS.map((d) => d.bloco)).size).toBe(DESTINOS.length)
  })
  it('todo destino é um panorama que existe e, quando traz ?aba=, uma aba que existe', () => {
    for (const d of DESTINOS) {
      const [caminho, consulta] = d.para.split('?')
      if (PAGINAS_DE_DETALHE.includes(caminho)) continue
      expect(Object.keys(PANORAMAS), d.bloco).toContain(caminho)
      const aba = new URLSearchParams(consulta ?? '').get('aba')
      if (aba) expect(PANORAMAS[caminho], `${d.bloco} → ${d.para}`).toContain(aba)
    }
    for (const alvo of Object.values(ALIAS)) expect(Object.keys(PANORAMAS)).toContain(alvo)
  })
  it('IPv6 vem antes de IPv4 no Panorama técnico e o Panorama de IPv6 virou a aba ipv6', () => {
    const ids = ABAS_TECNICO.map((a) => a.id)
    expect(ids.indexOf('ipv6')).toBeGreaterThan(-1)
    expect(ids.indexOf('ipv6')).toBeLessThan(ids.indexOf('ipv4'))
    expect(ids).toEqual(['resumo', 'ipv6', 'ipv4', 'interconexao', 'seguranca'])
  })
  it('as abas retiradas em 2026-11-17 seguem respondendo como alias de uma aba que existe', () => {
    for (const [antiga, nova] of Object.entries(ALIASES_TECNICO)) {
      expect(ids(ABAS_TECNICO), antiga).not.toContain(antiga)
      expect(ids(ABAS_TECNICO), `${antiga} → ${nova}`).toContain(nova)
    }
    expect(Object.keys(ALIASES_TECNICO).sort()).toEqual(['dnssec', 'ixbr', 'mapa', 'prontidao'])
  })
  it('toda aba de panorama tem rótulo e descrição, e ninguém repete id dentro do panorama', () => {
    for (const abas of [ABAS_TECNICO, ABAS_MERCADO]) {
      expect(new Set(abas.map((a) => a.id)).size).toBe(abas.length)
      for (const a of abas) { expect(a.rotulo).not.toBe(''); expect(a.descricao.length).toBeGreaterThan(20) }
    }
  })
})

describe('alias das páginas dissolvidas', () => {
  const Onde = () => { const l = useLocation(); return <div data-testid="onde">{l.pathname}{l.search}</div> }
  const montar = (rota: string) => render(
    <MemoryRouter initialEntries={[rota]}>
      <Routes>
        <Route path="/visao-geral" element={<AliasPanorama de="visao-geral" antiga={<p>página antiga</p>} />} />
        <Route path="/estatisticas" element={<AliasPanorama de="estatisticas" antiga={<p>estatísticas antigas</p>} />} />
        <Route path="*" element={<Onde />} />
      </Routes>
    </MemoryRouter>,
  )
  it('redireciona para o panorama técnico', () => {
    montar('/visao-geral')
    expect(screen.getByTestId('onde')).toHaveTextContent('/panorama/tecnico')
    montar('/estatisticas')
    expect(screen.getAllByTestId('onde')[screen.getAllByTestId('onde').length - 1]).toHaveTextContent('/panorama/tecnico')
  })
  it('?versao=1 mostra a página como era', () => {
    montar('/visao-geral?versao=1')
    expect(screen.getByText('página antiga')).toBeInTheDocument()
  })
})

describe('PaginaPanorama', () => {
  const montar = (rota: string) => {
    const Um = () => <p>conteúdo um</p>; const Dois = () => <p>conteúdo dois</p>
    return render(
      <MemoryRouter initialEntries={[rota]}>
        <PaginaPanorama titulo="Panorama X" descricao="Descrição do panorama X."
          abas={[{ id: 'um', rotulo: 'Um', descricao: 'Primeira lente do panorama.', Conteudo: Um }, { id: 'dois', rotulo: 'Dois', descricao: 'Segunda lente do panorama.', Conteudo: Dois }]} />
      </MemoryRouter>,
    )
  }
  it('mostra a primeira aba e só monta o conteúdo da aba aberta', () => {
    montar('/p')
    expect(screen.getByRole('heading', { level: 1, name: 'Panorama X' })).toBeInTheDocument()
    expect(screen.getByText('conteúdo um')).toBeInTheDocument()
    expect(screen.queryByText('conteúdo dois')).toBeNull()
  })
  it('?aba= de uma aba retirada abre a nova e reescreve a URL', async () => {
    const Um = () => <p>conteúdo um</p>; const Dois = () => <p>conteúdo dois</p>
    const Onde = () => { const l = useLocation(); return <div data-testid="onde">{l.search}</div> }
    render(
      <MemoryRouter initialEntries={['/p?aba=velha']}>
        <PaginaPanorama titulo="Panorama X" descricao="Descrição do panorama X." aliases={{ velha: 'dois' }}
          abas={[{ id: 'um', rotulo: 'Um', descricao: 'Primeira lente do panorama.', Conteudo: Um }, { id: 'dois', rotulo: 'Dois', descricao: 'Segunda lente do panorama.', Conteudo: Dois }]} />
        <Onde />
      </MemoryRouter>,
    )
    expect(screen.getByText('conteúdo dois')).toBeInTheDocument()
    expect(await screen.findByTestId('onde')).toHaveTextContent('?aba=dois')
  })
  it('?aba= escolhe a lente e o clique troca', () => {
    montar('/p?aba=dois')
    expect(screen.getByText('conteúdo dois')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: 'Um' }))
    expect(screen.getByText('conteúdo um')).toBeInTheDocument()
  })
})

describe('aba IPv6 do Panorama técnico', () => {
  beforeEach(() => {
    useAppStore.setState({ activeDate: '2026-09-20', latestSnapshot: '2026-09-20' })
    server.use(
      http.get('*/api/v1/brasil/snapshots/:date', () => HttpResponse.json({ date: '2026-09-20', manifest: null,
        summary: { snapshot_date: '2026-09-20', total_asns_br: 1136, br_ipv6_pct: 97.1, br_asns_ft_v6: 763, registro_br_prefixes_v6: 776,
          global_table: { br_asns_in_ft: 1000, v6_br_coverage_pct: 88.6 }, ixp_aggregate: { v6_br_coverage_pct: 51.5 } } })),
    )
  })
  it('anúncio de IPv6 vem da tabela global, não do campo que inclui IPv6 só alocado', async () => {
    const { container } = render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><VisibilidadeGlobal f="v6" /></MemoryRouter></QueryClientProvider>)
    expect(await screen.findByText('763')).toBeInTheDocument()
    expect(container).toHaveTextContent('76,3% dos 1.000 visíveis')
    expect(container).toHaveTextContent('88,6%')
    expect(container).not.toHaveTextContent('97,1%')
  })
})

describe('selo, fonte e data visíveis nos KPIs do panorama (PT-14)', () => {
  const ARQUIVOS = ['AbaFamilia', 'AbaInterconexao', 'AbaSeguranca', 'IndicadoresBrasil', 'ResumoTecnico']
  it('toda chamada de Kpi dos cinco arquivos do panorama declara selo (66 chamadas)', () => {
    let total = 0
    const fontes = import.meta.glob('./{AbaFamilia,AbaInterconexao,AbaSeguranca,IndicadoresBrasil,ResumoTecnico}.tsx', { query: '?raw', import: 'default', eager: true }) as Record<string, string>
    for (const a of ARQUIVOS) {
      const fonte = fontes[`./${a}.tsx`]
      expect(fonte, a).toBeTruthy()
      const chamadas = fonte.match(/<Kpi\s[^>]*?rotulo=/g) ?? []
      total += chamadas.length
      for (const c of chamadas) expect(c, `${a}: ${c}`).toMatch(/selo=/)
      expect((fonte.match(/<Kpi[\s>]/g) ?? []).length, a).toBe(chamadas.length)
    }
    expect(total).toBe(66)
  })
  beforeEach(() => {
    useAppStore.setState({ activeDate: '2026-09-20', latestSnapshot: '2026-09-20' })
    server.use(
      http.get('*/api/v1/brasil/indicadores', () => HttpResponse.json({ snapshot_date: '2026-09-20',
        ipv6: { usuarios: 1000, usuarios_ipv6: 412, pct_usuarios_ipv6: 41.2, asns_com_estimativa: 10, asns_com_ipv6: 7, fonte: 'APNIC', nota: '' },
        rpki: { publicacao: { br_asns_with_roa: 43, br_asns_with_aspa: 2, br_asns_total: 100, br_space_v6_roa_48: 5, br_space_v6_total_48: 10, br_space_v4_roa_24: 5, br_space_v4_total_24: 10 } } })),
    )
  })
  const montarComRotas = (ui: React.ReactElement) => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>)
  it('aba IPv6: usuários com IPv6 aparecem como Estimado, com fonte e data, em texto', async () => {
    montarComRotas(<Ipv6Apnic />)
    expect((await screen.findAllByText('Estimado · APNIC Labs · ref. 2026-09-20', { selector: 'p' })).length).toBeGreaterThan(0)
    for (const k of screen.getAllByTestId('kpi')) expect(k.querySelector('[data-kpi-selo]'), k.textContent ?? '').not.toBeNull()
  })
  it('segurança: ROA é Fato, com RPKI como fonte e a data do snapshot', async () => {
    montarComRotas(<RpkiPublicacao />)
    expect(await screen.findAllByText('Fato · RPKI (Routinator) · ref. 2026-09-20')).toHaveLength(2)
    expect(screen.getAllByText('Fato · RPKI e RouteViews · ref. 2026-09-20')).toHaveLength(2)
  })
})

describe('organizações com vários ASNs', () => {
  it('a antiga aba "Grupos econômicos" do Panorama de mercado leva a /ases e não é mais aba de mercado', () => {
    expect(ABAS_MERCADO.map((a) => a.id)).not.toContain('grupos')
    function Onde() { const l = useLocation(); return <p data-testid="onde">{l.pathname + l.search}</p> }
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={['/panorama/mercado?aba=grupos']}>
          <Routes>
            <Route path="/panorama/mercado" element={<PanoramaMercado />} />
            <Route path="/ases" element={<Onde />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(screen.getByTestId('onde')).toHaveTextContent(ABA_GRUPOS_MOVIDA)
    expect(ABA_GRUPOS_MOVIDA).toBe('/ases?secao=organizacoes')
  })
})
