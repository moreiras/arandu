// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Síntese do Panorama de mercado (PT-22): meses próprios por serviço, fixo e móvel nunca somados, "três maiores" com a regra na frase. */
import { describe, expect, it } from 'vitest'
import { PALAVRAS_PROIBIDAS } from '../../lib/sintese'
import { parcelaTresMaiores, sinteseMercado } from './sinteseMercado'

const fixo = { snapshot_date: '2026-11-22', mes_referencia: '2026-09', total_acessos: 58075574, operadoras_ativas: 9928,
  top_operadoras: [{ acessos: 10000000 }, { acessos: 8000000 }, { acessos: 4540000 }, { acessos: 100 }] } as never
const movel = { snapshot_date: '2026-11-22', mes_referencia: '2026-08', total_acessos: 220900000, acessos_m2m: 36100000 } as never

describe('sinteseMercado', () => {
  it('fixo e móvel, cada um com o seu mês, e nenhuma soma entre os dois', () => {
    const f = sinteseMercado(fixo, movel)
    expect(f.map((x) => x.id)).toEqual(['fixo', 'tres-maiores', 'movel'])
    expect(f[0].dataRef).toBe('2026-09')
    expect(f[2].dataRef).toBe('2026-08')
    expect(f[0].texto).toContain('58.075.574')
    expect(f[2].texto).toContain('220.900.000')
    expect(f[2].texto).toContain('sem M2M')
    expect(f.some((x) => x.texto.includes('279'))).toBe(false)
    for (const x of f) { expect(x.selo).toBe('fato'); expect(x.fonte).toMatch(/SICI/); expect(x.texto).not.toMatch(PALAVRAS_PROIBIDAS) }
  })

  it('"três maiores" traz a regra na frase, não nomeia empresa e confere com a soma dos três primeiros', () => {
    expect(parcelaTresMaiores(fixo.top_operadoras, fixo.total_acessos)).toBeCloseTo((100 * 22540000) / 58075574, 6)
    const t = sinteseMercado(fixo, movel)[1].texto
    expect(t).toContain('38,8%')
    expect(t).toMatch(/sem agrupar por grupo econômico/)
  })

  it('bordas: menos de três CNPJs, total zero e dado ausente não geram frase nem zero', () => {
    expect(parcelaTresMaiores([{ acessos: 5 }, { acessos: 4 }], 100)).toBeNull()
    expect(parcelaTresMaiores(fixo.top_operadoras, 0)).toBeNull()
    expect(sinteseMercado(null, null)).toEqual([])
    expect(sinteseMercado({ ...fixo, total_acessos: 0 }, null)).toEqual([])
    expect(sinteseMercado(fixo, null).map((x) => x.id)).toEqual(['fixo', 'tres-maiores'])
  })
})
