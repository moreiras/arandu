// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AvisosRecorte, textoPeso } from './AvisoRecorte'

describe('AvisosRecorte (D6: aviso é rótulo, não supressão)', () => {
  it('desenha um selo neutro por aviso, com a explicação no title, e nada sem aviso', () => {
    const { container, rerender } = render(<AvisosRecorte avisos={['poucos_casos', 'maior_integrante']} />)
    expect(screen.getByTestId('aviso-poucos_casos').getAttribute('title')).toMatch(/Menos de 5 casos/)
    expect(screen.getByTestId('aviso-maior_integrante').getAttribute('title')).toMatch(/30% ou mais/)
    expect(container.innerHTML).not.toMatch(/(?:text|bg|border)-(?:ok|perigo|alerta|aviso)-\d{2,3}/)       // sem cor de juízo
    rerender(<AvisosRecorte avisos={[]} />)
    expect(container.innerHTML).toBe('')
    rerender(<AvisosRecorte />)
    expect(container.innerHTML).toBe('')
  })

  it('o peso do maior integrante sai em texto', () => {
    expect(textoPeso(0.345)).toBe('maior: 35%')
    expect(textoPeso(null)).toBeNull()
  })
})
