// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { HistoricoBloco } from '../../types/api'
import { LinhaDoTempo } from './LinhaDoTempo'
import { fraseEvento, inicioDosSnapshots, TIPOS_DA_PAGINA } from './rotulos'

const historico: HistoricoBloco = {
  completo: true, snapshots_com_historico: 3, colunas: ['users', 'p4', 'n_roa'],
  serie: [{ date: '2026-10-29', users: 100, p4: 10, n_roa: 0 }, { date: '2026-10-30', users: 150, p4: 12, n_roa: 2 }, { date: '2026-10-31', users: 140, p4: 12, n_roa: 2 }],
  eventos: [
    { data: '2026-10-30', tipo: 'roa_ganho', entidade: 'asn:64500', chave: '', estado: 'confirmado' },
    { data: '2026-10-31', tipo: 'mudanca_origem', entidade: 'prefixo:198.18.24.0/21', chave: '64503', de: 64502, para: 64503, estado: 'pendente', destaque: true },
  ],
  eventos_total: 2,
}
const ver = (h?: HistoricoBloco | null, escopo: 'asn' | 'ixp' | 'operadora' | 'uf' = 'asn') =>
  render(<MemoryRouter><LinhaDoTempo historico={h} escopo={escopo} /></MemoryRouter>)

describe('LinhaDoTempo', () => {
  it('desenha uma miniatura por métrica com o valor mais recente, a data e, sem anotação da API, nenhuma variação', () => {
    const { container } = ver(historico)
    const cartao = screen.getAllByTestId('linha-do-tempo-metrica')[0]
    expect(cartao.textContent).toMatch(/Usuários estimados \(APNIC\)140em 2026-10-31/)
    expect(screen.queryByTestId('linha-do-tempo-variacao')).toBeNull()
    expect(container.querySelectorAll('svg').length).toBe(3)
    expect(screen.getByText(/3 snapshots com histórico, de 2026-10-29 a 2026-10-31/)).toBeTruthy()
  })

  it('lista os eventos como diferença observada, com o estado e o destaque de RPKI inválido', () => {
    ver(historico)
    expect(screen.getByText('Passou a ter ROA')).toBeTruthy()
    expect(screen.getByText(/Prefixo 198\.18\.24\.0\/21: origem mudou de AS64502 para AS64503/)).toBeTruthy()
    expect(screen.getByText('em confirmação')).toBeTruthy()
    expect(screen.getByText(/novo estado: RPKI inválido/)).toBeTruthy()
    expect(screen.getByText(/sem causa atribuída/)).toBeTruthy()
  })

  it('sem histórico mostra uma explicação, não um erro', () => {
    ver(null)
    expect(screen.getByText(/Ainda não há histórico guardado/)).toBeTruthy()
    expect(document.body.textContent).not.toMatch(/outubro de 2026/)
    ver({ ...historico, serie: [] })
  })

  it('o anônimo é avisado de que vê só os 2 snapshots mais recentes', () => {
    ver({ ...historico, completo: false, serie: historico.serie.slice(1) })
    expect(screen.getByText(/só os 2 snapshots mais recentes/)).toBeTruthy()
    expect(screen.getByText(/\(3 existem\)/)).toBeTruthy()
  })

  it('um único ponto não quebra o desenho', () => {
    const { container } = ver({ ...historico, serie: [historico.serie[0]], eventos: [], eventos_total: 0 })
    expect(container.querySelectorAll('circle').length).toBe(3)
    expect(screen.getByText(/Nenhuma mudança observada/)).toBeTruthy()
  })
})

describe('LinhaDoTempo com a regra de comparabilidade (PT-28)', () => {
  const regra = { versao: 1, min_pontos_linha: 4, motivos: { data_atipica: 'um dos pontos está numa data atípica marcada', ausente: 'falta a medida em um dos pontos' }, texto: ['Variação só entre pontos comparáveis.'] }
  const pontos = (flags: Array<boolean | null>) => flags.map((f, i) => ({ date: `2026-10-0${i + 1}`, comparavel_com_anterior: f, motivos: f === false ? ['data_atipica'] : [] }))
  const base = (metricas: HistoricoBloco['metricas'], n: number): HistoricoBloco => ({
    completo: true, snapshots_com_historico: n, colunas: ['users'], regra, metricas,
    serie: Array.from({ length: n }, (_, i) => ({ date: `2026-10-0${i + 1}`, users: 100 + i })), eventos: [], eventos_total: 0,
  })

  it('variação calculada aparece com o intervalo; a linha só liga trechos com 4 pontos comparáveis', () => {
    const m = { id: 'users', desenhar_linha: true, segmentos: [[0, 1, 2, 3]], pontos: pontos([null, true, true, true]), variacao: { de: '2026-10-01', para: '2026-10-04', calculada: true, absoluta: 3, unidade: 'absoluta', pct: 3, motivos: [] } }
    const { container } = ver(base([m], 4))
    expect(screen.getByTestId('linha-do-tempo-variacao').textContent).toBe('+3 entre 2026-10-01 e 2026-10-04')
    expect(container.querySelectorAll('polyline').length).toBe(1)
  })

  it('série curta fica só em pontos, sem linha, e a variação não calculada traz o motivo, nunca zero', () => {
    const m = { id: 'users', desenhar_linha: false, segmentos: [[0], [1, 2]], pontos: pontos([null, false, true]), variacao: { de: '2026-10-01', para: '2026-10-03', calculada: false, absoluta: null, unidade: null, pct: null, motivos: ['data_atipica'] } }
    const { container } = ver(base([m], 3))
    expect(container.querySelectorAll('polyline').length).toBe(0)
    expect(container.querySelectorAll('line[stroke-dasharray="3 3"]').length).toBe(1)
    expect(screen.getByTestId('linha-do-tempo-variacao').textContent).toMatch(/Variação não calculada entre 2026-10-01 e 2026-10-03: um dos pontos está numa data atípica marcada/)
  })

  it('traz o "Como ler" da regra, a tabela dos mesmos números e a marca de data atípica no evento', () => {
    const h = base([], 3)
    h.eventos = [{ data: '2026-10-02', tipo: 'roa_perdido', entidade: 'asn:1', chave: '', estado: 'confirmado', atipico: 'campo ausente' }]
    h.eventos_total = 1
    ver(h)
    expect(screen.getByText('Variação só entre pontos comparáveis.')).toBeTruthy()
    expect(screen.getByTestId('ver-dados')).toBeTruthy()
    expect(screen.getByText('data atípica marcada')).toBeTruthy()
  })
})

describe('rótulos do histórico', () => {
  it('toda frase é linguagem de evidência: sem culpa, causa nem nome de empresa, e provedor fica de fora', () => {
    expect(TIPOS_DA_PAGINA).not.toContain('provedor_novo')
    expect(TIPOS_DA_PAGINA).not.toContain('provedor_perdido')
    for (const t of TIPOS_DA_PAGINA) {
      const f = fraseEvento({ data: '2026-10-31', tipo: t, entidade: 'asn:1', chave: 'x', estado: 'confirmado' })
      expect(f, t).not.toMatch(/sequestr|hijack|ataque|culp|fraude|ilegal/i)
    }
  })

  it('a data inicial é a do primeiro snapshot da lista, não uma data fixa', () => {
    expect(inicioDosSnapshots(['2026-11-22', '2026-06-28', '2026-11-15'])).toBe('28/06/2026')
    expect(inicioDosSnapshots(['2027-01-03'])).toBe('03/01/2027')
    expect(inicioDosSnapshots([])).toBe('')
    expect(inicioDosSnapshots(undefined)).toBe('')
  })
})
