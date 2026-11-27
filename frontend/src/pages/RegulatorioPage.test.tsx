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
import { server } from '../test/server'
import { RegulatorioPage } from './RegulatorioPage'
import { MultasOperadoraBloco } from '../features/regulatorio/blocos'
import type { MultasOperadora } from '../types/api'

vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ anon: null, loading: false }) }))

const meta = { natureza: 'cadastro_regulatorio', fonte: 'Anatel', data_arquivo: 'Mon, 02 Nov 2026 10:30:08 GMT', limites: 'Multa constituída não é condenação definitiva.', snapshot_date: '2026-11-02' }
// o gráfico anual usa o ResponsiveContainer do recharts, que mede o contêiner com ResizeObserver, que o jsdom não tem
beforeAll(() => { vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} }) })
const totais = { empresas: 2, multas: 5, original: 2000, pago: 500, saldo: 1500, situacoes: { Quitado: 3, Devedor: 2 } }
const multasResumo = { ...meta, leitura: { linhas: 50, pessoa_fisica: 10, fora_do_escopo: 20, sem_servico: 5, empresas: 2, multas: 5 }, brasil: totais, por_grupo: { SCM: totais, SMP: totais },
  por_ano: [{ ano: 2020, SCM: 1, SMP: 2, STFC: 0, SeAC: 0, total: 3 }] }
const empresa = { raiz: '11111111', cnpj_matriz: '11111111000111', entidade: 'PROVEDOR UM LTDA', grupo: 'SCM', uf: 'SP', multas: 3, original: 8000, pago: 1700, saldo: 9050, situacoes: { Quitado: 1, Devedor: 2 }, primeiro_ano: '2019', ultimo_ano: '2021' }
const montar = (rota: string) => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[rota]}><RegulatorioPage /></MemoryRouter></QueryClientProvider>,
)

describe('Regulatório', () => {
  it('aba Multas: totais, lista com link para a operadora e aviso de que não é condenação definitiva', async () => {
    let grupoPedido: string | null = 'x'
    let ordemPedida: string | null = 'x'
    server.use(
      http.get('*/api/v1/multas/resumo', () => HttpResponse.json(multasResumo)),
      http.get('*/api/v1/multas/empresas', ({ request }) => {
        grupoPedido = new URL(request.url).searchParams.get('grupo')
        ordemPedida = new URL(request.url).searchParams.get('ordem')
        return HttpResponse.json({ ...meta, grupo: grupoPedido, ordem: ordemPedida ?? 'empresa', regra_ordem: 'Ordem alfabética pelo nome da empresa e, em empate, pela raiz do CNPJ e pelo serviço (neutra).', aviso: 'Multa constituída não é condenação definitiva.', total: 1, limit: 20, offset: 0, items: [empresa] })
      }),
    )
    montar('/regulatorio?aba=multas')
    await waitFor(() => expect(screen.getByText('PROVEDOR UM LTDA').getAttribute('href')).toBe('/operadora/11111111000111'))
    expect(screen.getAllByText(/não é condenação definitiva/).length).toBeGreaterThan(0)
    expect(screen.getByText(/10 de pessoa física/)).toBeTruthy()
    expect(grupoPedido).toBeNull()
    expect(ordemPedida).toBeNull()                                                     // D6: sem `ordem`, a API entrega a ordem alfabética
    expect(screen.getByTestId('regra-multas').textContent).toMatch(/Ordem alfabética pelo nome da empresa.*Multa constituída não é condenação definitiva/)
    expect(screen.getByText('1 quitada · 2 devedores')).toBeTruthy()                 // a situação em texto
    fireEvent.change(screen.getAllByRole('combobox')[0], { target: { value: 'SMP' } })
    await waitFor(() => expect(grupoPedido).toBe('SMP'))
  })

  it('aba Multas: síntese com a situação, ano parcial marcado, critério de atualização e nenhuma qualificação de infração (PT-26 / REG 5.2)', async () => {
    server.use(
      http.get('*/api/v1/multas/resumo', () => HttpResponse.json({ ...multasResumo, por_ano: [{ ano: 2025, SCM: 1, SMP: 0, STFC: 0, SeAC: 0, total: 1 }, { ano: 2026, SCM: 2, SMP: 0, STFC: 0, SeAC: 0, total: 2 }] })),
      http.get('*/api/v1/multas/empresas', () => HttpResponse.json({ ...meta, grupo: null, ordem: 'empresa', total: 0, limit: 20, offset: 0, items: [] })),
    )
    montar('/regulatorio?aba=multas')
    const sintese = (await screen.findByTestId('sintese-multas')).textContent ?? ''
    expect(sintese).toMatch(/registra 5 multas constituídas contra pessoas jurídicas de SCM, SMP, STFC e SeAC/)
    expect(sintese).toMatch(/3 \(60%\) constam como quitadas e 2 em aberto \(2 devedor e 0 parcial\)/)
    expect(sintese).toMatch(/saldo devedor atualizado informado pela Anatel/)
    expect(sintese).toMatch(/Multa constituída não é condenação definitiva/)
    expect(screen.getByText(/2026/, { selector: 'td' }).textContent).toMatch(/parcial, até 02\/11\/2026/)
    expect(screen.getByTestId('atualizacao-multas').textContent).toMatch(/Selic.*0,33% ao dia até 20%.*589\/2012.*10\.522\/2002/)
    expect(document.body.textContent).not.toMatch(/infra[çc]|irregular|omi[s]s|culpa|devedor contumaz/i)
  })

  it('aba Multas: abre por empresa (raiz), alterna para por serviço e o gráfico anual tem tabela e marca o ano parcial (PT-26 / REG 5.2)', async () => {
    const visoes: Array<string | null> = []
    server.use(
      http.get('*/api/v1/multas/resumo', () => HttpResponse.json({ ...multasResumo, raizes: 1, por_ano: [{ ano: 2025, SCM: 1, SMP: 0, STFC: 0, SeAC: 0, total: 1 }, { ano: 2026, SCM: 2, SMP: 0, STFC: 0, SeAC: 0, total: 2 }] })),
      http.get('*/api/v1/multas/empresas', ({ request }) => {
        const v = new URL(request.url).searchParams.get('visao')
        visoes.push(v)
        const { grupo: _g, ...resto } = empresa
        return HttpResponse.json({ ...meta, visao: v, grupo: null, ordem: 'empresa', total: 1, limit: 20, offset: 0,
          items: [v === 'raiz' ? { ...resto, servicos: ['SCM', 'SMP'], nomes_alternativos: ['PROVEDOR 1'] } : empresa] })
      }),
    )
    montar('/regulatorio?aba=multas')
    await waitFor(() => expect(screen.getByText('SCM, SMP')).toBeTruthy())
    expect(visoes[0]).toBe('raiz')
    expect(screen.getByRole('button', { name: 'Por empresa' }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByTestId('regra-multas').textContent).toMatch(/Cada linha é uma raiz de CNPJ.*serviços somados.*Valores absolutos.*sem ajuste pelo tamanho da empresa/)
    expect(screen.getByText(/contra 1 raiz de CNPJ \(2 combinações de raiz e serviço\)/)).toBeTruthy()
    expect(screen.getByTestId('grafico-multas-ano')).toBeTruthy()
    expect(screen.getByTestId('ano-parcial').textContent).toMatch(/2026 é parcial: vai até 02\/11\/2026/)
    fireEvent.click(screen.getByRole('button', { name: 'Por serviço' }))
    await waitFor(() => expect(visoes).toContain('servico'))
    await waitFor(() => expect(screen.queryByText('SCM, SMP')).toBeNull())
  })

  it('aba Espectro: faixas de interesse e filtro por serviço', async () => {
    let servicoPedido: string | null = 'x'
    server.use(
      http.get('*/api/v1/espectro/resumo', () => HttpResponse.json({ ...meta, natureza: 'norma', limites: 'É norma, não licença.', resumo: { faixas: 5, com_destinacao: 5, com_atribuicao: 3, de_interesse: 1 },
        referencias: [{ nome: '3,5 GHz', ini_mhz: 3300, fim_mhz: 3700, faixas: 2, destinacao: [{ servico: 'MÓVEL PESSOAL', carater: 'Primário' }, { servico: 'Radioamador', carater: 'Secundário' }] }] })),
      http.get('*/api/v1/espectro/faixas', ({ request }) => {
        servicoPedido = new URL(request.url).searchParams.get('servico')
        return HttpResponse.json({ ...meta, natureza: 'norma', de: null, ate: null, servico: servicoPedido, carater: null, total: 1, limit: 25, offset: 0, referencias: null,
          items: [{ ini_mhz: 3300, fim_mhz: 3400, destinacao: [{ servico: 'MÓVEL PESSOAL', carater: 'Primário' }], atribuicao: [{ servico: 'FIXO', carater: 'Primário' }] }] })
      }),
    )
    montar('/regulatorio?aba=espectro')
    await waitFor(() => expect(screen.getByText('3,5 GHz')).toBeTruthy())
    expect(screen.getByText('Radioamador').className).toContain('text-gray-400')
    fireEvent.change(screen.getByPlaceholderText('ex.: móvel pessoal'), { target: { value: 'fixo' } })
    await waitFor(() => expect(servicoPedido).toBe('fixo'))
  })

  it('aba Satélites: direito vencido aparece marcado; NGEO um sistema por linha com a faixa declarada (REGULATORIO-E1)', async () => {
    const reg = (objeto: string, agenda_ano: number, constelacao: number) => ({ cnpj: null, prestadora: 'P', lancamento: null, estacao: objeto.slice(0, 3), objeto, status: 'OPERAÇÃO COMERCIAL', orbita: 'BAIXA (LEO)', planos: 6, constelacao, agenda_ano })
    server.use(
      http.get('*/api/v1/satelites/resumo', () => HttpResponse.json({ ...meta, resumo: { direitos: 4, operadoras: 3, satelites: 3, por_tipo: { Estrangeiro: 3, Brasileiro: 1 }, por_status: {}, vencidos_na_data: 1, ngeo: 6, ngeo_sistemas: 2, operando: 2, ngeo_por_orbita: {} },
        ngeo: [reg('Iridium', 2026, 66), ...[[2022, 2661], [2023, 4408], [2024, 4408], [2025, 7184], [2026, 9857]].map(([a, c]) => reg('Starlink', a, c))],
        ngeo_sistemas: [{ ...reg('Iridium', 2026, 66), registros: 1, anos_agenda: [2026], constelacao_min: 66, constelacao_max: 66 },
          { ...reg('Starlink', 2026, 9857), registros: 5, anos_agenda: [2022, 2023, 2024, 2025, 2026], constelacao_min: 2661, constelacao_max: 9857 }], operando: [] })),
      http.get('*/api/v1/satelites/direitos', () => HttpResponse.json({ ...meta, operadora: null, tipo: null, status: null, total: 1, limit: 20, offset: 0,
        items: [{ operadora: 'SATELITE BRASILEIRO SA', satelite: 'BR-SAT 2', codigo: 'x', posicao: '65ºO', banda: 'Ka', tipo: 'Brasileiro', status: 'operação comercial', lancamento: '2020-05-10', validade: '2026-01-31', prorrogado: false, vencido: true }] })),
    )
    montar('/regulatorio?aba=satelites')
    await waitFor(() => expect(screen.getByText(/\(vencida\)/)).toBeTruthy())
    expect(screen.getByText('Iridium')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Sistemas de órbita não geoestacionária (2)' })).toBeTruthy()
    expect(screen.getAllByText('Starlink')).toHaveLength(1)
    expect(screen.getByText('2.661 a 9.857 em 5 registros')).toBeTruthy()
  })

  it('aba FUST: programas, editais e municípios; sem executora', async () => {
    const t = { compromissos: 10, atendidos: 4, a_vencer: 3, em_apuracao: 3, investimento: 1_000_000 }
    server.use(
      http.get('*/api/v1/fust/resumo', () => HttpResponse.json({ ...meta, brasil: { ...t, municipios: 5571, municipios_com_compromisso: 3365, programas: 1, editais: 1 }, ufs: { SP: { ...t, municipios: 645, municipios_com_compromisso: 500, programas: { '1.1': 10 } } },
        programas: [{ codigo: '1.1', nome: 'Conectividade para Escolas Públicas', municipios: 8, ...t }], editais: [{ origem: 'Edital nº 1/2026', municipios: 8, ...t }],
        casamento: { compromissos: 10, com_municipio_no_ibge: 10, sem_municipio_no_ibge: 0, base_2010: 5, base_2022: 5, sem_investimento: 0 } })),
      http.get('*/api/v1/fust/municipios', () => HttpResponse.json({ ...meta, uf: null, programa: null, ordem: 'compromissos', total: 1, limit: 15, offset: 0,
        items: [{ ibge: '3550308', nome: 'São Paulo', uf: 'SP', por_10mil_hab: 1, programas: ['1.1'], ...t }] })),
    )
    montar('/regulatorio')
    await waitFor(() => expect(screen.getByText('São Paulo').getAttribute('href')).toBe('/municipio/3550308'))
    expect(screen.getByText(/1\.1 · Conectividade para Escolas Públicas/, { selector: 'td' })).toBeTruthy()
    expect(screen.getByText('Edital nº 1/2026')).toBeTruthy()
  })

  it('bloco de multas da operadora soma as filiais e repete o aviso', () => {
    const multas: MultasOperadora = { ...meta, raiz: '11111111', multas: 3, original: 8000, pago: 1700, saldo: 9050, por_grupo: [empresa as never], brasil: { empresas: 4, multas: 12, saldo: 20000 } }
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><MultasOperadoraBloco dados={{ multas } as never} snapshot={null} /></MemoryRouter></QueryClientProvider>)
    expect(screen.getByText('multas constituídas')).toBeTruthy()
    expect(screen.getByText(/raiz do CNPJ 11111111/)).toBeTruthy()
    expect(screen.getByText(/não é condenação definitiva/)).toBeTruthy()
  })
})
