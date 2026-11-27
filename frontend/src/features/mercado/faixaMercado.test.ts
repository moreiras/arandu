// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Faixa de cartões do Panorama de mercado (PT-22 / 5.3): mês próprio por serviço, sem soma entre fixo e móvel, sem nome de empresa, sem zero inventado. */
import { describe, expect, it } from 'vitest'
import { PALAVRAS_PROIBIDAS } from '../../lib/sintese'
import { cartoesMercado, mesHa12, parcelaTresMaioresUnidades, variacao12Meses } from './faixaMercado'

const fixo = {
  snapshot_date: '2026-11-22', mes_referencia: '2026-09', total_acessos: 58075574, operadoras_ativas: 9928,
  top_operadoras: [{ acessos: 10000000 }, { acessos: 8000000 }, { acessos: 4540000 }, { acessos: 100 }],
  serie_total: [{ mes: '2025-09', acessos: 54861114, cnpjs: 1 }, { mes: '2026-09', acessos: 58075574, cnpjs: 1 }],
} as never
const movel = { snapshot_date: '2026-11-22', mes_referencia: '2026-08', total_acessos: 220900000, acessos_m2m: 36100000,
  top_operadoras: [{ acessos: 100000000 }, { acessos: 70000000 }, { acessos: 45400000 }] } as never
const grupos = { mes_referencia: '2026-09', brasil: { hhi_cnpj: 1234, acessos: 1, n_cnpjs: 1, nota: '' }, resumo: { municipios: 5570, por_faixa_cnpj: { competitivo: 1, moderado: 1, concentrado: 446, sem_dado: 0 } } } as never
const maiores = { mes_referencia: '2026-09', unidades: [{ id: 'a', grupo: true, nome: 'X', acessos: 5, cnpjs: 1, share: 20 }, { id: 'b', grupo: false, nome: 'Y', acessos: 4, cnpjs: 1, share: 15 }, { id: 'c', grupo: false, nome: 'Z', acessos: 3, cnpjs: 1, share: 6.4 }] } as never

describe('cartoesMercado', () => {
  it('fixo e móvel com mês próprio, selo e fonte, e nenhuma soma entre os dois', () => {
    const c = cartoesMercado(fixo, movel, grupos, maiores)
    expect(c.map((x) => x.id)).toEqual(['fixo-acessos', 'fixo-tres-cnpj', 'fixo-tres-grupo', 'fixo-hhi', 'movel-linhas', 'movel-tres-cnpj'])
    expect(c.filter((x) => x.servico === 'fixo').every((x) => x.dataRef === '2026-09')).toBe(true)
    expect(c.filter((x) => x.servico === 'movel').every((x) => x.dataRef === '2026-08')).toBe(true)
    expect(c[0].valor).toBe('58,1 mi')
    expect(c[0].variacao).toContain('+5,9% em 12 meses')
    expect(c[0].variacao).toContain('09/2025')
    expect(c[1].valor).toBe('38,8%')
    expect(c[2].valor).toBe('41,4%')
    expect(c[2].selo).toBe('inferido')
    expect(c[3].referencia).toContain('446 municípios com HHI local de 2.500 ou mais')
    expect(c[4].referencia).toContain('36.100.000 acessos M2M à parte')
    expect(c[5].valor).toBe('97,5%')
    expect(c.some((x) => x.valor.includes('279'))).toBe(false)
    for (const x of c) { expect(x.fonte).toMatch(/SICI|cálculo/); expect(`${x.rotulo} ${x.referencia ?? ''}`).not.toMatch(PALAVRAS_PROIBIDAS) }
  })

  it('dado ausente não gera cartão nem zero', () => {
    expect(cartoesMercado(null, null, null, null)).toEqual([])
    const so = cartoesMercado(fixo, null, null, null)
    expect(so.map((x) => x.id)).toEqual(['fixo-acessos', 'fixo-tres-cnpj'])
    expect(cartoesMercado({ ...(fixo as object), total_acessos: 0 } as never, null, null, null)).toEqual([])
  })

  it('variação em 12 meses só existe se o mês de comparação está na série', () => {
    expect(mesHa12('2026-09')).toBe('2025-09')
    expect(variacao12Meses([{ mes: '2026-09', acessos: 10 }], '2026-09')).toBeNull()
    expect(variacao12Meses([{ mes: '2025-09', acessos: 0 }, { mes: '2026-09', acessos: 10 }], '2026-09')).toBeNull()
    expect(variacao12Meses([{ mes: '2025-09', acessos: 100 }, { mes: '2026-09', acessos: 90 }], '2026-09')?.pct).toBeCloseTo(-10)
  })

  it('três maiores empresas ou grupos exige três itens com parcela conhecida', () => {
    expect(parcelaTresMaioresUnidades({ unidades: [{ acessos: 1, share: 1 }, { acessos: 1, share: 1 }] } as never)).toBeNull()
    expect(parcelaTresMaioresUnidades({ unidades: [{ acessos: 3, share: 1 }, { acessos: 2, share: null }, { acessos: 1, share: 1 }] } as never)).toBeNull()
  })
})
