// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PreviaLista, textoPrevia } from './PreviaLista'

describe('prévia de lista para quem não tem login (D9)', () => {
  it('diz quantas linhas aparecem e quantas existem, com o convite a entrar', () => {
    const entrar = vi.fn()
    render(<PreviaLista mostradas={100} total={9129} aoEntrar={entrar} />)
    expect(screen.getByTestId('previa-lista').textContent).toBe('Prévia: 100 de 9.129. Entre para ver as demais.')
    fireEvent.click(screen.getByRole('button', { name: 'Entre para ver as demais.' }))
    expect(entrar).toHaveBeenCalledTimes(1)
  })

  it('não aparece quando a lista inteira já está na tela', () => {
    const { container } = render(<PreviaLista mostradas={42} total={42} aoEntrar={() => {}} />)
    expect(container.innerHTML).toBe('')
  })

  it('o texto é o da decisão', () => expect(textoPrevia(100, 1420)).toBe('Prévia: 100 de 1.420.'))
})
