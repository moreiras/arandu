// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Síntese do Panorama técnico (PT-22): mesmos números dos KPIs, selo por frase, nada de juízo. */
import { describe, expect, it } from 'vitest'
import { PALAVRAS_PROIBIDAS } from '../../lib/sintese'
import { sinteseTecnica } from './sinteseTecnica'

const s = { ixps_ok: 38, ixps_partial: 1, ixps_missing: 1, ixp_aggregate: { asn_direct_union_count: 3134 } } as never
const br = {
  snapshot_date: '2026-11-22',
  ipv6: { usuarios: 161288456, usuarios_ipv6: 97577000, pct_usuarios_ipv6: 60.5, asns_com_estimativa: 1, asns_com_ipv6: 1, fonte: 'APNIC', nota: '' },
  rpki: { publicacao: { br_asns_total: 9129, br_asns_with_roa: 3934 }, rotas: null },
  rov: { media_ponderada_pct: 6.4, fonte: { as_of: '2026-11-20' } },
} as never

describe('sinteseTecnica', () => {
  it('quatro frases com os números dos KPIs, selos corretos e data de referência', () => {
    const f = sinteseTecnica(s, br, '2026-11-22')
    expect(f.map((x) => x.id)).toEqual(['ipv6', 'roa', 'ixbr', 'rov'])
    expect(f[0].texto).toContain('60,5%')
    expect(f[0].selo).toBe('estimado')
    expect(f[1].texto).toContain('3.934 dos 9.129')
    expect(f[1].texto).toContain('(43,1%)')
    expect(f[1].selo).toBe('fato')
    expect(f[2].texto).toContain('40 PTTs')
    expect(f[2].texto).toContain('3.134 ASNs')
    expect(f[3].texto).toContain('6,4%')
    expect(f[3].dataRef).toBe('2026-11-20')
    for (const x of f) { expect(x.fonte).not.toBe(''); expect(x.dataRef).toBeTruthy(); expect(x.texto).not.toMatch(PALAVRAS_PROIBIDAS) }
  })

  it('usa o rótulo de universo do PT-15 para o denominador do ROA', () => {
    expect(sinteseTecnica(s, br, '2026-11-22')[1].texto).toContain('ASNs na lista do Registro.br')
  })

  it('dado ausente não gera frase (nunca zero) e com menos de duas a síntese some', () => {
    expect(sinteseTecnica(null, null, null)).toEqual([])
    const so = sinteseTecnica(s, { snapshot_date: '2026-11-22', ipv6: { pct_usuarios_ipv6: null } } as never, '2026-11-22')
    expect(so.map((x) => x.id)).toEqual([])
    const tres = sinteseTecnica(s, { ...(br as object), rov: undefined } as never, '2026-11-22')
    expect(tres.map((x) => x.id)).toEqual(['ipv6', 'roa', 'ixbr'])
  })
})
