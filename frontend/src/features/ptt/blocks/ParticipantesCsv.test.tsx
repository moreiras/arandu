// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../../test/server'
import { ParticipantesTabelaBloco } from './ParticipantesTabelaBloco'
import { CABECALHO_PARTICIPANTES, montarCsvParticipantes } from '../participantesCsv'
import type { ParticipantePtt, ParticipantesPtt } from '../../../types/api'

const auth = vi.hoisted(() => ({ logado: false, motivos: [] as string[] }))
vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ user: auth.logado ? { id: 'x' } : null, requireLogin: (m?: string) => { if (!auth.logado) auth.motivos.push(m ?? ''); return auth.logado } }),
}))

const linha = (asn: number, o: Partial<ParticipantePtt> = {}): ParticipantePtt => ({
  asn, nome: `REDE, ${asn}`, uf: 'SP', is_br: true, membro: true, direto: { v6: null, v4: true }, originador: { v6: null, v4: false }, sessao_rs: { sessoes: 2, up: 2, down: 0, incertas: 0 },
  cadastrado_sem_sessao_rs: false, sessao_rs_sem_cadastro: false, rejeicao: { filtradas: 20, recebidas: 100, pct: 20, sessoes_up: 2 },
  rejeicao_detalhe: { rotas: 20, coletado_ate: '2026-11-12T10:00:00Z', idade_dias: 10, herdado: true, contagem: 'exata' }, cdns: ['CDN Alfa', 'CDN Beta'],
  sici: { acessos: 12345, compartilhado: true }, ...o,
})
const fontes: ParticipantesPtt['fontes'] = {
  cadastro: { fonte: 'IX.br (cadastro de participantes)', snapshot: '2026-11-22' }, looking_glass: { fonte: 'looking glass do IX.br', snapshot: '2026-11-22', coleta: { v6: 'vazia', v4: 'ok' } },
  route_servers: { fonte: 'Alice-LG', coletado_em: '2026-11-22T06:00:00+00:00', versao_alice: '6.1.0', rs_consultados: 1, rs_total: 1 },
  rejeicoes_por_motivo: { fonte: 'Alice-LG', coletado_nivel2: '2026-11-21T06:00:00+00:00', cobertura: null }, cdns: { fonte: 'lista curada de CDNs', snapshot: '2026-11-22' },
  sici: { fonte: 'Anatel, SICI (banda larga fixa)', mes_referencia: '2026-09', snapshot: '2026-11-22' },
}
const resposta = (items: ParticipantePtt[], total = items.length): ParticipantesPtt => ({
  snapshot_date: '2026-11-22', ixp: 'fec', limites: 'Cada linha é um ASN.', filtros: { q: null, uf: null, filtro: 'todos', definicao_do_filtro: 'todos os participantes' }, ordem: 'ASN, crescente (ordem neutra)',
  page: 1, limit: 50, route_servers_medido: true, fontes, total, total_participantes: total,
  contagens: { todos: total, 'sem-v6': 0, 'sem-v4': 0, 'sem-direto': 0, 'membro-sem-sessao-rs': 0, 'sessao-sem-cadastro': 0, 'com-cdn': total, 'com-rejeicao': total }, ufs: ['SP'], items,
})

describe('montarCsvParticipantes', () => {
  it('IPv6 antes de IPv4, família sem coleta vazia (nunca "não"), aspas em vírgula, BOM e data do snapshot e do mês do SICI em cada linha', () => {
    const csv = montarCsvParticipantes([linha(64496), linha(64497, { sici: null, rejeicao: null, rejeicao_detalhe: null, sessao_rs: null, cdns: [] })], fontes, '2026-11-22')
    expect(csv.charCodeAt(0)).toBe(0xfeff)
    const [cab, a, b] = csv.slice(1).split('\n')
    expect(cab).toBe(CABECALHO_PARTICIPANTES.join(','))
    const nomes = cab.split(',')
    expect(nomes.indexOf('direto_v6')).toBeLessThan(nomes.indexOf('direto_v4'))
    expect(nomes.indexOf('originador_v6')).toBeLessThan(nomes.indexOf('originador_v4'))
    expect(a).toBe('64496,"REDE, 64496",SP,sim,,sim,,não,2,2,0,20,100,20,20,10,sim,12345,sim,2026-09,CDN Alfa CDN Beta,2026-11-22')
    expect(b).toBe('64497,"REDE, 64497",SP,sim,,sim,,não,,,,,,,,,,,,,,2026-11-22')
    expect(csv).not.toMatch(/@|telefone|e-mail/i)
  })
})

describe('botão Baixar CSV da tabela de participantes', () => {
  const pedidos: URL[] = []
  let baixou: Blob[] = []
  beforeEach(() => {
    auth.logado = false; auth.motivos.length = 0; pedidos.length = 0; baixou = []
    URL.createObjectURL = (b: Blob | MediaSource) => { baixou.push(b as Blob); return 'blob:x' }
    URL.revokeObjectURL = () => {}
    HTMLAnchorElement.prototype.click = () => {}
  })
  const montar = () => {
    server.use(http.get('*/api/v1/ixps/fec/participantes', ({ request }) => {
      const u = new URL(request.url); pedidos.push(u)
      const pag = Number(u.searchParams.get('page') ?? '1'), lim = Number(u.searchParams.get('limit') ?? '50')
      const todos = Array.from({ length: 250 }, (_, i) => linha(64500 + i))
      return HttpResponse.json({ ...resposta(todos.slice((pag - 1) * lim, pag * lim), 250), page: pag, limit: lim })
    }))
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return render(<QueryClientProvider client={qc}><MemoryRouter initialEntries={['/ixp/fec?aba=participantes&filtro=sem-v6&ordem=assinantes&sentido=desc']}>
      <ParticipantesTabelaBloco {...({ dados: { code: 'fec', date: '2026-11-22', setSelectedPeerV4: () => {}, setSelectedPeerV6: () => {} } } as any)} /></MemoryRouter></QueryClientProvider>)
  }

  it('sem login pede o login com o motivo "exportar" e não faz nenhuma chamada além da tabela', async () => {
    montar()
    await screen.findByText('AS64500')
    const antes = pedidos.length
    fireEvent.click(screen.getByRole('button', { name: 'Baixar CSV' }))
    expect(auth.motivos).toEqual(['exportar'])
    expect(pedidos.length).toBe(antes)
    expect(baixou).toHaveLength(0)
  })

  it('logado, pede o PTT inteiro em páginas de 200 com o filtro e a ordem da tela e baixa um CSV com todas as linhas', async () => {
    auth.logado = true
    montar()
    await screen.findByText('AS64500')
    pedidos.length = 0
    fireEvent.click(screen.getByRole('button', { name: 'Baixar CSV' }))
    await waitFor(() => expect(baixou).toHaveLength(1))
    expect(pedidos.map((u) => [u.searchParams.get('page'), u.searchParams.get('limit')])).toEqual([['1', '200'], ['2', '200']])
    expect(pedidos.every((u) => u.searchParams.get('filtro') === 'sem-v6' && u.searchParams.get('ordem') === 'assinantes' && u.searchParams.get('desc') === 'true')).toBe(true)
    const texto = await new Promise<string>((ok) => { const r = new FileReader(); r.onload = () => ok(String(r.result)); r.readAsText(baixou[0]) })
    expect(texto.split('\n')).toHaveLength(251)                                  // cabeçalho + 250 linhas
  })
})
