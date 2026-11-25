// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Síntese da Home (PT-22): sai dos mesmos KPIs da faixa, com selo, fonte e data; ausência não vira frase nem zero. */
import { describe, expect, it } from 'vitest'
import { MAX_FRASES, PALAVRAS_PROIBIDAS } from '../../lib/sintese'
import { montarKpis } from './kpisBrasilEmNumeros'
import { sinteseHome } from './sinteseHome'

const resumo = { total_asns_br: 9129, br_asns_ft_v6: 7500, br_ipv6_pct: 97.1, ixps_ok: 40, ixps_partial: 0, br_apnic_users_total: 161288456 }
const sici = { mes_referencia: '2026-09', total_acessos: 58075574, operadoras_ativas: 9928, municipios_atendidos: 5500, por_meio: { Fibra: 40000000 }, serie_total: [] }
const kpis = montarKpis(resumo as never, null, sici as never, '2026-11-22')

describe('sinteseHome', () => {
  it('2 a 4 frases, cada uma com selo, fonte e data, e os números são os mesmos dos KPIs', () => {
    const f = sinteseHome(kpis)
    expect(f.length).toBeGreaterThanOrEqual(2)
    expect(f.length).toBeLessThanOrEqual(MAX_FRASES)
    for (const x of f) {
      expect(['fato', 'estimado', 'inferido']).toContain(x.selo)
      expect(x.fonte).not.toBe('')
      expect(x.dataRef).toBeTruthy()
      expect(x.texto).not.toMatch(PALAVRAS_PROIBIDAS)
    }
    const valor = (id: string) => [...kpis.rede, ...kpis.mercado].find((k) => k.id === id)!.valor!
    expect(f.find((x) => x.id === 'ases')!.texto).toContain(valor('ases'))
    expect(f.find((x) => x.id === 'ipv6')!.texto).toContain(valor('ipv6'))
    expect(f.find((x) => x.id === 'acessos')!.texto).toContain(valor('acessos'))
    expect(f.find((x) => x.id === 'acessos')!.dataRef).toBe('2026-09')
  })

  it('usa os rótulos de universo do PT-15 e rotula a estimativa do APNIC como estimado', () => {
    const f = sinteseHome(kpis)
    expect(f.find((x) => x.id === 'ases')!.texto).toContain('ASNs brasileiros (delegados pela LACNIC ao Brasil)')
    const u = f.find((x) => x.id === 'usuarios')!
    expect(u.selo).toBe('estimado')
    expect(u.texto).toContain('estimativa')
  })

  it('KPI sem valor não gera frase; sem dado nenhum a síntese some (nunca zero)', () => {
    expect(sinteseHome(montarKpis(null, null, null, null))).toEqual([])
    const so = sinteseHome(montarKpis(resumo as never, null, null, '2026-11-22'))
    expect(so.some((x) => x.id === 'acessos')).toBe(false)
    expect(so.every((x) => !/\b0\b/.test(x.texto))).toBe(true)
  })

  it('sem o KPI de fibra a frase de acessos continua, sem a parcela', () => {
    const k = { rede: kpis.rede, mercado: kpis.mercado.filter((x) => x.id !== 'fibra') }
    const t = sinteseHome(k).find((x) => x.id === 'acessos')!.texto
    expect(t).not.toContain('fibra')
  })
})
