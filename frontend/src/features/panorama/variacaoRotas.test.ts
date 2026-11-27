// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import type { SerieNacional } from '../../services/api'
import { variacaoRotasRpki } from './variacaoRotas'

const metrica = (id: string, calculada: boolean, absoluta: number | null, de = '2026-11-15') =>
  ({ id, variacao: { de, para: '2026-11-22', calculada, absoluta, unidade: 'pp', motivos: calculada ? [] : ['base_diferente'] } })
const serie = (metricas: unknown[]) => ({ metricas } as unknown as SerieNacional)

describe('variacaoRotasRpki', () => {
  it('mostra IPv6 antes de IPv4, em p.p., com a data de comparação, sem marcar bom ou ruim', () => {
    const v = variacaoRotasRpki(serie([metrica('v4', true, -0.1), metrica('v6', true, 0.35)]), 'v6', 'v4', '2026-11-15')
    expect(v).toEqual({ texto: 'IPv6 +0,35 p.p. · IPv4 -0,1 p.p. desde 2026-11-15 (série semanal)' })
  })
  it('uma família não comparável fica de fora; nenhuma comparável, sem texto (nunca zero)', () => {
    expect(variacaoRotasRpki(serie([metrica('v6', false, null), metrica('v4', true, 0.2)]), 'v6', 'v4', '2026-11-15')?.texto).toMatch(/^IPv4 \+0,2 p\.p\./)
    expect(variacaoRotasRpki(serie([metrica('v6', false, null), metrica('v4', false, null)]), 'v6', 'v4', '2026-11-15')).toBeUndefined()
  })
  it('ignora variação de outro par de datas e a falta de série ou de snapshot anterior', () => {
    expect(variacaoRotasRpki(serie([metrica('v6', true, 1, '2026-11-01')]), 'v6', 'v4', '2026-11-15')).toBeUndefined()
    expect(variacaoRotasRpki(undefined, 'v6', 'v4', '2026-11-15')).toBeUndefined()
    expect(variacaoRotasRpki(serie([metrica('v6', true, 1)]), 'v6', 'v4', null)).toBeUndefined()
  })
})
