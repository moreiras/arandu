// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** S.A. no agrupamento (P8): rótulo, grupo do SICI ao lado e o limite no "Como ler". */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SemInferenciaSA, SeloSA } from './SemInferenciaSA'

describe('S.A. sem inferência pelo quadro societário', () => {
  it('rótulo e Como ler; sem grupoSici, a página do grupo não afirma "nenhum"', () => {
    render(<SemInferenciaSA />)
    expect(screen.getByTestId('grupo-nao-inferivel')).toHaveTextContent('grupo não inferível pelo quadro societário (S.A.)')
    expect(screen.getByTestId('grupo-nao-inferivel')).not.toHaveTextContent('SICI')
    expect(screen.getByTestId('como-ler')).toHaveTextContent('diretoria e conselho, não acionistas')
  })

  it('com o grupo do SICI ao lado, ou "nenhum" quando a Anatel registra OUTROS', () => {
    const { unmount } = render(<SemInferenciaSA grupoSici="OI" />)
    expect(screen.getByTestId('grupo-nao-inferivel')).toHaveTextContent('grupo declarado ao SICI: OI')
    unmount()
    render(<SemInferenciaSA grupoSici="OUTROS" />)
    expect(screen.getByTestId('grupo-nao-inferivel')).toHaveTextContent('grupo declarado ao SICI: nenhum')
  })

  it('selo curto de listas', () => {
    render(<SeloSA />)
    expect(screen.getByTestId('selo-sa')).toHaveTextContent('S.A.: quadro societário não informa acionistas')
  })
})
