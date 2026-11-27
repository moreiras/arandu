// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Referência nacional e posição nos cartões da UF (PT-22 / uf 5.5): contas das linhas de `/ufs`, sem juízo na redação. */
import { describe, expect, it } from 'vitest'
import { PALAVRAS_PROIBIDAS } from '../../lib/sintese'
import { referenciaUf, valorBrasil } from './referenciasUf'

const u = (uf: string, acessos: number | null, fibra: number | null, dom: number | null, ptts: number, asns: number) =>
  ({ uf, acessos, fibra_pct: fibra, domicilios: dom, penetracao: acessos != null && dom ? acessos / dom : null, ptts, asns, municipios: 1, usuarios: 0, municipios_sem_ptt: 0 }) as never
const ufs = [u('SP', 1000, 80, 1000, 5, 30), u('AM', 100, 50, 200, 1, 3), u('RR', null, null, null, 1, 1)]

describe('referenciaUf', () => {
  it('Brasil e posição pelo maior valor, com a regra da posição escrita', () => {
    const t = referenciaUf(ufs, 'AM', 'acessos')
    expect(t).toBe('Brasil: 1.100 · posição 2 de 2 UFs (1 = maior valor)')
    expect(referenciaUf(ufs, 'SP', 'ptts')).toContain('posição 1 de 3 UFs')
    expect(PALAVRAS_PROIBIDAS.test(t)).toBe(false)
  })

  it('fibra do país pondera pelos acessos e penetração soma só UFs com os dois dados', () => {
    expect(valorBrasil(ufs, 'fibra')).toBe(`${((1000 * 80 + 100 * 50) / 1100).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`)
    expect(valorBrasil(ufs, 'penetracao')).toBe(((100 * 1100) / 1200).toLocaleString('pt-BR', { maximumFractionDigits: 1 }))
  })

  it('UF sem valor fica sem posição, e sem /ufs não há linha', () => {
    expect(referenciaUf(ufs, 'RR', 'acessos')).toBe('Brasil: 1.100')
    expect(referenciaUf(undefined, 'AM', 'acessos')).toBe('')
    expect(referenciaUf([], 'AM', 'acessos')).toBe('')
  })
})
