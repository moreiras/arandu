// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { TransitoUfBloco } from './TransitoUfBloco'
import type { UfCtx } from '../contexto'
import type { TransitoUf } from '../../../types/api'

const t: TransitoUf = {
  snapshot_date: '2026-11-05', limites: 'Inferência (ARC v2); UF = sede da organização.', uf: 'ES', asns_br: 120, asns_com_provedor: 90, pct_com_provedor: 75, elos_provedor: 140,
  provedores_distintos: 30, hhi_clientes: 1800, top1_share: 0.31, top3_share: 0.55, share_provedores_estrangeiros: 0.12,
  provedores: [{ asn: 64510, nome: 'Trânsito Exemplo', br: true, clientes_uf: 44, usuarios_uf: 120000, share_clientes: 0.31, share_usuarios: 0.4 },
    { asn: 3356, nome: 'Level3', br: false, clientes_uf: 10, usuarios_uf: 1000, share_clientes: 0.07, share_usuarios: 0.01 }],
}

describe('bloco trânsito da UF', () => {
  it('mostra a concentração e os provedores como inferência, com o exterior rotulado', () => {
    render(<MemoryRouter><TransitoUfBloco dados={{ uf: 'ES', transito: t } as UfCtx} snapshot={null} /></MemoryRouter>)
    expect(screen.getByTestId('transito-uf').textContent).toContain('90 de 120 ASNs com sede na UF têm provedor inferido (75%)')
    expect(screen.getByTestId('transito-uf').textContent).toContain('HHI 1.800')
    expect(screen.getByText('AS64510').getAttribute('href')).toBe('/asn/64510')
    expect(screen.getByText(/exterior/)).toBeTruthy()
    expect(screen.getByText(/Inferência \(ARC v2\) no snapshot 2026-11-05/)).toBeTruthy()
  })

  it('não renderiza nada sem o produto', () => {
    const { container } = render(<MemoryRouter><TransitoUfBloco dados={{ uf: 'ES' } as UfCtx} snapshot={null} /></MemoryRouter>)
    expect(container.innerHTML).toBe('')
  })
})
