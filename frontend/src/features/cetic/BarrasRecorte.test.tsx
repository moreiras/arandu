// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurapé.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BarrasRecorte, recortesDaColuna } from './BarrasRecorte'
import type { CeticLinha } from '../../types/api'
import { estadoMargem } from './margem'

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
  it('margem zero com proporção entre 0 e 100 não vira "±0,0"; margem de metade do valor ou mais é precisão baixa (USO-E1)', () => {
    render(<BarrasRecorte recortes={[{ dimensao: 'Total', recorte: 'Total', valor: 43.61, margem: 0 }, { dimensao: 'Região', recorte: 'Sul', valor: 2.07, margem: 2.67 },
      { dimensao: 'Região', recorte: 'Norte', valor: 88.5, margem: 2.5 }]} medida="proporcao" coluna="Sim" />)
    expect(screen.queryByText(/±0,0/)).toBeNull()
    expect(screen.getByRole('img', { name: /Total: 43,6%, margem de erro registrada como zero na planilha do Cetic\.br/ })).toBeTruthy()
    expect(screen.getByRole('img', { name: /Sul: 2,1%, margem de 2,7%, precisão baixa/ })).toBeTruthy()
    expect(screen.getByText(/±2,5%/)).toBeTruthy()
  })
  it('regras da margem: zero com valor 0 ou 100 é zero de fato; sem margem não diz nada', () => {
    expect(estadoMargem(43.61, 0, 'proporcao')).toBe('zero_registrado')
    expect(estadoMargem(0, 0, 'proporcao')).toBe('normal')
    expect(estadoMargem(100, 0, 'proporcao')).toBe('normal')
    expect(estadoMargem(50, null, 'proporcao')).toBe('sem')
    expect(estadoMargem(0.21, 0.42, 'proporcao')).toBe('precisao_baixa')
    expect(estadoMargem(88.5, 2.5, 'proporcao')).toBe('normal')
    expect(estadoMargem(1000, 0, 'total')).toBe('normal')
  })
})
