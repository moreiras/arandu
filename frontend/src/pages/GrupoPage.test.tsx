// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Página do grupo: composição, somas com o "quantas empresas têm o dado" e nenhum dado de pessoa física. */
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { server } from '../test/server'
import { useAppStore } from '../store/app'
import { GrupoPage } from './GrupoPage'

const grupo = {
  snapshot_date: '2026-09-20', grupo_id: 'g1', classificacao: 'total', tamanho: 2, empresas: 2, assinantes: 1500, usuarios_apnic: 900, visibilidade_bgp: true,
  cnpjs: [{ cnpj: '90000001000129', empresa: 'Provedor 01 Telecom Ltda', assinantes: 1000, asns: [64500], has_scm: true }, { cnpj: '90000002000129', empresa: 'Provedor 02 Ltda', assinantes: 500, asns: [], has_scm: true }],
  asns: [64500], municipios: [],
  credito_publico: { empresas_com_registro: 1, operacoes: 3, contratado: 1_000_000, desembolsado: 800_000, natureza: 'operações diretas do BNDES' },
  sancoes: { empresas_com_registro: 0, vigentes: 0, futuras: 0, encerradas: 0, natureza: 'registro do órgão sancionador' },
  contratos: { empresas_lidas: 1, empresas_com_resultado: 1, itens: 4, contratacoes: 3, valor_homologado: 250_000, natureza: 'resultados de itens publicados no PNCP' },
  limites: 'Soma das empresas do grupo que têm o dado.',
}

// recharts (ResponsiveContainer) mede o contêiner com ResizeObserver, que o jsdom não tem
beforeAll(() => { vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} }) })

const mercado = {
  grupo_id: 'g1', mes_referencia: '2026-09', meses: ['2025-09', '2026-09'],
  serie: [{ mes: '2025-09', acessos: 1400, parcela: 0.5 }, { mes: '2026-09', acessos: 1500, parcela: 0.6 }],
  posicao: { atual: 2, ha_12_meses: 3, mes_ha_12_meses: '2025-09', unidades: 900 }, cnpjs_total: 2, cnpjs_com_acessos: 2,
  por_uf: [{ uf: 'SP', acessos: 1000, parcela_do_grupo: 66.7, parcela_na_uf: 0.1, hhi_cnpj: 1700, hhi_grupo: 1800, faixa_grupo: 'moderado' }],
  por_tecnologia: { FTTH: 1500 }, sobreposicao_interna: { municipios: 10, com_mais_de_um_cnpj: 2 },
  concorrentes: [{ cnpj: '22222222000122', empresa: 'Concorrente SA', municipios_em_comum: 7, acessos_dele_nos_comuns: 12345 }],
  natureza: 'fato com agrupamento inferido', limites: 'Posição por acessos declarados.',
}

const regulatorio = {
  grupo_id: 'g1', empresas: 2, outorgas: { SCM: 2, SMP: 0, STFC: 0, SeAC: 1 },
  multas: { empresas_com_registro: 1, multas: 5, original: 1000, pago: 100, saldo: 1200, por_empresa: [{ raiz: '90000001', empresa: 'Provedor 01 Telecom Ltda', multas: 5, original: 1000, pago: 100, saldo: 1200 }], fonte: 'Anatel', limites: 'Multa constituída não é condenação definitiva.' },
  qualidade: { prestadoras: [{ servico: 'Banda Larga Fixa', prestadora: 'PROV01', municipios: 12, casamento: 'curada' }], limites: null },
  reclamacoes_anatel: { marcas: ['PROV01'], anos: [{ ano: 2025, reclamacoes: 40, por_servico: { SCM: 40 } }], limites: null },
  consumidor: { janela: { de: '2025-11', ate: '2026-10' }, marcas: [{ marca: 'Prov 01', casamento: 'curada', n: 77, pct_respondidas: 99, indice_solucao: 70, nota_media: 3.4 }], reclamacoes_finalizadas: 77, limites: null },
  natureza: 'fato', limites: 'Grupo inferido.',
}
const relacoes = {
  grupo_id: 'g1', classificacao: 'total', empresas: 2, referencia_receita: '2026-09', tipos: {},
  ligacoes: [{ tipo: 'quadro_identico', tipo_rotulo: 'Quadro de sócios idêntico', de: '90000001000129', para: '90000002000129', de_nome: 'Provedor 01 Telecom Ltda', para_nome: 'Provedor 02 Ltda', socios: null },
             { tipo: 'controle_parcial', tipo_rotulo: 'Uma empresa controla parte da outra (sócio pessoa jurídica)', de: '90000001000129', para: '90000002000129', de_nome: 'Provedor 01 Telecom Ltda', para_nome: 'Provedor 02 Ltda', socios: 2 }],
  fora_do_grupo: { total: 1, itens: [{ cnpj: '90000009000129', empresa: 'Outra Empresa Ltda', tipo: 'socios_em_comum', tipo_rotulo: 'Sócios em comum', socios_em_comum: 1, liga_a: ['90000001000129'] }] },
  controladoras_externas: [{ cnpj_basico: '31908265', razao_social: 'HOLDING SA', situacao_cadastral: 'ATIVA', natureza_juridica: 'Sociedade Anônima Fechada', controla: ['90000001000129'] }],
  natureza: 'inferido do quadro societário', limites: 'Só a estrutura entre empresas (PJ).',
}
const tecnico = {
  grupo_id: 'g1', asns_total: 2, asns_com_dado: 2, asns_detalhados: 2, asns_omitidos: 0, visibilidade_bgp: true, prefixos: { v4: 10, v6: 4 },
  ipv6: { asns_com_ipv6: 1, usuarios: 1000, usuarios_v6: 500, pct_v6: 50 }, rpki: { validados: 14, valido: 12, invalido: 1, sem_roa: 1, valido_pct: 85.7 },
  transito: { asns_multihomed: 1, provedores: [{ asn: 4230, asns_do_grupo: 2 }] }, ptts: [{ ixp: 'sp', asns: [64500, 64501] }],
  por_asn: [{ asn: 64500, nome: 'Prov 01', usuarios: 700, pct_v6: 60, prefixos_v4: 6, prefixos_v6: 3, tem_ipv6: true, roa_valido_pct: 90, ptts_diretos: 1 }],
  natureza: 'fato e estimativa', limites: 'Grupo inferido.',
}

beforeEach(() => {
  useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' })
  server.use(
    http.get('*/api/v1/grupos/g1', () => HttpResponse.json(grupo)),
    http.get('*/api/v1/grupos/nao', () => new HttpResponse(null, { status: 404 })),
    http.get('*/api/v1/brasil/snapshots/:date', () => HttpResponse.json({ date: '2026-09-20', summary: null, manifest: { sources: [] } })),
  )
})

const montar = (id: string, consulta = '') => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter initialEntries={[`/grupo/${id}${consulta}`]}><Routes><Route path="/grupo/:id" element={<GrupoPage />} /></Routes></MemoryRouter>
  </QueryClientProvider>,
)

describe('/grupo/:id', () => {
  it('mostra a composição e as somas, cada uma com quantas empresas têm o dado', async () => {
    montar('g1')
    expect(await screen.findByRole('heading', { level: 1, name: /Grupo de Provedor 01 Telecom Ltda/ })).toBeInTheDocument()
    const tabela = await screen.findByRole('table', { name: 'Empresas do grupo' })
    expect(within(tabela).getByRole('link', { name: 'Provedor 02 Ltda' })).toHaveAttribute('href', '/operadora/90000002000129')
    expect(screen.getByRole('tab', { name: 'Regulatório' })).toBeInTheDocument()
    cleanup()
    montar('g1', '?aba=regulatorio')                                                    // crédito, sanções e contratos moram na aba Regulatório
    expect((await screen.findAllByText('1 de 2')).length).toBe(2)                    // crédito e contratos: 1 de 2 empresas com o dado; sanções: 0 de 2
    expect(await screen.findByText('0 de 2')).toBeInTheDocument()
    cleanup()
    montar('g1')
    expect(await screen.findByText(/só a estrutura entre empresas é mostrada/)).toBeInTheDocument()
    expect(document.body.textContent).toContain('o grupo reúne as empresas ligadas em cadeia')
    expect(document.body.textContent).not.toMatch(/nunca transitiva/)
    expect(document.body.textContent).not.toMatch(/CPF|sócio pessoa|\d{3}\.\d{3}\.\d{3}-\d{2}/)
  })

  it('aba Mercado: posição, UFs e concorrentes só com dado do grupo, sem veredito', async () => {
    server.use(http.get('*/api/v1/grupos/g1', ({ request }) => HttpResponse.json(new URL(request.url).searchParams.get('include') === 'mercado' ? { ...grupo, mercado_fixo: mercado } : grupo)))
    montar('g1', '?aba=mercado')
    expect(await screen.findByText('2º de 900')).toBeInTheDocument()
    expect(screen.getByText(/subiu 1 posição/)).toBeInTheDocument()
    const ufs = await screen.findByRole('table', { name: 'Acessos do grupo por UF' })
    expect(within(ufs).getByRole('link', { name: 'SP' })).toHaveAttribute('href', '/uf/SP')
    expect(within(ufs).getByText('moderadamente concentrado')).toBeInTheDocument()
    expect(within(await screen.findByRole('table', { name: 'Empresas presentes nos mesmos municípios' })).getByRole('link', { name: 'Concorrente SA' })).toHaveAttribute('href', '/operadora/22222222000122')
    expect(document.body.textContent).not.toMatch(/melhor|pior|vencedor/i)
  })

  it('aba Regulatório: multas por empresa em ordem alfabética, reclamações sem veredito e a contagem de empresas', async () => {
    server.use(http.get('*/api/v1/grupos/g1', ({ request }) => HttpResponse.json(new URL(request.url).searchParams.get('include') === 'regulatorio' ? { ...grupo, regulatorio } : grupo)))
    montar('g1', '?aba=regulatorio')
    expect(await screen.findByText('2 de 2', { selector: 'div' })).toBeInTheDocument()
    const multas = await screen.findByRole('table', { name: 'Multas por empresa do grupo' })
    // cabeçalhos associados às células (GRUPO-E1)
    for (const th of within(multas).getAllByRole('columnheader')) expect(th).toHaveAttribute('scope', 'col')
    expect(screen.getByText(/1 de 2 empresas \(raízes de CNPJ\) têm registro/)).toBeInTheDocument()
    expect(await screen.findByText(/40/, { selector: 'strong' })).toBeInTheDocument()
    for (const th of within(screen.getByRole('table', { name: 'Empresas do Consumidor.gov.br ligadas ao grupo' })).getAllByRole('columnheader')) expect(th).toHaveAttribute('scope', 'col')
    expect(document.body.textContent).not.toMatch(/melhor|pior|vencedor|maior infrator/i)
  })

  it('aba Técnico: ASes, IPv6, RPKI e PTTs, com a ressalva de que peering bilateral não é visível', async () => {
    server.use(http.get('*/api/v1/grupos/g1', ({ request }) => HttpResponse.json(new URL(request.url).searchParams.get('include') === 'tecnico' ? { ...grupo, tecnico } : grupo)))
    montar('g1', '?aba=tecnico')
    const t = await screen.findByRole('table', { name: 'ASes do grupo' })
    expect(within(t).getByRole('link', { name: 'AS64500' })).toHaveAttribute('href', '/asn/64500')
    expect(await screen.findByText('85,7%')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /SP/ })).toHaveAttribute('href', '/ixp/sp')
    // os ASes do PTT estavam só no title (OPERADORA-E4): agora fazem parte do nome acessível do link
    expect(screen.getByRole('link', { name: /SP \(2\)\s*, ASes: AS64500, AS64501/ })).toBeInTheDocument()
    expect(screen.getByText(/Peering bilateral não é visível/)).toBeInTheDocument()
  })

  it('aba Relações: tipo da ligação e contagem de sócios, sem nome de pessoa física', async () => {
    server.use(http.get('*/api/v1/grupos/g1', ({ request }) => HttpResponse.json(new URL(request.url).searchParams.get('include') === 'relacoes' ? { ...grupo, relacoes } : grupo)))
    montar('g1', '?aba=relacoes')
    const t = await screen.findByRole('table', { name: 'Ligações entre as empresas do grupo' })
    expect(within(t).getByText('Quadro de sócios idêntico')).toBeInTheDocument()
    expect(within(t).getAllByRole('link', { name: 'Provedor 02 Ltda' })[0]).toHaveAttribute('href', '/operadora/90000002000129')
    expect(within(t).getByText('2')).toBeInTheDocument()
    expect(screen.getByText(/HOLDING SA/)).toBeInTheDocument()
    expect(screen.getByText(/1 empresa tem ligação parcial com o grupo/)).toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/\d{3}\.\d{3}\.\d{3}-\d{2}|nomes_em_comum/)           // o texto pode dizer que não mostra CPF; não pode haver um
  })

  it('aba Mercado de grupo sem acessos declarados: mensagem, não erro', async () => {
    server.use(http.get('*/api/v1/grupos/g1', () => HttpResponse.json({ ...grupo, mercado_fixo: null })))
    montar('g1', '?aba=mercado')
    expect((await screen.findAllByText(/não tem acessos fixos declarados/)).length).toBeGreaterThan(0)
  })

  it('grupo inexistente: mensagem e volta para a lista', async () => {
    montar('nao')
    expect(await screen.findByText('Grupo não encontrado')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Voltar para os grupos/ })).toHaveAttribute('href', '/grupos')
  })
})

describe('/grupo/:id: D5 (PT-10)', () => {
  const comNome = { ...grupo, nome: 'PROVEDOR 01', nome_regra: 'maior_acesso_sici', nome_regra_texto: 'nome do CNPJ do grupo com mais acessos fixos declarados ao SICI', nome_base: '90000001000129' }

  it('mostra o nome do grupo com a regra que o escolheu, sem afirmar controle', async () => {
    server.use(http.get('*/api/v1/grupos/g1', () => HttpResponse.json(comNome)))
    montar('g1')
    expect(await screen.findByRole('heading', { level: 1, name: /Grupo de PROVEDOR 01/ })).toBeInTheDocument()
    const regra = await screen.findByTestId('grupo-nome-regra')
    expect(regra).toHaveTextContent('Nome do grupo: nome do CNPJ do grupo com mais acessos fixos declarados ao SICI')
    expect(regra).toHaveTextContent('Identificador estável: g1')
    expect(regra).toHaveTextContent(/não afirma controle de uma empresa sobre outra/)
    expect(document.body.textContent).not.toMatch(/grupo econômico verdadeiro/i)
  })

  it('"Mercado consolidado" soma por agrupamento inferido: selo inferido', async () => {
    server.use(http.get('*/api/v1/grupos/g1', () => HttpResponse.json(comNome)))
    montar('g1')
    await screen.findByRole('heading', { level: 1, name: /Grupo de PROVEDOR 01/ })
    const secao = document.getElementById('bloco-mercado') as HTMLElement
    expect(within(secao).getByTestId('proveniencia')).toHaveTextContent(/inferido/i)
    expect(within(secao).getByTestId('proveniencia')).not.toHaveTextContent(/^fato/i)
    expect(secao.textContent).toContain('o agrupamento é inferência')
  })

  it('link com id antigo é redirecionado para o id estável', async () => {
    let pedidos = 0
    server.use(
      http.get('*/api/v1/grupos/grp_antigo', () => HttpResponse.json({ ...comNome, grupo_id: 'g1', redirecionado_de: 'grp_antigo' })),
      http.get('*/api/v1/grupos/g1', () => { pedidos += 1; return HttpResponse.json(comNome) }),
    )
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={['/grupo/grp_antigo']}><Routes><Route path="/grupo/:id" element={<GrupoPage />} /></Routes></MemoryRouter>
      </QueryClientProvider>,
    )
    expect(await screen.findByRole('heading', { level: 1, name: /Grupo de PROVEDOR 01/ })).toBeInTheDocument()
    await vi.waitFor(() => expect(pedidos).toBeGreaterThan(0))                  // a página foi para /grupo/g1 e pediu o grupo pelo id estável
    expect(screen.getByTestId('grupo-nome-regra')).toHaveTextContent('Identificador estável: g1')
  })

  it('aba Relações: força da evidência e classe de qualificação por ligação, e a regra de ligação', async () => {
    const rel = {
      ...relacoes, classes: { socio: 'sócio', socio_administrador: 'sócio-administrador' }, forcas: { forte: 'quadro idêntico, participação de uma empresa na outra ou 2 ou mais sócios em comum', fraca: 'um único sócio em comum' },
      regra_ligacao: 'Só sócio com participação societária liga empresas. Administrador, diretor e presidente sem participação não ligam.', resumo: { ligacoes: 2, fortes: 1, fracas: 1 },
      ligacoes: [{ ...relacoes.ligacoes[0], forca: 'forte', classes_qualificacao: ['socio_administrador'] }, { ...relacoes.ligacoes[1], tipo: 'socios_em_comum', tipo_rotulo: 'Sócios em comum', socios: 1, forca: 'fraca', classes_qualificacao: ['socio'] }],
    }
    server.use(http.get('*/api/v1/grupos/g1', ({ request }) => HttpResponse.json(new URL(request.url).searchParams.get('include') === 'relacoes' ? { ...comNome, relacoes: rel } : comNome)))
    montar('g1', '?aba=relacoes')
    const t = await screen.findByRole('table', { name: 'Ligações entre as empresas do grupo' })
    expect(within(t).getByText('forte')).toBeInTheDocument()
    expect(within(t).getByText('fraca (1 sócio)')).toBeInTheDocument()
    expect(within(t).getByText('sócio-administrador')).toBeInTheDocument()
    expect(within(t).getByText('sócio')).toBeInTheDocument()
    expect(screen.getByTestId('grupo-regra-ligacao')).toHaveTextContent('Administrador, diretor e presidente sem participação não ligam')
    expect(screen.getByTestId('grupo-forca-resumo')).toHaveTextContent('1 de 2 ligações são fortes')
    expect(screen.getByTestId('grupo-forca-resumo')).toHaveTextContent('pode ser homonímia')
  })
})
