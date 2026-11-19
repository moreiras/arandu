// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import docBase from '../../../test/fixtures/asn_detail.json'
import type { AsnRelacoes, TransitoAsn } from '../../../types/api'
import { RelacoesBloco } from './RelacoesBloco'

vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} })
vi.mock('../../../components/graphs/ASRelationsGraph', () => ({ ASRelationsGraph: () => <div data-testid="grafo" /> }))

const rel: AsnRelacoes = {
  algoritmo: 'ARC v1',
  provedores: [
    { asn: 64510, nome: 'Trânsito Exemplo', p: 0.97, nivel: 'confirmado', afi: ['v4', 'v6'] },
    { asn: 64511, p: 0.55, nivel: 'possivel', afi: ['v4'] },
  ],
  clientes: [{ asn: 64520, p: 0.9, nivel: 'provavel', afi: ['v4'] }],
  pares: [], irmaos: [], sem_classificacao: [],
  n_provedores: { v4: 1, v6: 1 },
  visibilidade: { v4: { vps: 5, ptts: 3, coletores: true }, v6: { vps: 0, ptts: 1, coletores: true } },
  multihomed: { v4: false, v6: null },
  single_homed: { v4: true, v6: null },
}

function ver(relacoes?: AsnRelacoes, transito?: TransitoAsn) {
  const doc: any = { ...docBase, relacoes }
  return render(<MemoryRouter><RelacoesBloco dados={{ doc, transito, date: '2026-09-20', ixpPaths: {}, pathNodeMeta: {}, ixpMemberCodes: [], carregandoCaminhos: false }} snapshot="2026-09-20" /></MemoryRouter>)
}

describe('RelacoesBloco', () => {
  it('mostra provedores com nível e probabilidade, e a situação por família sem afirmar o que é indeterminado', () => {
    ver(rel)
    expect(screen.getByText('Provedores')).toBeTruthy()
    expect(screen.getByText('AS64510').getAttribute('href')).toBe('/asn/64510')
    expect(screen.getByText('Trânsito Exemplo')).toBeTruthy()
    expect(screen.getByText('97%')).toBeTruthy()
    expect(screen.getByText('confirmado')).toBeTruthy()
    expect(screen.getByText('possível')).toBeTruthy()
    expect(screen.getByText('IPv4: um só provedor inferido')).toBeTruthy()
    expect(screen.getByText('IPv6: indeterminado (pouca visibilidade)')).toBeTruthy()
  })

  it('vista em tabela: todos os papéis num quadro, com filtro por papel e ordenação, mesmos níveis das listas', () => {
    ver(rel)
    expect(screen.queryByRole('table', { name: 'Relações do AS em tabela' })).toBeNull()        // a vista padrão continua sendo a de listas
    fireEvent.click(screen.getByRole('button', { name: 'Tabela' }))
    const t = screen.getByRole('table', { name: 'Relações do AS em tabela' })
    expect(within(t).getAllByRole('row')).toHaveLength(1 + 3)                                  // cabeçalho + 2 provedores + 1 cliente
    expect(within(t).getByText('Cliente')).toBeTruthy()
    expect(within(t).getByRole('link', { name: 'AS64510' }).getAttribute('href')).toBe('/asn/64510')
    expect(within(t).getAllByRole('row')[1].textContent).toContain('AS64510')                   // confiança 97% primeiro
    fireEvent.change(screen.getByLabelText('Papel'), { target: { value: 'cliente' } })
    expect(within(screen.getByRole('table', { name: 'Relações do AS em tabela' })).getAllByRole('row')).toHaveLength(2)
    fireEvent.change(screen.getByLabelText('Papel'), { target: { value: 'par' } })
    expect(screen.getByText(/Nenhuma relação com esse papel/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Listas' }))
    expect(screen.getByText('Provedores')).toBeTruthy()
  })

  it('rebaixados por estrato mostram o rótulo composto e a probabilidade calibrada', () => {
    const r: AsnRelacoes = { ...rel, provedores: [
      { asn: 64530, p: 0.6, nivel: 'possivel', afi: ['v4'], estrato: 'sem_evidencia', p_calibrada: 0.02 },
      { asn: 64531, p: 0.6, nivel: 'possivel', afi: ['v4'], estrato: 'conflito', p_calibrada: null },
      { asn: 64532, p: 0.9, nivel: 'provavel', afi: ['v4'], estrato: 'ambos', p_calibrada: 0.92 },
      { asn: 64533, p: 0.99, nivel: 'declarado', afi: ['v4'], estrato: 'sem_evidencia' },
    ] }
    ver(r)
    expect(screen.getByText('possível · sem confirmação')).toBeTruthy()
    expect(screen.getByText('possível · fontes divergem')).toBeTruthy()
    expect(screen.getByText('declarado')).toBeTruthy()          // nível acima de possível mantém o selo do nível
    expect(screen.getAllByTestId('p-calibrada').map((e) => e.textContent)).toEqual(['calibrada 2%', 'calibrada 92%'])  // null não mostra
    expect(screen.getByTestId('como-ler-niveis').textContent).toMatch(/só o ASPA é referência independente/)
  })

  it('D7: o grafo desenha provedores e clientes inferidos; os vizinhos observados ficam na lista recolhida', () => {
    ver(rel)
    expect(screen.getByRole('heading', { name: 'Provedores e clientes' })).toBeTruthy()
    expect(screen.getByText('Vizinhos observados no AS_PATH (sem classificar)')).toBeTruthy()
    expect(screen.getByText(/não indica provedor ou cliente/)).toBeTruthy()
    expect(screen.getAllByTestId('grafo').length).toBe(2)
  })

  it('snapshot sem relações inferidas: grafos vazios e os vizinhos observados continuam disponíveis', () => {
    ver(undefined)
    expect(screen.queryByText('Provedores')).toBeNull()
    expect(screen.getByTestId('vizinhos-observados')).toBeTruthy()
    expect(screen.getAllByTestId('grafo').length).toBe(2)
  })

  it('ARC v2: complexas com o papel em cada família, mudança pendente, e o aviso de calibração', () => {
    const v2: AsnRelacoes = {
      ...rel, algoritmo: 'ARC v2', p_calibrada: { v4: false, v6: false },
      provedores: [{ asn: 64510, p: 0.97, nivel: 'confirmado', afi: ['v4'], mudanca_pendente: true }],
      complexas: [{ asn: 64530, nome: 'Híbrido SA', p: 0.85, nivel: 'provavel', afi: ['v4', 'v6'], subtipo: 'hibrida', v4: 'provedor', v6: 'par' }],
    }
    ver(v2)
    expect(screen.getByText('mudança pendente')).toBeTruthy()
    expect(screen.getByTestId('relacoes-complexas').textContent).toContain('IPv6: par · IPv4: provedor')
    expect(screen.getByText('híbrida')).toBeTruthy()
    expect(screen.getByText(/probabilidade ainda NÃO calibrada/)).toBeTruthy()
  })

  it('cone de clientes com ressalva de inferência, e a ausência de cliente não vira afirmação', () => {
    const t: TransitoAsn = { snapshot_date: '2026-11-05', limites: 'Inferência sobre inferência.', asn: 64510, com_cliente: true, clientes_diretos: 3, cone_asns: 12, cone_br: 10, cone_usuarios: 5000, cone_ufs: { ES: 6, SP: 4 }, irmaos_excluidos: 0, posicao_cone_br: 7 }
    const { unmount } = ver({ ...rel, algoritmo: 'ARC v2' }, t)
    expect(screen.getByTestId('cone-transito').textContent).toContain('cone de 12 ASN(s), 10 do Brasil')
    expect(screen.getByTestId('cone-transito').textContent).toContain('ES 6 · SP 4')
    expect(screen.getByTestId('cone-transito').textContent).toContain('Inferência sobre relações inferidas')
    unmount()
    ver({ ...rel, algoritmo: 'ARC v2' }, { ...t, com_cliente: false, cone_asns: 0, cone_br: 0, cone_ufs: {} })
    expect(screen.getByText(/não quer dizer que o AS não tenha clientes/)).toBeTruthy()
  })
})
