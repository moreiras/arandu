// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurapé.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BulletPrestadoras, numeroDaReferencia } from './BulletPrestadoras'
import type { QualIndicador } from '../../types/api'

const ind = (sup: string | null, inf: string | null): QualIndicador => ({ servico: 'Banda Larga Fixa', codigo: 'IND4', descricao: 'x', tipo: 'IQS', grupo: 'g', unidade: '%', referencia_superior: sup, referencia_inferior: inf })

describe('BulletPrestadoras', () => {
  it('lê a referência numérica e rejeita texto', () => {
    expect(numeroDaReferencia('90%')).toBe(90)
    expect(numeroDaReferencia('1,5')).toBe(1.5)
    expect(numeroDaReferencia('maior que 3')).toBeNull()
    expect(numeroDaReferencia(null)).toBeNull()
  })
  it('uma linha por prestadora, na ordem dada, com valor acessível e sem veredito', () => {
    render(<BulletPrestadoras indicador={ind('90%', '60%')} linhas={[{ prestadora: 'A', valor: 95 }, { prestadora: 'B', valor: null }]} />)
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    expect(screen.getByRole('img', { name: /A: 95 %/ })).toBeTruthy()
    expect(screen.getByRole('img', { name: /B: sem valor/ })).toBeTruthy()
    expect(screen.getByText(/inferior 60, superior 90/)).toBeTruthy()
    expect(screen.queryByText(/melhor|pior/i)).toBeNull()
  })
  it('sem referência numérica avisa e não quebra', () => {
    render(<BulletPrestadoras indicador={ind(null, null)} linhas={[{ prestadora: 'A', valor: 3 }]} />)
    expect(screen.getByText(/não tem referência numérica/)).toBeTruthy()
  })
})
