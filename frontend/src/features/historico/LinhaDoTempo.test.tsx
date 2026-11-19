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
import { fraseEvento, TIPOS_DA_PAGINA } from './rotulos'

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
  it('desenha uma miniatura por métrica com o valor mais recente e a variação', () => {
    const { container } = ver(historico)
    expect(screen.getByText('Usuários estimados (APNIC)')).toBeTruthy()
    expect(screen.getByText('140')).toBeTruthy()
    expect(screen.getByText(/\+40 desde 2026-10-29/)).toBeTruthy()
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

describe('rótulos do histórico', () => {
  it('toda frase é linguagem de evidência: sem culpa, causa nem nome de empresa, e provedor fica de fora', () => {
    expect(TIPOS_DA_PAGINA).not.toContain('provedor_novo')
    expect(TIPOS_DA_PAGINA).not.toContain('provedor_perdido')
    for (const t of TIPOS_DA_PAGINA) {
      const f = fraseEvento({ data: '2026-10-31', tipo: t, entidade: 'asn:1', chave: 'x', estado: 'confirmado' })
      expect(f, t).not.toMatch(/sequestr|hijack|ataque|culp|fraude|ilegal/i)
    }
  })
})
