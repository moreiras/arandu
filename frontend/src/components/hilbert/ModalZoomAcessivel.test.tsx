// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it } from 'vitest'
import { V6_BLOCKS } from './hilbert'
import { ZoomModalDashV4, ZoomModalV6 } from './IXPHilbertZoom'
import { ModalAcessivel } from '../ui/ModalAcessivel'

const lacnic = V6_BLOCKS.find((b) => b.id === 'lacnic')!

function Abridor({ children }: { children: (fechar: () => void) => React.ReactNode }) {
  const [aberto, setAberto] = useState(false)
  return (
    <QueryClientProvider client={new QueryClient()}>
      <button type="button" onClick={() => setAberto(true)}>abrir zoom</button>
      {aberto && children(() => setAberto(false))}
    </QueryClientProvider>
  )
}

const zoomV6 = (fechar: () => void) => (
  <ZoomModalV6 config={lacnic} gx={0} gy={0} allCells={[1, 2, 3]} ownCells={null} thirdCells={null} isPeerMode={false} color="#0891b2" onClose={fechar} />
)

describe('modal de zoom da curva de Hilbert (acessibilidade)', () => {
  it('ZoomModalV6: role, aria-modal, nome pelo título, foco inicial dentro, Esc fecha e o foco volta', () => {
    render(<Abridor>{zoomV6}</Abridor>)
    const abridor = screen.getByRole('button', { name: 'abrir zoom' })
    abridor.focus()
    fireEvent.click(abridor)
    const dialogo = screen.getByRole('dialog')
    expect(dialogo).toHaveAttribute('aria-modal', 'true')
    const titulo = dialogo.getAttribute('aria-labelledby')
    expect(titulo).toBeTruthy()
    expect(document.getElementById(titulo!)?.tagName).toBe('H3')
    expect(dialogo).toHaveAccessibleName(document.getElementById(titulo!)!.textContent!)
    expect(dialogo.contains(document.activeElement)).toBe(true)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(document.activeElement).toBe(abridor)
  })

  it('ZoomModalV6: o botão de fechar tem nome acessível e fecha', () => {
    render(<Abridor>{zoomV6}</Abridor>)
    fireEvent.click(screen.getByRole('button', { name: 'abrir zoom' }))
    fireEvent.click(screen.getByRole('button', { name: 'Fechar' }))
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('ZoomModalDashV4 também é um diálogo modal com título', () => {
    render(
      <Abridor>
        {(fechar) => <ZoomModalDashV4 sx={0} sy={0} slashEight={0} activeLayer="rir_br" layerColor="#3b82f6" density={new Array(65536).fill(0)} semDetalhe onClose={fechar} />}
      </Abridor>,
    )
    fireEvent.click(screen.getByRole('button', { name: 'abrir zoom' }))
    const dialogo = screen.getByRole('dialog')
    expect(dialogo).toHaveAttribute('aria-modal', 'true')
    expect(dialogo).toHaveAccessibleName(/\/8$/)
  })
})

describe('ModalAcessivel: foco preso', () => {
  function Exemplo({ onClose = () => {} }: { onClose?: () => void }) {
    return (
      <>
        <button type="button">fora</button>
        <ModalAcessivel idTitulo="t" onClose={onClose}>
          <h3 id="t">Título</h3>
          <button type="button">primeiro</button>
          <button type="button">último</button>
        </ModalAcessivel>
      </>
    )
  }

  it('Tab no último volta ao primeiro e Shift+Tab no primeiro vai ao último', () => {
    render(<Exemplo />)
    const primeiro = screen.getByRole('button', { name: 'primeiro' })
    const ultimo = screen.getByRole('button', { name: 'último' })
    expect(document.activeElement).toBe(primeiro)
    ultimo.focus()
    fireEvent.keyDown(document, { key: 'Tab' })
    expect(document.activeElement).toBe(primeiro)
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(ultimo)
  })

  it('foco que escapou para fora é trazido de volta', () => {
    render(<Exemplo />)
    screen.getByRole('button', { name: 'fora' }).focus()
    fireEvent.keyDown(document, { key: 'Tab' })
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'primeiro' }))
  })

  it('Esc chama onClose uma vez', () => {
    let n = 0
    render(<Exemplo onClose={() => { n++ }} />)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(n).toBe(1)
  })
})
