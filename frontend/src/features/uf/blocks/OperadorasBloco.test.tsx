// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Operadoras da UF: padrão = presentes na UF com acessos na UF; a lista de sediadas fica na outra visão (UF-E2). */
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { OperadorasBloco } from './OperadorasBloco'
import type { UfCtx } from '../contexto'

const presente = (cnpj: string, empresa: string, acessos: number, share: number, uf_sede: string) =>
  ({ cnpj, empresa, razao_social: empresa, uf_sede, acessos, share, municipios: 3, acessos_brasil: acessos * 50, asns: [] })
const dados = {
  uf: 'AM',
  operadorasPresentes: [presente('40432544000147', 'CLARO', 179458, 24.77, 'SP'), presente('11111111000191', 'CLICK IP', 113148, 15.62, 'AM')],
  operadorasPresentesTotal: 211,
  operadoras: [{ cnpj: '11111111000191', empresa: 'CLICK IP', razao_social: 'CLICK IP', acessos: 44803, municipios: 25 }],
  operadorasTotal: 141,
} as unknown as UfCtx

describe('OperadorasBloco da UF (UF-E2)', () => {
  it('abre nas presentes, com acessos e parcela na UF, e alterna para as sediadas', () => {
    render(<MemoryRouter><OperadorasBloco dados={dados} snapshot={null} /></MemoryRouter>)
    expect(screen.getByRole('button', { name: 'Presentes na UF (211)' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByText('CLARO')).toBeInTheDocument()
    expect(screen.getByText('179.458')).toBeInTheDocument()
    expect(screen.getByText('24,8%')).toBeInTheDocument()
    expect(screen.getByText(/Mostrando as 2 maiores de 211/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Com sede na UF (141)' }))
    expect(screen.queryByText('CLARO')).toBeNull()
    expect(screen.getByText('44.803')).toBeInTheDocument()
    expect(screen.getByText(/declarados em todo o país/)).toBeInTheDocument()
  })

  it('snapshot servido sem `operadoras_presentes`: só a lista de sediadas, sem alternância', () => {
    render(<MemoryRouter><OperadorasBloco dados={{ ...dados, operadorasPresentes: [], operadorasPresentesTotal: 0 } as UfCtx} snapshot={null} /></MemoryRouter>)
    expect(screen.queryByRole('button')).toBeNull()
    expect(screen.getByText('CLICK IP')).toBeInTheDocument()
  })
})
