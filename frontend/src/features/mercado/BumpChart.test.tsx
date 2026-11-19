// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurapé.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { BumpChart } from './BumpChart'

describe('BumpChart', () => {
  it('desenha uma linha por trecho contínuo e quebra onde não há posição', () => {
    const { container, getByTestId } = render(<BumpChart meses={['2026-01', '2026-02', '2026-03', '2026-04']} series={[
      { id: 'a', nome: 'Alfa', posicao: [1, 1, 2, 2] },
      { id: 'b', nome: 'Beta', posicao: [2, null, null, 1] }]} />)
    expect(getByTestId('bump').getAttribute('aria-label')).toMatch(/2 maiores operadoras.*2026-01 a 2026-04/)
    expect(container.querySelectorAll('polyline')).toHaveLength(1)        // Beta só tem trechos de 1 ponto (sem linha); Alfa tem um trecho
    expect(container.textContent).toContain('Alfa')
    expect(container.textContent).toContain('Beta')
  })
  it('rótulo longo é cortado e não há legenda separada', () => {
    const { container } = render(<BumpChart meses={['2026-01', '2026-02']} series={[{ id: 'a', nome: 'EMPRESA COM UM NOME MUITO LONGO LTDA', posicao: [1, 1] }]} />)
    expect(container.textContent).toContain('…')
  })
})
