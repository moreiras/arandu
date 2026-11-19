// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurapé.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BarrasRecorte, recortesDaColuna } from './BarrasRecorte'
import type { CeticLinha } from '../../types/api'

const l = (dimensao: string, recorte: string, item: string, resposta: string, p: number | null, mp: number | null, t = 1000): CeticLinha =>
  ({ tabela: 'A1', titulo_tabela: 'x', dimensao, recorte, item, resposta, proporcao: p, margem_proporcao: mp, total: t, margem_total: 50 })
const LINHAS = [l('Total', 'Total', '', 'Sim', 88.5, 1.2), l('Região', 'Norte', '', 'Sim', 80, 3), l('Região', 'Sul', '', 'Sim', 92, 2), l('Região', 'Sul', '', 'Não', 8, 2), l('Total', 'Total', 'Item', 'Sim', 50, 1)]

describe('BarrasRecorte', () => {
  it('pega os recortes de uma coluna, na ordem da planilha, sem repetir', () => {
    expect(recortesDaColuna(LINHAS, 'Sim', 'proporcao').map((r) => `${r.dimensao}:${r.recorte}`)).toEqual(['Total:Total', 'Região:Norte', 'Região:Sul'])
    expect(recortesDaColuna(LINHAS, 'Item — Sim', 'total')[0].valor).toBe(1000)
  })
  it('uma barra por recorte com o valor e a margem acessíveis, agrupada pela dimensão, sem ranking', () => {
    render(<BarrasRecorte recortes={recortesDaColuna(LINHAS, 'Sim', 'proporcao')} medida="proporcao" coluna="Sim" />)
    expect(screen.getByRole('img', { name: /Norte: 80,0%, margem de 3,0%/ })).toBeTruthy()
    expect(screen.getByText('Região')).toBeTruthy()
    expect(screen.queryByText(/melhor|pior/i)).toBeNull()
    expect(screen.getByText(/Ordem da planilha, sem ranking/)).toBeTruthy()
  })
  it('coluna sem valor avisa em vez de desenhar vazio', () => {
    render(<BarrasRecorte recortes={[{ dimensao: 'Total', recorte: 'Total', valor: null, margem: null }]} medida="total" coluna="x" />)
    expect(screen.getByText(/não tem valor publicado/)).toBeTruthy()
  })
})
