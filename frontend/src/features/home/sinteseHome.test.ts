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
  it('cada frase tem selo, fonte e data, sem palavra de juízo, e os números dos KPIs são os mesmos', () => {
    const f = sinteseHome(kpis, dados)
    expect(f.length).toBeGreaterThan(4)
    expect(f.length).toBeLessThanOrEqual(MAX_FRASES_HOME)
    for (const x of f) {
      expect(['fato', 'estimado', 'inferido']).toContain(x.selo)
      expect(x.fonte).not.toBe('')
      expect(x.dataRef).toBeTruthy()
      expect(x.paragrafo).toBeTruthy()
      expect(x.texto).not.toMatch(PALAVRAS_PROIBIDAS)
      expect(x.texto).not.toMatch(/[—–]/)
    }
    const valor = (id: string) => [...kpis.rede, ...kpis.mercado].find((k) => k.id === id)!.valor!
    expect(f.find((x) => x.id === 'ases')!.texto).toContain(valor('ases'))
    expect(f.find((x) => x.id === 'ipv6')!.texto).toContain(valor('ipv6'))
    expect(f.find((x) => x.id === 'acessos')!.texto).toContain(valor('acessos'))
    expect(f.find((x) => x.id === 'acessos')!.dataRef).toBe('2026-09')
  })

  it('segue a ordem rede, IX.br, segurança, mercado e usuários, com IPv6 antes de IPv4', () => {
    const f = sinteseHome(kpis, dados)
    expect(f.map((x) => x.id)).toEqual(['ases', 'ipv6', 'ixbr-diretos', 'ixbr-indiretos', 'ixbr-espaco', 'dnssec', 'roa', 'roa-rotas', 'rov', 'aspa',
      'acessos', 'operadoras', 'hhi', 'tres-maiores', 'usuarios', 'ixbr-usuarios'])
    expect(f.find((x) => x.id === 'ixbr-espaco')!.texto.indexOf('IPv6')).toBeLessThan(f.find((x) => x.id === 'ixbr-espaco')!.texto.indexOf('IPv4'))
    expect(f.find((x) => x.id === 'roa-rotas')!.texto.indexOf('IPv6')).toBeLessThan(f.find((x) => x.id === 'roa-rotas')!.texto.indexOf('IPv4'))
  })

  it('IX.br: diretos e indiretos do agregado, espaço coberto e usuários pela união por ASN', () => {
    const f = sinteseHome(kpis, dados)
    const t = (id: string) => f.find((x) => x.id === id)!
    expect(t('ixbr-diretos').texto).toContain('2.100 ASNs da lista do Registro.br participam diretamente')
    expect(t('ixbr-diretos').selo).toBe('fato')
    expect(t('ixbr-indiretos').texto).toContain('Outros 1.500 ASNs participam indiretamente')
    expect(t('ixbr-indiretos').selo).toBe('inferido')
    expect(t('ixbr-espaco').texto).toContain('61,3% do espaço IPv6 e 48,5% do espaço IPv4')
    expect(t('ixbr-usuarios').selo).toBe('estimado')
    expect(t('ixbr-usuarios').texto).toContain('120 mi')
    expect(t('ixbr-usuarios').texto).toContain('74,4%')
    expect(t('ixbr-usuarios').texto).toContain('Cada ASN conta uma só vez')
  })

  it('segurança e mercado: números e regras visíveis, sem nomear empresa', () => {
    const f = sinteseHome(kpis, dados)
    const t = (id: string) => f.find((x) => x.id === id)!
    expect(t('dnssec').texto).toContain('38,46%')
    expect(t('dnssec').dataRef).toBe('2026-11-20')
    expect(t('roa').texto).toContain('4.500 dos 9.000')
    expect(t('roa-rotas').texto).toContain('80,5% em IPv6 e 70,3% em IPv4')
    expect(t('rov').texto).toContain('61,23%')
    expect(t('aspa').texto).toContain('90 ASNs (1%)')
    expect(t('operadoras').texto).toContain('9.928 CNPJs que declararam')
    expect(t('hhi').texto).toContain('1.234')
    expect(t('hhi').texto).toContain('não agrupa CNPJs do mesmo grupo econômico')
    expect(t('tres-maiores').texto).toContain('60%')
  })

  it('usa os rótulos de universo do PT-15 e rotula a estimativa do APNIC como estimado', () => {
    const f = sinteseHome(kpis, dados)
    expect(f.find((x) => x.id === 'ases')!.texto).toContain('ASNs brasileiros (delegados pela LACNIC ao Brasil)')
    const u = f.find((x) => x.id === 'usuarios')!
    expect(u.selo).toBe('estimado')
    expect(u.texto).toContain('estimado a partir de amostras de anúncios')
  })

  it('sem os agregados novos a síntese cai para as frases dos KPIs, sem zero inventado', () => {
    const f = sinteseHome(kpis)
    expect(f.map((x) => x.id)).toEqual(['ases', 'ipv6', 'acessos', 'usuarios'])
    const so = sinteseHome(montarKpis(resumo as never, null, null, '2026-11-22'))
    expect(so.some((x) => x.id === 'acessos')).toBe(false)
    expect(sinteseHome(montarKpis(null, null, null, null))).toEqual([])
    expect(f.every((x) => !/\b0\b/.test(x.texto))).toBe(true)
  })

  it('PTT sem coleta não gera frase de IX.br, e cobertura zero de uma família não aparece', () => {
    const sem = { ...dados, resumo: { ...resumo, ixps_ok: 0 } } as unknown as DadosSinteseHome
    expect(sinteseHome(kpis, sem).some((x) => x.id.startsWith('ixbr-') && x.id !== 'ixbr-usuarios')).toBe(false)
    const v6zero = { ...dados, resumo: { ...resumo, ixp_aggregate: { ...resumo.ixp_aggregate, v6_br_coverage_pct: 0 } } } as unknown as DadosSinteseHome
    const t = sinteseHome(kpis, v6zero).find((x) => x.id === 'ixbr-espaco')!.texto
    expect(t).not.toContain('IPv6')
    expect(t).toContain('IPv4')
  })

  it('singular quando há um só ASN', () => {
    const um = { ...dados, br: { ...br, ixbr: { ...br.ixbr, asns_br_diretos: 1, asns_br_indiretos: 1 } } } as unknown as DadosSinteseHome
    const f = sinteseHome(kpis, um)
    expect(f.find((x) => x.id === 'ixbr-diretos')!.texto).toContain('1 ASN da lista do Registro.br participa diretamente')
    expect(f.find((x) => x.id === 'ixbr-indiretos')!.texto).toContain('Outros 1 ASN participa indiretamente, pois só origina')
  })
})
