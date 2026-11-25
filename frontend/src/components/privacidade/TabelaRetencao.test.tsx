// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TabelaRetencao } from './TabelaRetencao'
import retencao from '../../lib/retencao.gen.json'
import { Privacidade } from '../../pages/Privacidade'

describe('TabelaRetencao (D10)', () => {
  it('mostra uma linha por registro do JSON gerado, com prazo e indicação de IP', () => {
    render(<TabelaRetencao />)
    expect(screen.getAllByRole('row')).toHaveLength(retencao.linhas.length + 1)
    for (const l of retencao.linhas) {
      expect(screen.getByText(l.registro)).toBeTruthy()
      expect(screen.getByText(l.prazo)).toBeTruthy()
    }
  })

  it('a página /privacidade não exibe a tabela enquanto o mantenedor não liga a flag', () => {
    render(<Privacidade />)
    expect(screen.queryByText('Registros e prazos de retenção')).toBeNull()
  })
})
