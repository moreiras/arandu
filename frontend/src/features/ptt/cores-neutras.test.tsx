// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { PctCell } from './ui'
import { IndicadoresAsBloco } from './blocks/IndicadoresAsBloco'
import { PotencialBloco } from './blocks/PotencialBloco'

/** Cor de juízo = verde, amarelo, laranja ou vermelho que diz "bom" ou "ruim" (IXP-E10, política editorial). */
const COR_DE_JUIZO = /(?:text|bg|border)-(?:ok|perigo|alerta|aviso)-\d{2,3}/

describe('PTT sem cores de juízo (PT-17 / IXP-E10)', () => {
  it('PctCell tem cor única em qualquer percentual', () => {
    for (const v of [0, 5, 15, 45, 99.5, null]) {
      const { container, unmount } = render(<PctCell label="Cobertura" value={v} />)
      expect(container.innerHTML).not.toMatch(COR_DE_JUIZO)
      unmount()
    }
  })

  it('o bloco de AS não traz mais "Participantes vs diretos" e não usa cor de juízo', () => {
    const dados = { v4: {}, v6: {}, par: 120, dir: 60, dif: 100, org: 90, cbrAsns: 12, cftAsns: 3, totalBrASNs: 9129, totalGlobalASNs: 80000 }
    const { container } = render(<IndicadoresAsBloco dados={dados as never} snapshot={null} />)
    expect(container.textContent).not.toMatch(/Participantes vs diretos/)
    expect(container.textContent).toMatch(/Participantes/)
    expect(container.innerHTML).not.toMatch(COR_DE_JUIZO)
  })

  it('potencial aparece em paleta neutra', () => {
    const b = render(<PotencialBloco dados={{ potential: { nearby_asn_count: 3, v6_prefixes_48: 10, v4_prefixes_24: 20, estimated_users_total: 1000 } } as never} snapshot={null} />)
    expect(b.container.innerHTML).not.toMatch(COR_DE_JUIZO)
  })
})
