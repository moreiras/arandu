// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** ROAs de uma CDN: resumo agregado à vista e a lista (que passa de mil linhas) recolhida. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { RoaTable } from './componentes'

const roas = [
  { prefix: '104.16.0.0/13', maxLength: 13, ta: 'arin' }, { prefix: '104.24.0.0/14', maxLength: 24, ta: 'arin' },
  { prefix: '2606:4700::/32', maxLength: 48, ta: 'ripencc' }, { prefix: '172.64.0.0/13', maxLength: 13, ta: 'arin' },
]

describe('ROAs agregados', () => {
  it('mostra contagem por trust anchor e por maxLength, com a lista dentro de um bloco recolhido', () => {
    render(<RoaTable title="RPKI: ROAs autorizados" accent="#000" roaList={roas as never} />)
    expect(screen.getByTestId('roa-agregado')).toHaveTextContent('ARIN: 3 · RIPENCC: 1 · maxLength igual ao prefixo: 2 · maxLength maior que o prefixo: 2')
    const detalhe = screen.getByText(/Ver a lista dos 4 ROAs/).closest('details')!
    expect(detalhe.open).toBe(false)
    expect(detalhe).toHaveTextContent('104.16.0.0/13')
  })

  it('sem ROA, só o estado vazio', () => {
    render(<RoaTable title="t" accent="#000" roaList={[]} />)
    expect(screen.getByText('Nenhum ROA encontrado')).toBeInTheDocument()
    expect(screen.queryByTestId('roa-agregado')).toBeNull()
  })
})
