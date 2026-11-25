// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { presencaPorPtt } from './calculos'
import { distanciasPtt } from './geo'
import { BlocoInterconexao } from './BlocoInterconexao'

const JUAZEIRO: [number, number] = [-7.2258, -39.3252]
const NOMES: Record<string, string> = { ce: 'Fortaleza', cpv: 'Campina Grande', sp: 'São Paulo' }
const pttLabel = (c: string) => `${NOMES[c] ?? c} (${c})`
const pres: Record<number, { m: string[]; o: string[] }> = { 1: { m: ['ce'], o: ['cpv'] }, 2: { m: ['ce'], o: [] }, 3: { m: [], o: ['cpv'] }, 4: { m: [], o: [] } }
const ixOf = (a: number) => pres[a] ?? { m: [], o: [] }

const monta = (asns: number[]) => presencaPorPtt(asns, ixOf, JUAZEIRO, distanciasPtt(JUAZEIRO[0], JUAZEIRO[1]))

describe('bloco de interconexão no raio (PT-25 / localizador 5.1)', () => {
  it('mostra referência e mais próximo, denominador explícito, selo inferido e regra', () => {
    render(<MemoryRouter><BlocoInterconexao presenca={monta([1, 2, 3, 4])} pttLabel={pttLabel} snapshot="2026-11-22" /></MemoryRouter>)
    const b = screen.getByTestId('localizador-interconexao')
    expect(within(screen.getByTestId('ptt-referencia')).getByRole('link', { name: 'Fortaleza (ce)' })).toHaveAttribute('href', '/ixp/ce')
    expect(screen.getByTestId('ptt-referencia').textContent).toMatch(/2 de 4 redes são membros/)
    expect(screen.getByTestId('ptt-mais-proximo').textContent).toMatch(/Campina Grande \(cpv\), 3\d\d km em linha reta; 0 de 4 redes são membros/)
    expect(b.textContent).toMatch(/Participantes de algum PTT do IX\.br: 2 de 4 redes/)
    expect(b.textContent).toMatch(/com prefixos vistos em route server \(inferido; podem chegar por outro participante\): 1 de 4 redes/)
    expect(b.textContent).toMatch(/Fora do cadastro e sem prefixos vistos: 1 de 4 redes/)
    expect(b.textContent).toMatch(/inferido/)
    expect(b.textContent).toMatch(/2026-11-22/)
    expect(b.textContent).not.toMatch(/desassistid|abandon|omiti|culpa/i)
    expect(screen.getByRole('table')).toBeTruthy()
    expect(screen.getAllByRole('columnheader').every(th => th.getAttribute('scope') === 'col')).toBe(true)
  })

  it('sem nenhuma rede membro: diz isso e mantém o mais próximo; sem redes no raio não renderiza', () => {
    const { container, rerender } = render(<MemoryRouter><BlocoInterconexao presenca={monta([3, 4])} pttLabel={pttLabel} snapshot="2026-11-22" /></MemoryRouter>)
    expect(screen.getByTestId('ptt-referencia').textContent).toMatch(/nenhuma rede do raio consta como participante de PTT do IX\.br/)
    expect(screen.getByTestId('ptt-mais-proximo')).toBeTruthy()
    rerender(<MemoryRouter><BlocoInterconexao presenca={monta([])} pttLabel={pttLabel} snapshot="2026-11-22" /></MemoryRouter>)
    expect(container.textContent).toBe('')
  })
})
