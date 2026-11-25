// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Componente da síntese em texto (PT-22): selo por extenso (nunca só cor), fonte e data em cada frase, limite de quatro e bloco ausente sem frases. */
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MAX_FRASES, limitar, type FraseSintese } from '../../lib/sintese'
import { SinteseTopo } from './SinteseTopo'

const f = (id: string, selo: FraseSintese['selo'] = 'fato'): FraseSintese => ({ id, selo, texto: `Frase ${id}.`, fonte: 'Fonte X', dataRef: '2026-09' })

describe('SinteseTopo', () => {
  it('cada frase mostra o selo por extenso, a fonte e a data de referência, e o bloco traz o snapshot e a versão das regras', () => {
    render(<SinteseTopo frases={[f('a', 'estimado'), f('b')]} snapshot="2026-11-22" regras="regras-x-1" />)
    const bloco = screen.getByTestId('sintese-topo')
    expect(within(bloco).getByRole('heading', { name: 'Em resumo' })).toBeInTheDocument()
    expect(bloco).toHaveTextContent('2026-11-22')
    expect(within(screen.getByTestId('sintese-a')).getByText('Estimado · Fonte X · ref. 2026-09')).toBeInTheDocument()
    expect(within(screen.getByTestId('sintese-b')).getByText('Fato · Fonte X · ref. 2026-09')).toBeInTheDocument()
    expect(bloco).toHaveTextContent('regras-x-1')
    expect(bloco).toHaveTextContent('descrevem, não explicam causas')
  })

  it('no máximo quatro frases; com menos que o mínimo o bloco não aparece', () => {
    const { rerender, container } = render(<SinteseTopo frases={['a', 'b', 'c', 'd', 'e', 'f'].map((i) => f(i))} regras="r" />)
    expect(screen.getAllByTestId(/^sintese-[a-f]$/)).toHaveLength(MAX_FRASES)
    rerender(<SinteseTopo frases={[f('a')]} regras="r" />)
    expect(container).toBeEmptyDOMElement()
    rerender(<SinteseTopo frases={[]} regras="r" />)
    expect(container).toBeEmptyDOMElement()
  })

  it('região ao vivo só quando pedida (localizador)', () => {
    const { rerender } = render(<SinteseTopo frases={[f('a'), f('b')]} regras="r" />)
    expect(screen.getByTestId('sintese-topo')).not.toHaveAttribute('role')
    rerender(<SinteseTopo frases={[f('a'), f('b')]} regras="r" aoVivo />)
    expect(screen.getByTestId('sintese-topo')).toHaveAttribute('aria-live', 'polite')
  })
})

describe('limitar', () => {
  it('descarta frases falsas e ids repetidos, corta em quatro e some com menos de duas', () => {
    expect(limitar([false, null, undefined, f('a')])).toEqual([])
    expect(limitar([f('a'), f('a'), false, f('b')]).map((x) => x.id)).toEqual(['a', 'b'])
    expect(limitar(['a', 'b', 'c', 'd', 'e'].map((i) => f(i))).map((x) => x.id)).toEqual(['a', 'b', 'c', 'd'])
  })
})
