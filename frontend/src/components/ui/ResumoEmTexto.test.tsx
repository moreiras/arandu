// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ResumoEmTexto } from './ResumoEmTexto'

describe('ResumoEmTexto: link depois da frase', () => {
  it('a frase com link ganha o link logo depois do texto; as demais seguem sem link', () => {
    render(
      <MemoryRouter>
        <ResumoEmTexto regras="t-1" frases={[
          { id: 'a', texto: 'Primeira frase.', selo: 'fato', fonte: 'f' },
          { id: 'b', texto: 'Segunda frase.', selo: 'fato', fonte: 'f', link: { to: '/operadoras?visao=ranking&uf=AM', rotulo: 'Ver o ranking completo da UF' } },
        ]} />
      </MemoryRouter>,
    )
    expect(within(screen.getByTestId('frase-a')).queryByRole('link')).toBeNull()
    const link = within(screen.getByTestId('frase-b')).getByRole('link', { name: 'Ver o ranking completo da UF' })
    expect(link).toHaveAttribute('href', '/operadoras?visao=ranking&uf=AM')
  })
})
