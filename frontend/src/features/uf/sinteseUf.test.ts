// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Síntese da UF (PT-22, uf 5.5): números do painel, selo por frase, sem juízo; DF sem a frase de distância; sem dado, sem frase. */
import { describe, expect, it } from 'vitest'
import { PALAVRAS_PROIBIDAS } from '../../lib/sintese'
import type { UfCtx } from './contexto'
import { sinteseUf } from './sinteseUf'

const base = (over: Partial<UfCtx['totais']> = {}, ixps = 1, penetracao: number | null = 0.58): UfCtx => ({
  uf: 'AM', ixps: new Array(ixps).fill({}), municipios: [], semCentroides: false, mesReferencia: '2026-09',
  totais: { municipios: 62, acessos: 724373, fibra_pct: 66.9, asns: 110, usuarios: 1000, municipios_sem_ptt: 55, acessos_sem_ptt: 142967, raio_sem_ptt_km: 100, ...over },
  territorio: penetracao === null ? undefined : { penetracao, mes_referencia_sici: '2026-09' },
  operadoras: [], operadorasTotal: 0, operadorasPresentes: [], operadorasPresentesTotal: 0,
} as unknown as UfCtx)

describe('sinteseUf', () => {
  it('AM: quatro frases na ordem mercado, domicílios, infraestrutura, rede, com selo e data', () => {
    const f = sinteseUf(base(), '2026-11-22')
    expect(f.map((x) => x.id)).toEqual(['acessos', 'penetracao', 'sem-ptt', 'rede'])
    expect(f[0].texto).toBe('Amazonas tem 724.373 acessos de banda larga fixa declarados ao SICI em 09/2026, em 62 municípios, e 66,9% deles são em fibra.')
    expect(f[0].selo).toBe('fato')
    expect(f[1].texto).toContain('58 acessos fixos para cada 100 domicílios')
    expect(f[1].selo).toBe('estimado')
    expect(f[2].texto).toContain('55 ficam a mais de 100 km em linha reta')
    expect(f[2].texto).toContain('142.967')
    expect(f[2].selo).toBe('estimado')
    expect(f[3].texto).toContain('1 PTT do IX.br')
    expect(f[3].texto).toContain('110 ASNs brasileiros com UF da sede conhecida')
    for (const x of f) { expect(x.fonte).not.toBe(''); expect(x.dataRef).toBeTruthy(); expect(x.texto).not.toMatch(PALAVRAS_PROIBIDAS) }
  })

  it('DF (0 municípios longe) não ganha a frase de distância; sem PTT a frase de rede diz isso', () => {
    const f = sinteseUf(base({ municipios_sem_ptt: 0, acessos_sem_ptt: 0 }, 0), '2026-11-22')
    expect(f.some((x) => x.id === 'sem-ptt')).toBe(false)
    expect(f.find((x) => x.id === 'rede')!.texto).toMatch(/^Não há PTT do IX\.br na UF/)
  })

  it('sem SICI (acessos nulos) e sem território, só resta a frase de rede e a síntese some', () => {
    expect(sinteseUf(base({ acessos: null, municipios: null, fibra_pct: null, municipios_sem_ptt: null, acessos_sem_ptt: null }, 1, null), '2026-11-22')).toEqual([])
  })

  it('penetração pequena não vira zero falso e a fibra ausente some da frase', () => {
    const f = sinteseUf(base({ fibra_pct: null }, 1, 0.0033), '2026-11-22')
    expect(f[0].texto).not.toContain('fibra')
    expect(f.find((x) => x.id === 'penetracao')!.texto).toContain('0,3 acessos fixos')
  })
})
