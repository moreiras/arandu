// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Síntese da operadora: regras fixas, selo por frase, nada sem dado, nada de veredito. */
import { describe, expect, it } from 'vitest'
import { kpisOperadora, REGRAS_VERSAO, sinteseOperadora } from './sintese'
import type { OperadoraCtx } from './contexto'

const base = { cnpjFinal: '90000001000129', hasScm: true, hasSici: true, hasStfc: false, hasSeac: false, b2cPct: 71.5 } as OperadoraCtx

describe('síntese da operadora', () => {
  it('monta as frases só com o que o snapshot tem, cada uma com selo', () => {
    const ctx = { ...base,
      data: { municipios: 12, asns: [64500, 64501] } as any,
      indicadores: { mes_referencia: '2026-08', metodologia: 'm', acessos: 12345, share_br: 0.42, posicao_br: 31, var_aa: { abs: 500, pct: 4.2 } } as any }
    const f = sinteseOperadora('Provedor 01', ctx)
    expect(f.map((x) => x.id)).toEqual(['outorgas', 'acessos', 'variacao', 'municipios', 'asns'])
    expect(f.find((x) => x.id === 'acessos')!.texto).toMatch(/12\.345 acessos .* 2026-08, 0,42% .* \(31º por acessos\)/)
    expect(f.every((x) => x.selo === 'fato')).toBe(true)
    expect(REGRAS_VERSAO).toBe('sintese-operadora-1')
  })

  it('sem indicadores nem municípios, não inventa frase', () => {
    const f = sinteseOperadora('X', { ...base, hasScm: false, hasSici: false } as OperadoraCtx)
    expect(f.map((x) => x.id)).toEqual(['asns'])
    expect(f[0].texto).toMatch(/Não tem ASN próprio/)
  })

  it('empresa com outorga SCM sem declaração diz só o fato e o mês', () => {
    const f = sinteseOperadora('X', { ...base, indicadores: { mes_referencia: '2026-08', metodologia: 'm', sem_declaracao: { razao_social: 'X', uf: 'SP', n_outorgas: 1, desde: null, asns: [], usuarios_apnic: null, classe: 'sem_usuarios' } } as any } as OperadoraCtx)
    expect(f.find((x) => x.id === 'sem-declaracao')!.texto).toBe('Tem outorga SCM, mas não declarou acessos ao SICI em 2026-08.')
  })

  it('indicadores sem valor não viram KPI vazio na ficha', () => {
    expect(kpisOperadora({ ...base } as OperadoraCtx).filter((k) => k.valor != null).map((k) => k.id)).toEqual(['asns'])
  })
})
