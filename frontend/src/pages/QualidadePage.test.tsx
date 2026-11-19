// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../test/server'
import { QualidadePage } from './QualidadePage'
import { QualidadeMunicipioBloco, QualidadeOperadoraBloco, ReclamacoesMunicipioBloco, ReclamacoesOperadoraBloco } from '../features/qualidade/blocos'
import type { QualIndicador, QualidadeOperadora, ReclamacoesMunicipio, ReclamacoesOperadora } from '../types/api'

vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ anon: null, loading: false }) }))

const meta = { natureza: 'medido_ou_apurado', fonte: 'Anatel', data_arquivo: 'Fri, 06 Nov 2026 11:04:10 GMT', limites: 'Cobre só as grandes prestadoras.', snapshot_date: '2026-11-05' }
const ind4: QualIndicador = { servico: 'Banda Larga Fixa', codigo: 'IND4', descricao: 'Cumprimento de velocidade', tipo: 'Indicador IQS', grupo: 'Redes', unidade: '%', referencia_superior: '90%', referencia_inferior: '60%' }
const resumo = {
  ...meta, leitura: { linhas: 100, resultados_numericos: 80, sem_valor: { NA: 20 }, municipios: 3, municipios_com_resultado: 3, mes_inicial: '2022-03', mes_final: '2026-09', itens_municipais: 10 },
  indicadores: [ind4], prestadoras: [
    { servico: 'Banda Larga Fixa', prestadora: 'ALFA', municipios: 2, raizes: ['11111111'], cnpjs_matriz: ['11111111000111'], casamento: 'curada', base_casamento: 'x' },
    { servico: 'Banda Larga Fixa', prestadora: 'BETA', municipios: 1, raizes: [], casamento: null, base_casamento: null }],
  casamento: { prestadoras: 2, com_cnpj: 1, pct_resultados_com_cnpj: 50, sem_cnpj: ['BETA (Banda Larga Fixa)'], tabela_curada: { versao: 1, curada_em: '2026-11-06', fonte: 'x' } },
}
const estat = { municipios: 2, resultados: 2, medidas: 520, media: 70, media_ponderada: 75.38, mediana: 70 }
const montar = (rota: string) => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[rota]}><QualidadePage /></MemoryRouter></QueryClientProvider>,
)

describe('Qualidade', () => {
  it('aba Indicadores: prestadoras em ordem alfabética, referência da Anatel, link ao CNPJ e aviso de que não há ranking', async () => {
    let pedido: URLSearchParams | null = null
    server.use(
      http.get('*/api/v1/qualidade/resumo', () => HttpResponse.json(resumo)),
      http.get('*/api/v1/qualidade/prestadoras', ({ request }) => {
        pedido = new URL(request.url).searchParams
        return HttpResponse.json({ ...meta, indicador: ind4, uf: pedido.get('uf'), periodo: { mes: '2026-08' }, ordem: 'prestadora (alfabética; sem ranking)', total: 2,
          items: [{ servico: 'Banda Larga Fixa', prestadora: 'ALFA', indicador: 'IND4', mes: '2026-08', ...estat, raizes_cnpj: ['11111111'] }, { servico: 'Banda Larga Fixa', prestadora: 'BETA', indicador: 'IND4', mes: '2026-08', ...estat, media_ponderada: null, raizes_cnpj: [] }] })
      }),
      http.get('*/api/v1/qualidade/serie', () => HttpResponse.json({ ...meta, indicador: ind4, uf: null, granularidade: 'mensal nacional', total: 1, items: [{ servico: 'Banda Larga Fixa', prestadora: 'ALFA', indicador: 'IND4', mes: '2026-08', ...estat }] })),
    )
    montar('/qualidade')
    await waitFor(() => expect(screen.getByText('11111111').getAttribute('href')).toBe('/operadora/11111111000111'))
    expect(screen.getByText(/Sem ranking: as prestadoras aparecem em ordem alfabética/)).toBeTruthy()
    expect(screen.getByText(/referência da Anatel \(superior \/ inferior\): 90% \/ 60%/)).toBeTruthy()
    expect(screen.getByText('sem CNPJ ligado')).toBeTruthy()
    expect(screen.getByText(/Prestadoras sem CNPJ ligado/).textContent).toContain('BETA')
    expect(pedido!.get('servico')).toBe('Banda Larga Fixa')
    fireEvent.change(screen.getAllByRole('combobox')[2], { target: { value: 'SP' } })
    await waitFor(() => expect(pedido!.get('uf')).toBe('SP'))
  })

  it('aba Reclamações: cobertura do CNPJ, lista alfabética, taxa só onde calculada e filtro por serviço', async () => {
    let servico: string | null = 'x'
    const taxa = (por: number | null) => ({ marca: 'ALFA', grupo: 'SCM', raizes: ['11111111'], casamento: 'curada', reclamacoes: 120, acessos: 6000, por_mil_acessos: por, motivo_sem_taxa: por == null ? 'sem acessos' : null })
    server.use(
      http.get('*/api/v1/reclamacoes/resumo', () => HttpResponse.json({
        ...meta, natureza: 'declarado_por_consumidores', limites: 'Reclamação não é prova de falha.',
        leitura: { arquivos: { 'reclamacoes_contexto.csv': { linhas: 1, linhas_usadas: 1, solicitacoes: 1, mes_inicial: '2020-01', mes_final: '2026-09' } }, corte_contexto: '2020-01', anos: [2025, 2026], marcas: 3, municipios: 2, reclamacoes: 1000, sem_marca: 10 },
        casamento: { reclamacoes_total: 1000, por_metodo: { curada: 900 }, pct_com_cnpj: 90, marcas: 3, marcas_com_cnpj: 1, tabela_curada: { versao: 1, curada_em: '2026-11-06', fonte: 'x', marcas: 28 } },
        taxas: { janela: { de: '2025-10', ate: '2026-09' }, sici_mes_referencia: { SCM: '2026-08', SMP: '2026-08' }, regra: 'reclamações ÷ acessos × 1.000' },
        por_ano_servico: [{ ano: 2026, servico: 'SCM', reclamacoes: 600 }, { ano: 2025, servico: 'SCM', reclamacoes: 400 }], assuntos_ano: { ano: 2026, itens: [{ servico: 'SCM', assunto: 'Cobrança', reclamacoes: 300 }] }, uf: [] })),
      http.get('*/api/v1/reclamacoes/marcas', ({ request }) => {
        servico = new URL(request.url).searchParams.get('servico')
        return HttpResponse.json({ ...meta, ano: 2026, servico, ordem: 'marca (alfabética; sem ranking)', total: 2, limit: 25, offset: 0, items: [
          { marca: 'ALFA', ano: 2026, reclamacoes: 120, por_servico: { SCM: 120 }, raizes: ['11111111'], cnpjs_matriz: ['11111111000111'], casamento: 'curada', taxas: [taxa(20)] },
          { marca: 'SEM DONO', ano: 2026, reclamacoes: 5, por_servico: { SCM: 5 }, raizes: [], cnpjs_matriz: [], casamento: null, taxas: [] }] })
      }),
    )
    montar('/qualidade?aba=reclamacoes')
    await waitFor(() => expect(screen.getByText('ALFA')).toBeTruthy())
    expect(screen.getByText(/90,0% das reclamações com CNPJ ligado/)).toBeTruthy()
    expect(screen.getByText('11111111').getAttribute('href')).toBe('/operadora/11111111000111')
    expect(screen.getByText('sem CNPJ ligado')).toBeTruthy()
    expect(screen.getByText(/SCM 20,00/)).toBeTruthy()
    expect(screen.getAllByText(/ordem alfabética|alfabética/).length).toBeGreaterThan(0)
    expect(screen.getByText(/Só agregados da própria Anatel: nenhum texto livre nem dado de quem reclamou/)).toBeTruthy()
    fireEvent.change(screen.getAllByRole('combobox')[0], { target: { value: 'SCM' } })
    await waitFor(() => expect(servico).toBe('SCM'))
  })
})

describe('Blocos de qualidade e reclamações', () => {
  const bloco: QualidadeOperadora = {
    ...meta, raiz: '11111111', indicadores: [ind4], prestadoras: [{ servico: 'Banda Larga Fixa', prestadora: 'ALFA', municipios: 2, raizes: ['11111111'], casamento: 'curada', base_casamento: 'x' }],
    itens: [{ servico: 'Banda Larga Fixa', prestadora: 'ALFA', indicador: 'IND4', mes: '2026-08', ...estat }],
  }
  it('operadora: mostra a média ponderada, a referência da Anatel e a ressalva de que é valor nacional da prestadora', () => {
    render(<MemoryRouter><QualidadeOperadoraBloco dados={{ qualidade: bloco } as never} snapshot="2026-11-05" /></MemoryRouter>)
    expect(screen.getByText(/ligação ao CNPJ: curada/)).toBeTruthy()
    expect(screen.getByText('75,38 %')).toBeTruthy()
    expect(screen.getByText('90% / 60%')).toBeTruthy()
    expect(screen.getByText(/não do CNPJ isolado/)).toBeTruthy()
  })

  it('município: resultado com erro amostral e intervalo', () => {
    const q = { ...meta, ibge: '1', nome: 'Alfa', uf: 'RO', indicadores: [ind4], prestadoras: [{ servico: 'Banda Larga Fixa', prestadora: 'ALFA', itens: [{ indicador: 'IND4', mes: '2026-08', resultado: 85, medidas: 400, coletores: 50, erro_amostral: 4, estatistica: true, limite_inferior: 81, limite_superior: 89 }] }] }
    render(<MemoryRouter><QualidadeMunicipioBloco dados={{ qualidade: q } as never} snapshot="2026-11-05" /></MemoryRouter>)
    expect(screen.getByText('85,00 %')).toBeTruthy()
    expect(screen.getByTitle(/intervalo 81,0 a 89,0/)).toBeTruthy()   // o detalhe vai no title da célula (quadro resumido)
    expect(screen.getByTitle(/erro amostral 4,00/)).toBeTruthy()
  })

  it('operadora: reclamações com marcas ligadas, taxa calculada e taxa não calculada com o motivo', () => {
    const r: ReclamacoesOperadora = {
      ...meta, natureza: 'declarado_por_consumidores', raiz: '11111111', marcas: [{ marca: 'ALFA', casamento: 'curada' }], anos: [{ ano: 2025, reclamacoes: 400, por_servico: { SCM: 400 } }, { ano: 2026, reclamacoes: 600, por_servico: { SCM: 500, SMP_Pós: 100 } }],
      assuntos_ano: { ano: 2026, itens: [{ servico: 'SCM', assunto: 'Cobrança', reclamacoes: 300 }] },
      taxas: { janela: { de: '2025-10', ate: '2026-09' }, sici_mes_referencia: { SCM: '2026-08', SMP: '2026-08' }, regra: 'regra x', itens: [
        { marca: 'ALFA', grupo: 'SCM', raizes: ['11111111'], casamento: 'curada', reclamacoes: 120, acessos: 6000, por_mil_acessos: 20, motivo_sem_taxa: null },
        { marca: 'ALFA', grupo: 'SMP', raizes: ['11111111'], casamento: 'curada', reclamacoes: 40, acessos: null, por_mil_acessos: null, motivo_sem_taxa: 'sem acessos' }] },
      aviso: 'A marca pode agrupar mais de um CNPJ.',
    }
    render(<MemoryRouter><ReclamacoesOperadoraBloco dados={{ reclamacoes: r } as never} snapshot="2026-11-05" /></MemoryRouter>)
    expect(screen.getByText(/Marcas ligadas a este CNPJ: ALFA \(curada\)/)).toBeTruthy()
    expect(screen.getByText('20,00')).toBeTruthy()
    expect(screen.getByText('não calculado').getAttribute('title')).toBe('sem acessos')
  })

  it('município: reclamações por ano e por 100 mil habitantes; marcas em ordem alfabética', () => {
    const r: ReclamacoesMunicipio = {
      ...meta, natureza: 'declarado_por_consumidores', ibge: '1', nome: 'Alfa', uf: 'RO', populacao: 100000,
      anos: [{ ano: 2026, reclamacoes: 50, por_100mil_hab: 50, por_servico: { SCM: 50 }, marcas: [{ marca: 'ZETA', servico: 'SCM', reclamacoes: 40, raizes: [] }, { marca: 'ALFA', servico: 'SCM', reclamacoes: 10, raizes: [] }] }],
    }
    const { container } = render(<MemoryRouter><ReclamacoesMunicipioBloco dados={{ reclamacoes: r } as never} snapshot="2026-11-05" /></MemoryRouter>)
    expect(screen.getByText('50,0')).toBeTruthy()
    const itens = [...container.querySelectorAll('li')].map((li) => li.textContent ?? '')
    expect(itens[0]).toContain('ALFA')
    expect(itens[1]).toContain('ZETA')
  })
})
