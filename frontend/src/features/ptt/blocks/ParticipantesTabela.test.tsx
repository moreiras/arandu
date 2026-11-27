// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../../test/server'
import { ParticipantesTabelaBloco } from './ParticipantesTabelaBloco'
import type { ParticipantePtt, ParticipantesPtt } from '../../../types/api'

const linha = (asn: number, o: Partial<ParticipantePtt> = {}): ParticipantePtt => ({
  asn, nome: `REDE ${asn}`, uf: 'SP', is_br: true, membro: true, direto: { v6: true, v4: true }, originador: { v6: true, v4: true }, sessao_rs: { sessoes: 2, up: 2, down: 0, incertas: 0 },
  cadastrado_sem_sessao_rs: false, sessao_rs_sem_cadastro: false, rejeicao: { filtradas: 20, recebidas: 100, pct: 20, sessoes_up: 2 },
  rejeicao_detalhe: { rotas: 20, coletado_ate: '2026-11-12T10:00:00Z', idade_dias: 10, herdado: true, contagem: 'exata' }, cdns: ['CDN Alfa'], sici: null, ...o,
})
const resposta = (items: ParticipantePtt[], o: Partial<ParticipantesPtt> = {}): ParticipantesPtt => ({
  snapshot_date: '2026-11-22', ixp: 'fec', limites: 'Cada linha é um ASN.', filtros: { q: null, uf: null, filtro: 'todos', definicao_do_filtro: 'todos os participantes' }, ordem: 'ASN, crescente (ordem neutra)',
  page: 1, limit: 50, route_servers_medido: true,
  fontes: { cadastro: { fonte: 'IX.br (cadastro de participantes)', snapshot: '2026-11-22' }, looking_glass: { fonte: 'looking glass do IX.br', snapshot: '2026-11-22', coleta: { v6: 'ok', v4: 'ok' } },
    route_servers: { fonte: 'Alice-LG', coletado_em: '2026-11-22T06:00:00+00:00', versao_alice: '6.1.0', rs_consultados: 1, rs_total: 1 },
    rejeicoes_por_motivo: { fonte: 'Alice-LG', coletado_nivel2: '2026-11-21T06:00:00+00:00', cobertura: null }, cdns: { fonte: 'lista curada de CDNs', snapshot: '2026-11-22' }, sici: { fonte: 'Anatel, SICI (banda larga fixa)', mes_referencia: '2026-09', snapshot: '2026-11-22' } },
  total: items.length, total_participantes: items.length,
  contagens: { todos: items.length, 'sem-v6': 0, 'sem-v4': 0, 'sem-direto': 0, 'membro-sem-sessao-rs': 1, 'sessao-sem-cadastro': 0, 'com-cdn': items.length, 'com-rejeicao': items.length }, ufs: ['SP'], items, ...o,
})

const pedidos: URL[] = []
function Onde() { const l = useLocation(); return <p data-testid="onde">{l.pathname}{l.search}</p> }
const dados = { code: 'fec', date: '2026-11-22', setSelectedPeerV4: () => {}, setSelectedPeerV6: () => {} } as any
function montar(corpo: ParticipantesPtt | ((u: URL) => ParticipantesPtt), url = '/ixp/fec?aba=participantes') {
  server.use(http.get('*/api/v1/ixps/fec/participantes', ({ request }) => { const u = new URL(request.url); pedidos.push(u); return HttpResponse.json(typeof corpo === 'function' ? corpo(u) : corpo) }))
  pedidos.length = 0
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><MemoryRouter initialEntries={[url]}><ParticipantesTabelaBloco {...({ dados } as any)} /><Onde /></MemoryRouter></QueryClientProvider>)
}

describe('tabela única de participantes do PTT (PT-24 / IXP-E5.5)', () => {
  it('mostra cadastro, direto por família (IPv6 antes de IPv4) e CDNs, com legenda, cabeçalhos com escopo e fonte com data', async () => {
    montar(resposta([linha(64496), linha(64497, { membro: false, direto: { v6: false, v4: true } })]))
    await screen.findByText('AS64496')
    const tabela = screen.getByRole('table')
    expect(within(tabela).getByText(/Participantes do PTT: uma linha por ASN/)).toBeInTheDocument()          // caption
    const cab = within(tabela).getAllByRole('columnheader')
    expect(cab.every((c) => c.getAttribute('scope') === 'col')).toBe(true)
    const nomes = cab.map((c) => c.textContent ?? '')
    expect(nomes.findIndex((t) => /Direto IPv6/.test(t))).toBeLessThan(nomes.findIndex((t) => /Direto IPv4/.test(t)))
    expect(nomes.findIndex((t) => /Originador IPv6/.test(t))).toBeLessThan(nomes.findIndex((t) => /Originador IPv4/.test(t)))
    expect(screen.getByText(/Fato · .*cadastro de participantes.* · ref\. 2026-11-22/)).toBeInTheDocument()
    expect(screen.getByText(/Fato · Alice-LG 6\.1\.0: sessões e rotas filtradas ÷ recebidas · ref\. 2026-11-22/)).toBeInTheDocument()
    expect(screen.getAllByText('CDN Alfa').length).toBe(2)
  })

  it('acessos fixos do SICI: número com fonte e mês de referência, "compartilhado" quando o CNPJ tem mais de um ASN, traço sem vínculo, e a ordem pede ao servidor', async () => {
    montar(resposta([linha(64496, { sici: { acessos: 12345, compartilhado: false } }), linha(64497, { sici: { acessos: 900, compartilhado: true } }), linha(64498)]))
    await screen.findByText('AS64496')
    const cel = (asn: string) => Array.from(screen.getByText(asn).closest('tr')!.querySelectorAll('td')).map((t) => t.textContent)
    expect(cel('AS64496')).toContain('12.345')
    expect(cel('AS64497')).toContain('900 (compartilhado)')
    expect(cel('AS64498')).not.toContain('0')
    expect(cel('AS64498')[cel('AS64498').length - 2]).toBe('—')
    expect(screen.getByText(/Fato · Anatel, SICI \(banda larga fixa\): coluna Acessos fixos.* · ref\. 2026-09/)).toBeInTheDocument()
    fireEvent.click(within(screen.getByRole('columnheader', { name: /Acessos fixos/ })).getAllByRole('button')[0])
    await waitFor(() => expect(pedidos[pedidos.length - 1].searchParams.get('ordem')).toBe('assinantes'))
    expect(pedidos[pedidos.length - 1].searchParams.get('esquema')).toBe('2')
  })

  it('família sem coleta aparece como "sem coleta", nunca como "não", e o aviso diz que isso não é ausência de sessão', async () => {
    montar(resposta([linha(64496, { direto: { v6: null, v4: true }, originador: { v6: null, v4: true } })], {
      fontes: { ...resposta([]).fontes, looking_glass: { fonte: 'looking glass do IX.br', snapshot: '2026-11-22', coleta: { v6: 'vazia', v4: 'ok' } } } }))
    await screen.findByText('AS64496')
    const cel = Array.from(document.querySelectorAll('tbody tr:first-child td')).map((t) => t.textContent)
    expect(cel.filter((t) => t === 'sem coleta')).toHaveLength(2)                 // direto IPv6 e originador IPv6
    expect(cel).not.toContain('não')
    expect(screen.getByText(/Sem coleta válida no looking glass em IPv6 neste snapshot/)).toBeInTheDocument()
  })

  it('ASN fora do Brasil não tem originador publicado: diz "n/d", não "não"', async () => {
    montar(resposta([linha(64500, { is_br: false, originador: { v6: null, v4: null } })]))
    await screen.findByText('AS64500')
    expect(document.body.textContent).toMatch(/n\/d \(fora do Brasil\)/)
  })

  it('o filtro pede ao servidor, vai para a URL e traz os contadores do PTT inteiro; o botão tem aria-pressed', async () => {
    montar((u) => resposta(u.searchParams.get('filtro') === 'membro-sem-sessao-rs' ? [linha(64498, { sessao_rs: { sessoes: 0, up: 0, down: 0, incertas: 0 }, cadastrado_sem_sessao_rs: true })] : [linha(64496), linha(64498)]))
    await screen.findByText('AS64496')
    const chip = screen.getByRole('button', { name: /No cadastro, sem sessão no RS \(1\)/ })
    expect(chip).toHaveAttribute('aria-pressed', 'false')
    fireEvent.click(chip)
    await waitFor(() => expect(screen.getByTestId('onde').textContent).toContain('filtro=membro-sem-sessao-rs'))
    await waitFor(() => expect(screen.queryByText('AS64496')).not.toBeInTheDocument())
    expect(screen.getByText('AS64498')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /No cadastro, sem sessão no RS/ })).toHaveAttribute('aria-pressed', 'true')
    expect(pedidos[pedidos.length - 1].searchParams.get('filtro')).toBe('membro-sem-sessao-rs')
    expect(screen.getByTestId('onde').textContent).toContain('aba=participantes')          // a lente da página continua
  })

  it('o estado vem da URL (filtro, ordem, página, colunas do route server)', async () => {
    montar(resposta([linha(64496)], { total: 120, total_participantes: 120 }), '/ixp/fec?aba=participantes&filtro=sem-v4&ordem=nome&sentido=desc&pagina=2&rs=1')
    await screen.findByText('AS64496')
    const u = pedidos[0].searchParams
    expect([u.get('filtro'), u.get('ordem'), u.get('desc'), u.get('page'), u.get('limit')]).toEqual(['sem-v4', 'nome', 'true', '2', '50'])
    expect(screen.getByRole('columnheader', { name: /Sessões RS/ })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: /Nome/ })).toHaveAttribute('aria-sort', 'descending')
    expect(screen.getByText(/página 2 de 3/)).toBeInTheDocument()
  })

  it('a ordem padrão é por ASN e o cabeçalho de ordenação é um botão com aria-sort', async () => {
    montar(resposta([linha(64496)]))
    await screen.findByText('AS64496')
    expect(screen.getByRole('columnheader', { name: /ASN/ })).toHaveAttribute('aria-sort', 'ascending')
    expect(screen.getByRole('columnheader', { name: /Nome/ })).toHaveAttribute('aria-sort', 'none')
    fireEvent.click(within(screen.getByRole('columnheader', { name: /^Nome/ })).getByRole('button'))
    await waitFor(() => expect(pedidos[pedidos.length - 1].searchParams.get('ordem')).toBe('nome'))
  })

  it('a linha abre por teclado (botão com aria-expanded) e mostra a idade e a herança da coleta por motivo, com a regra de leitura', async () => {
    montar(resposta([linha(64496)]), '/ixp/fec?aba=participantes&rs=1')
    await screen.findByText('AS64496')
    const botao = screen.getByRole('button', { name: 'Detalhes de AS64496' })
    expect(botao).toHaveAttribute('aria-expanded', 'false')
    expect(document.body.textContent).toMatch(/10 d, herdada/)
    fireEvent.click(botao)
    expect(botao).toHaveAttribute('aria-expanded', 'true')
    expect(botao.getAttribute('aria-controls')).toBe('part-64496')
    const det = document.getElementById('part-64496')!
    expect(det.textContent).toMatch(/20 ÷ 100 \(20%\)/)
    expect(det.textContent).toMatch(/herdada de uma rodada anterior/)
    expect(det.textContent).toMatch(/coleta de 2026-11-12/)
    expect(det.textContent).not.toMatch(/omitiu|culpa|falha do membro|ruim|bom/i)             // sem juízo, causa ou intenção
  })

  it('cadastrado sem sessão no route server é dito como pode haver peering bilateral; sem cor de juízo', async () => {
    const { container } = montar(resposta([linha(64498, { sessao_rs: { sessoes: 0, up: 0, down: 0, incertas: 0 }, cadastrado_sem_sessao_rs: true, rejeicao: null, rejeicao_detalhe: null })]), '/ixp/fec?aba=participantes&rs=1')
    await screen.findByText('AS64498')
    fireEvent.click(screen.getByRole('button', { name: 'Detalhes de AS64498' }))
    expect(document.getElementById('part-64498')!.textContent).toMatch(/pode haver peering bilateral/)
    expect(container.innerHTML).not.toMatch(/(?:text|bg|border)-(?:ok|perigo|alerta|aviso)-\d{2,3}/)
  })

  it('nome vazio vira "sem nome na fonte", nunca o CNPJ nem o ASN repetido', async () => {
    montar(resposta([linha(61580, { nome: null })]))
    await screen.findByText('AS61580')
    expect(screen.getByText('sem nome na fonte')).toBeInTheDocument()
  })

  it('a busca espera o fim da digitação e depois pede ao servidor com `q`', async () => {
    montar(resposta([linha(64496)]))
    await screen.findByText('AS64496')
    fireEvent.change(screen.getByLabelText(/Buscar por ASN ou nome/), { target: { value: 'AS6449' } })
    expect(pedidos).toHaveLength(1)
    await waitFor(() => expect(pedidos[pedidos.length - 1]?.searchParams.get('q')).toBe('AS6449'), { timeout: 2000 })
    expect(screen.getByTestId('onde').textContent).toContain('busca=AS6449')
  })
})
