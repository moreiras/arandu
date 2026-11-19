// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { posicaoNaMetrica } from './CartogramaUfs'

const u = (uf: string, fibra_pct: number | null) => ({ uf, fibra_pct }) as any

describe('posição da UF entre as 27', () => {
  it('1 = maior valor, ignora UFs sem dado e devolve null se a própria UF não tem valor', () => {
    const ufs = [u('SP', 80), u('RJ', 70), u('AC', null), u('MG', 90)]
    const f = (x: any) => x.fibra_pct
    expect(posicaoNaMetrica(ufs, 'MG', f)).toEqual({ posicao: 1, de: 3 })
    expect(posicaoNaMetrica(ufs, 'RJ', f)).toEqual({ posicao: 3, de: 3 })
    expect(posicaoNaMetrica(ufs, 'AC', f)).toBeNull()
  })
})
