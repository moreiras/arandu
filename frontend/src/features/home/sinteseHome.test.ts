// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Síntese da Home (PT-22): sai dos mesmos KPIs da faixa e dos agregados já carregados, com selo, fonte e data; ausência não vira frase nem zero. */
import { describe, expect, it } from 'vitest'
import { MAX_FRASES_HOME, PALAVRAS_PROIBIDAS } from '../../lib/sintese'
import { montarKpis } from './kpisBrasilEmNumeros'
import { sinteseHome, type DadosSinteseHome } from './sinteseHome'

const resumo = {
  total_asns_br: 9129, br_asns_ft_v6: 7500, br_ipv6_pct: 97.1, ixps_ok: 40, ixps_partial: 0, br_apnic_users_total: 161288456,
  ixp_estimated_users_v4: 120000000, ixp_aggregate: { asn_direct_union_count: 2300, v6_br_coverage_pct: 61.25, v4_br_coverage_pct: 48.5 },
}
const sici = {
  mes_referencia: '2026-09', total_acessos: 1000, operadoras_ativas: 9928, municipios_atendidos: 5500, por_meio: { Fibra: 400 }, serie_total: [],
  top_operadoras: [{ acessos: 300 }, { acessos: 200 }, { acessos: 100 }, { acessos: 50 }],
}
const br = {
  snapshot_date: '2026-11-22', ipv6: { pct_usuarios_ipv6: 52.4 },
  ixbr: { asns_br_total: 9000, asns_br_diretos: 2100, asns_br_indiretos: 1500, asns_br_originam: 3300, fonte: 'x', nota: 'y' },
  dnssec: { media_ponderada_pct: 38.456, fonte: { as_of: '2026-11-20' } }, rov: { media_ponderada_pct: 61.234, fonte: { as_of: '2026-11-21' } },
  rpki: { publicacao: { br_asns_total: 9000, br_asns_with_roa: 4500, br_asns_with_aspa: 90 }, rotas: { rpki: { v6: { pct: { valid: 80.5 } }, v4: { pct: { valid: 70.25 } } } } },
  mercado: { hhi_cnpj: 1234.4, acessos: 1000, n_cnpjs: 9928, mes_referencia: '2026-09' },
}
const dados = { resumo, br, sici } as unknown as DadosSinteseHome
const kpis = montarKpis(resumo as never, null, sici as never, '2026-11-22')

describe('sinteseHome', () => {
  it('no máximo 6 frases curtas em até dois parágrafos, cada uma com selo, fonte e data, sem palavra de juízo', () => {
    const f = sinteseHome(kpis, dados)
    expect(MAX_FRASES_HOME).toBe(6)
    expect(f.length).toBeGreaterThan(2)
    expect(f.length).toBeLessThanOrEqual(MAX_FRASES_HOME)
    expect(new Set(f.map((x) => x.paragrafo)).size).toBeLessThanOrEqual(2)
    for (const x of f) {
      expect(['fato', 'estimado', 'inferido']).toContain(x.selo)
      expect(x.fonte).not.toBe('')
      expect(x.dataRef).toBeTruthy()
      expect(x.paragrafo).toBeTruthy()
      expect(x.texto.length).toBeLessThan(260)
      expect(x.texto).not.toMatch(PALAVRAS_PROIBIDAS)
      expect(x.texto).not.toMatch(/[—–]/)
    }
  })

  it('segue a ordem rede, IX.br, usuários, segurança e mercado, com IPv6 antes de IPv4', () => {
    const f = sinteseHome(kpis, dados)
    expect(f.map((x) => x.id)).toEqual(['rede', 'ixbr', 'usuarios', 'seguranca', 'mercado'])
    const ix = f.find((x) => x.id === 'ixbr')!.texto
    expect(ix.indexOf('IPv6')).toBeLessThan(ix.indexOf('IPv4'))
  })

  it('rede e IPv6 numa frase, com os números dos cartões e o rótulo de universo do PT-15', () => {
    const t = sinteseHome(kpis, dados).find((x) => x.id === 'rede')!
    const valor = (id: string) => kpis.rede.find((k) => k.id === id)!.valor!
    expect(t.texto).toBe(`Dos ${valor('ases')} ASNs brasileiros (delegados pela LACNIC ao Brasil), ${valor('ipv6')} originam ao menos um prefixo IPv6 na tabela global.`)
    expect(t.selo).toBe('fato')
  })

  it('IX.br: diretos, indiretos e espaço coberto numa frase; usuários alcançados pela união por ASN', () => {
    const f = sinteseHome(kpis, dados)
    const t = (id: string) => f.find((x) => x.id === id)!
    expect(t('ixbr').texto).toBe('No IX.br, 2.100 ASNs participam diretamente e outros 1.500 participam indiretamente, só originando prefixos vistos nos PTTs; os prefixos vistos nos PTTs cobrem 61,3% do espaço IPv6 e 48,5% do espaço IPv4 alocados ao Brasil.')
    expect(t('ixbr').selo).toBe('inferido')
    expect(t('usuarios').selo).toBe('estimado')
    expect(t('usuarios').texto).toBe('Os PTTs do IX.br alcançam cerca de 120 mi dos 161,3 mi usuários de Internet que o APNIC estima no Brasil (74,4%), com cada ASN contado uma só vez e só em IPv4.')
  })

  it('segurança (ROA e ROV) e mercado (CNPJs e HHI) numa frase cada, sem nomear empresa', () => {
    const f = sinteseHome(kpis, dados)
    const t = (id: string) => f.find((x) => x.id === id)!
    expect(t('seguranca').texto).toBe('4.500 dos 9.000 ASNs na lista do Registro.br publicaram ao menos uma ROA (50%), e 61,23% das medições do APNIC indicam filtragem de rotas inválidas (ROV).')
    expect(t('seguranca').selo).toBe('estimado')
    expect(t('mercado').texto).toBe('9.928 CNPJs declararam acessos de banda larga fixa ao SICI, e o HHI nacional por CNPJ, sem agrupar grupos econômicos, é 1.234, numa escala de 0 a 10.000.')
    expect(t('mercado').selo).toBe('fato')
    expect(t('mercado').dataRef).toBe('2026-09')
    expect(f.some((x) => /DNSSEC|ASPA/.test(x.texto))).toBe(false)
  })

  it('sem os agregados novos a síntese cai para rede e usuários, sem zero inventado', () => {
    const f = sinteseHome(kpis)
    expect(f.map((x) => x.id)).toEqual(['rede', 'usuarios'])
    expect(sinteseHome(montarKpis(null, null, null, null))).toEqual([])
    expect(f.every((x) => !/\b0\b/.test(x.texto))).toBe(true)
  })

  it('PTT sem coleta não gera a frase de IX.br, e cobertura zero de uma família não aparece', () => {
    const sem = { ...dados, resumo: { ...resumo, ixps_ok: 0 } } as unknown as DadosSinteseHome
    expect(sinteseHome(kpis, sem).some((x) => x.id === 'ixbr')).toBe(false)
    const v6zero = { ...dados, resumo: { ...resumo, ixp_aggregate: { ...resumo.ixp_aggregate, v6_br_coverage_pct: 0 } } } as unknown as DadosSinteseHome
    const t = sinteseHome(kpis, v6zero).find((x) => x.id === 'ixbr')!.texto
    expect(t).not.toContain('IPv6')
    expect(t).toContain('IPv4')
  })

  it('singular quando há um só ASN', () => {
    const um = { ...dados, br: { ...br, ixbr: { ...br.ixbr, asns_br_diretos: 1, asns_br_indiretos: 1 } } } as unknown as DadosSinteseHome
    expect(sinteseHome(kpis, um).find((x) => x.id === 'ixbr')!.texto).toContain('1 ASN participa diretamente e outros 1 participa indiretamente')
  })
})
