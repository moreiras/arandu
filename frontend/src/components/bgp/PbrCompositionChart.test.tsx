// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { RoutingAnalysis } from '../../types/routingAnalysis'
import { PbrCompositionChart } from './PbrCompositionChart'

const e = (routes: number, asns: number) => ({ routes, asns })
const apoio = (routes: number, asns: number) => ({ routes, asns, fora_do_total: true })

const doc = (comp: RoutingAnalysis['pbr_composition']) => ({ pbr_composition: comp }) as unknown as RoutingAnalysis

describe('composição das rotas brasileiras (BGP-E3, D4)', () => {
  it('regra atual: só as categorias com prefixo do Registro.br compõem o total; origem BR fora de bloco é apoio à parte', () => {
    render(<PbrCompositionChart data={doc({
      v6: { strict_br: e(30000, 7000), prefix_only_br: e(600, 90), total: e(30600, 7050), asn_br_fora_de_bloco: apoio(977, 21), origin_only_br: apoio(977, 21) },
      v4: { strict_br: e(70000, 7900), prefix_only_br: e(900, 80), total: e(70900, 7950), asn_br_fora_de_bloco: apoio(8276, 21), origin_only_br: apoio(8276, 21) },
    })} />)
    expect(screen.getByText(/As duas somam o total/)).toBeInTheDocument()
    expect(screen.getByText(/IPv6: 977 rotas de 21 ASNs/)).toBeInTheDocument()
    expect(screen.getByText(/IPv4: 8\.276 rotas de 21 ASNs/)).toBeInTheDocument()
    expect(screen.queryByText(/Snapshot gerado antes da regra atual/)).toBeNull()
  })

  it('documento anterior à regra: avisa que o total incluía "apenas origem BR"', () => {
    render(<PbrCompositionChart data={doc({
      v6: { strict_br: e(30000, 7000), origin_only_br: e(1031, 40), prefix_only_br: e(600, 90) },
      v4: { strict_br: e(70000, 7900), origin_only_br: e(10580, 60), prefix_only_br: e(900, 80) },
    })} />)
    expect(screen.getByText(/Snapshot gerado antes da regra atual/)).toBeInTheDocument()
  })
})
