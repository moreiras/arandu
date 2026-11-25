// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../test/server'
import { MercadoIpv4Page } from './MercadoIpv4Page'
import { CicloDeVidaBloco } from '../features/prefixo/blocks/CicloDeVidaBloco'

vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ anon: null, loading: false }) }))

const meta = { natureza: 'observado', fonte: 'Registro.br e LACNIC', limites: 'Não se atribui causa nem intenção.', snapshot_date: '2026-11-01' }
const parte = (nome: string, pais = 'BR') => ({ nome, pais, rir: 'NICBR', pessoa: nome === 'Pessoa física' ? 'pf_provavel' : 'pj' })
const operacao = (o: object) => ({ id: 'x', data: '2026-03-01', origem: parte('ALFA LTDA'), destino: parte('BETA LTDA'), blocos: ['198.18.0.0/24'], n_blocos: 1, enderecos: 256, tamanho: 'ate_24', direcao: 'br_br', fontes: ['registrobr'],
  primeira_vez_visto: '2026-03-02', anterior_a_coleta: false, defasagem_dias: 1, ...o })
const mercado = { ...meta, periodo: ['2026-03-01', '2026-10-29'], operacoes: 3, blocos: 4, enderecos: 1024, por_ano: { '2026': { operacoes: 3, blocos: 4, enderecos: 1024, por_direcao: { br_br: { operacoes: 2, enderecos: 768 }, br_exterior: { operacoes: 1, enderecos: 256 } } } },
  por_tamanho: { ate_24: 2, '22_a_23': 1 }, concentracao: { top_destinos: [], top_origens: [] }, maior_operacao: { data: '2026-03-01', blocos: 2, enderecos: 512 },
  defasagem: { operacoes_com_medida: 2, mediana_dias: 1, maximo_dias: 2 }, casamento: { destino_br: 2, com_asn: 1, pct: 50 } }

const montar = (el: JSX.Element, rota = '/mercado-ipv4') => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[rota]}>{el}</MemoryRouter></QueryClientProvider>,
)

describe('Mercado de IPv4', () => {
  it('mostra o resumo, a lista com pessoa física omitida e o ASN atual, e filtra por direção', async () => {
    let direcaoPedida: string | null = 'x'
    server.use(
      http.get('*/api/v1/ipv4/transferencias/resumo', () => HttpResponse.json(mercado)),
      http.get('*/api/v1/ipv4/transferencias', ({ request }) => {
        direcaoPedida = new URL(request.url).searchParams.get('direcao')
        return HttpResponse.json({ ...meta, filtros: {}, total: 2, limit: 25, offset: 0, items: [operacao({ origem: parte('Pessoa física'), casamento: { asn: 64500, org: 'BETA' } }), operacao({ id: 'y', anterior_a_coleta: true })] })
      }),
    )
    montar(<MercadoIpv4Page />)
    await waitFor(() => expect(screen.getByText('Pessoa física')).toBeTruthy())
    expect(screen.getByText('AS64500').getAttribute('href')).toBe('/asn/64500')
    expect(screen.getByText('antes da coleta')).toBeTruthy()
    expect(screen.getByText(/Maior operação: 2 blocos/)).toBeTruthy()
    expect(screen.getByText(/50% dos destinos brasileiros casam/)).toBeTruthy()
    expect(screen.getByText(/Não se atribui causa nem intenção/)).toBeTruthy()
    expect(direcaoPedida).toBeNull()
    fireEvent.change(screen.getByLabelText('Direção'), { target: { value: 'br_exterior' } })
    await waitFor(() => expect(direcaoPedida).toBe('br_exterior'))
  })

  it('aba Recuperação lista os recursos e os eventos por mês', async () => {
    server.use(
      http.get('*/api/v1/ipv4/transferencias/resumo', () => HttpResponse.json(mercado)),
      http.get('*/api/v1/ipv4/recuperacao', () => HttpResponse.json({ ...meta, em_recuperacao: { total: 2, por_tipo: { bloco: 1, asn: 1 }, janelas: [['2026-09-01', '2026-11-30']],
        itens: [{ tipo: 'bloco', recurso: '198.19.4.0/24', inicio: '2026-09-01', fim: '2026-11-30', primeira_vez_visto: null, status_delegated: 'reserved' }, { tipo: 'asn', recurso: '64999', inicio: '2026-09-01', fim: '2026-11-30', primeira_vez_visto: null, status_delegated: null }] },
        recuperados: { total: 5, por_tipo: {} }, eventos_por_mes: { '2026-09': { recuperacao: 256 } } })),
    )
    montar(<MercadoIpv4Page />, '/mercado-ipv4?aba=recuperacao')
    await waitFor(() => expect(screen.getByText('198.19.4.0/24')).toBeTruthy())
    expect(screen.getByText('AS64999').getAttribute('href')).toBe('/asn/64999')
    expect(screen.getByText('reserved')).toBeTruthy()
    expect(screen.getByText('2026-09')).toBeTruthy()
  })
})

describe('bloco Ciclo de vida do prefixo', () => {
  const dados = { prefix: '198.18.2.0/24', date: '2026-11-01', info: {} as never, carregandoAsn: false }
  it('mostra o estado atual e a linha do tempo com o aviso de que não há causa nem intenção', async () => {
    server.use(http.get('*/api/v1/ipv4/blocos/*', () => HttpResponse.json({ ...meta, bloco: '198.18.2.0/24', aviso: 'Diferenças observadas, sem causa nem intenção.',
      atual: [{ inicio: '198.18.2.0', quantidade: 256, status: 'allocated', data_registro: '20120501', opaque_id: 'org-b', asn: 64497, organizacao: 'Provedor 02' }],
      espaco: [{ inicio: '198.18.2.0', quantidade: 256, classe: 'nao_anunciado', anunciado_pct: 0, asn: 64497, org: 'P', cnpj: null, uf: 'SP', tabelas_sem_anuncio: 3, sem_anuncio_desde: '2026-09-06', ano_registro: '2012', roa_asns: [] }],
      sinais_de_terceiros: [{ inicio: '198.18.2.0', quantidade: 256, classe: 'anunciado', anunciado_pct: 100, origens: [300], roa_asns: [], confianca: 'media', titular: null, sinais: [{ id: 'S3', confianca: 'media', evidencia: 'sem ASN titular; anunciado por AS300' }] }],
      linha_do_tempo: [{ data: '2026-03-02', fonte: 'delegated', tipo: 'titularidade', detalhe: { de: { opaque: 'org-a' }, para: { opaque: 'org-b' } } }] })))
    montar(<CicloDeVidaBloco dados={dados} snapshot={null} />)
    await waitFor(() => expect(screen.getByText('Mudou de organização (opaque-id)')).toBeTruthy())
    expect(screen.getByText(/de org-a · para org-b/)).toBeTruthy()
    expect(screen.getByText('AS64497').getAttribute('href')).toBe('/asn/64497')
    expect(screen.getByText(/sem causa nem intenção/)).toBeTruthy()
    expect(screen.getByText(/Hipótese de uso por terceiros \(198.18.2.0\)/)).toBeTruthy()
    expect(screen.getByText(/sem ASN titular; anunciado por AS300/)).toBeTruthy()
    expect(screen.getByText(/Não anunciado não é sem uso/)).toBeTruthy()
  })

  it('sem registro do Brasil não renderiza nada', async () => {
    server.use(http.get('*/api/v1/ipv4/blocos/*', () => new HttpResponse(null, { status: 204 })))
    const { container } = montar(<CicloDeVidaBloco dados={dados} snapshot={null} />)
    await new Promise((r) => setTimeout(r, 50))
    expect(container.innerHTML).toBe('')
  })
})

describe('Mercado de IPv4: espaço sem uso e uso por terceiros', () => {
  const meta2 = { ...meta, natureza: 'inferido' }
  it('espaço: avisa que não anunciado não é sem uso, mostra o resumo e a duração em tabelas de origem', async () => {
    server.use(
      http.get('*/api/v1/ipv4/transferencias/resumo', () => HttpResponse.json(mercado)),
      http.get('*/api/v1/ipv4/espaco', () => HttpResponse.json({ ...meta2, ultima_foto: '2026-11-02', filtros: {}, total: 1, limit: 25, offset: 0,
        resumo: { total_blocos: 10, total_enderecos: 2560, por_classe: { anunciado: { blocos: 9, enderecos: 2304 }, nao_anunciado: { blocos: 1, enderecos: 256 } }, por_uf: { SP: { blocos: 10, enderecos: 2560, nao_anunciado: 256 } }, maiores_titulares_nao_anunciado: [] },
        duracao: { tabelas_anteriores_consultadas: ['2026-10-27'], maximo_de_tabelas: 11 },
        items: [{ inicio: '198.18.9.0', quantidade: 256, classe: 'nao_anunciado', anunciado_pct: 0, asn: 64500, org: 'ALFA', cnpj: null, uf: 'SP', tabelas_sem_anuncio: 3, sem_anuncio_desde: '2026-10-13', ano_registro: '2012', roa_asns: [] }] })),
    )
    montar(<MercadoIpv4Page />, '/mercado-ipv4?aba=espaco')
    await waitFor(() => expect(screen.getByText('198.18.9.0')).toBeTruthy())
    expect(screen.getAllByText(/Não anunciado não é sem uso/).length).toBeGreaterThan(0)
    expect(screen.getByText(/3 tabelas \(desde/)).toBeTruthy()
    expect(screen.getByText('AS64500').getAttribute('href')).toBe('/asn/64500')
  })

  it('uso por terceiros: rotula como hipótese, mostra cada sinal com falso positivo e os não avaliados com o motivo', async () => {
    server.use(
      http.get('*/api/v1/ipv4/transferencias/resumo', () => HttpResponse.json(mercado)),
      http.get('*/api/v1/ipv4/uso-por-terceiros', () => HttpResponse.json({ ...meta2, rotulo: 'hipótese de uso por terceiros', por_sinal: { S1: 1 }, por_confianca: { media: 1 }, blocos_avaliados: 10, total: 1, limit: 25, offset: 0,
        sinais: { S1: { nome: 'Origem diferente do titular', avaliado: true, falsos_positivos: 'Provedor que anuncia o bloco do cliente.' }, S5: { nome: 'Geofeed divergente', avaliado: false, motivo: 'Sem coleta de geofeed por bloco.' } },
        items: [{ inicio: '198.18.9.0', quantidade: 256, classe: 'anunciado', anunciado_pct: 100, origens: [300], roa_asns: [], confianca: 'media', titular: { asn: 64500, org: 'ALFA', cnpj: null }, sinais: [{ id: 'S1', confianca: 'media', evidencia: 'anunciado por AS300, titular AS64500' }] }] })),
    )
    montar(<MercadoIpv4Page />, '/mercado-ipv4?aba=terceiros')
    await waitFor(() => expect(screen.getByText(/Hipótese de uso por terceiros, não aluguel/)).toBeTruthy())
    expect(screen.getByText(/Falso positivo conhecido: Provedor que anuncia o bloco do cliente/)).toBeTruthy()
    expect(screen.getByText('Sem coleta de geofeed por bloco.')).toBeTruthy()
    expect(screen.getByText(/anunciado por AS300, titular AS64500/)).toBeTruthy()
  })
})

describe('Mercado de IPv4: sub-asignações (IPV4-E15)', () => {
  const aguardando = { ...meta, natureza: 'indisponivel', ativa: false, aguardando: true, esquema_hipotetico: true,
    aviso: 'Aguardando a publicação oficial. A política LAC-2025-5 foi ratificada.', politica: { nome: 'LAC-2025-5', estado: 'ratificada em 2026-03-24', fonte_oficial: 'ainda não publicada' },
    validacoes: { receptor_origina: 'x' }, vigia: { ultima_varredura: '2026-11-02', alertas_30_dias: [{ data: '2026-11-02', tipo: 'padrao_novo', nome: 'bitacora.json', url: 'https://ftp.lacnic.net/' }] },
    indicador_terceiros: { com_registro: null, sem_registro: null, nota: 'x' }, eventos: [], total: 0, limit: 100, offset: 0, items: [] }

  it('sem bitácora oficial não há aba: um quadro ao fim de Transferências diz o que falta, sem registro inventado', async () => {
    server.use(
      http.get('*/api/v1/ipv4/transferencias/resumo', () => HttpResponse.json(mercado)),
      http.get('*/api/v1/ipv4/subasignacoes', () => HttpResponse.json(aguardando)),
    )
    montar(<MercadoIpv4Page />, '/mercado-ipv4?aba=subasignacoes')                  // o link antigo cai em Transferências
    await waitFor(() => expect(screen.getByTestId('quadro-subasignacoes')).toBeTruthy())
    const quadro = screen.getByTestId('quadro-subasignacoes').textContent ?? ''
    expect(quadro).toMatch(/LAC-2025-5: ratificada em 2026-03-24\. Fonte oficial: ainda não publicada\. Nenhum arquivo oficial encontrado até a varredura de/)
    expect(quadro).toMatch(/padrao novo bitacora.json/)
    expect(screen.queryByRole('tab', { name: 'Sub-asignações' })).toBeNull()
    expect(screen.queryByText(/sub-asignações\. Anúncios/)).toBeNull()
  })

  it('com fonte oficial a aba existe e mostra só agregados das verificações do OBINT, sem coluna por receptor nem conformidade total', async () => {
    const ativa = { ...aguardando, ativa: true, aguardando: false, aviso: null, validacoes: { receptor_origina: 'o receptor origina o bloco', tem_roa: 'tem ROA' }, total: 2,
      indicador_terceiros: { com_registro: 1, sem_registro: 0, nota: 'n' },
      items: [{ id: 'a', bloco: '203.0.113.0/24', receptor_asn: 64500, cedente_asn: null, inicio: '2026-01-01', fim: null, rir: 'lacnic', validacoes: { receptor_origina: true, tem_roa: null }, em_conformidade: false, pendentes: ['tem_roa'] },
        { id: 'b', bloco: '198.51.100.0/24', receptor_asn: 64501, cedente_asn: null, inicio: '2026-02-01', fim: null, rir: 'lacnic', validacoes: { receptor_origina: false, tem_roa: true }, em_conformidade: false, pendentes: [] }] }
    server.use(
      http.get('*/api/v1/ipv4/transferencias/resumo', () => HttpResponse.json(mercado)),
      http.get('*/api/v1/ipv4/subasignacoes', () => HttpResponse.json(ativa)),
    )
    montar(<MercadoIpv4Page />, '/mercado-ipv4?aba=subasignacoes')
    await waitFor(() => expect(screen.getByText(/Verificações feitas pelo OBINT \(não são decisão do Registro\.br nem do LACNIC\)/)).toBeTruthy())
    const agregado = screen.getByRole('table', { name: /agregadas/ })
    expect(within(agregado).getByText('origina').closest('tr')!.textContent).toBe('origina110')       // 1 sim, 1 não, 0 sem dado
    expect(within(agregado).getByText('ROA').closest('tr')!.textContent).toBe('ROA101')
    expect(document.body.textContent).not.toMatch(/conformidade|em conformidade/i)
    expect(screen.queryByRole('columnheader', { name: 'ROA' })).toBeNull()                     // nada por receptor na tabela de registros
  })
})
