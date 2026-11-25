// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Síntese de /municipios (PT-22): "longe de PTT" dito como distância em linha reta, comparação sem causa, grupo vazio sem frase, UF no texto. */
import { describe, expect, it } from 'vitest'
import { PALAVRAS_PROIBIDAS } from '../../lib/sintese'
import type { AgregadoTerritorio, ResumoTerritorio } from '../../types/api'
import { sinteseMunicipios } from './sinteseMunicipios'

const ag = (municipios: number, populacao_estimada: number, acessos_por_domicilio: number | null): AgregadoTerritorio =>
  ({ municipios, populacao_estimada, domicilios_projetados: 0, acessos: 0, nao_visto: 0, acessos_por_domicilio })
const resumo = (over: Partial<ResumoTerritorio> = {}): ResumoTerritorio => ({
  snapshot_date: '2026-11-22', mes_referencia_sici: '2026-09', censo_ano: '2022', pnad_ano: '2025', fonte: 'x', formulas: {}, limites: 'y', criterio: 'z',
  escopo: { pais: 'BR' }, raio_sem_ptt_km: 100,
  total: ag(5570, 214_300_000, 0.7), a_mais_de_100km: ag(3680, 77_984_588, 0.614), ate_100km: ag(1889, 136_315_412, 0.809), sem_distancia: ag(1, 0, null),
  penetracao: { porte_minimo_domicilios: 1000, municipios_com_penetracao: 5197, municipios_abaixo_do_porte: 372, municipios_sem_domicilios: 1, com_mais_acessos_que_domicilios: 449 },
  ...over,
}) as ResumoTerritorio

describe('sinteseMunicipios', () => {
  it('quatro frases com os agregados, a parcela da população e a razão de cada grupo', () => {
    const f = sinteseMunicipios(resumo())
    expect(f.map((x) => x.id)).toEqual(['longe', 'razao', 'acima-de-1', 'cobertura'])
    expect(f[0].texto).toBe('A mais de 100 km em linha reta de um ponto de interconexão do IX.br vivem 78 mi pessoas (36,4% da população estimada), em 3.680 municípios.')
    expect(f[0].selo).toBe('estimado')
    expect(f[1].texto).toBe('Nesses municípios há 0,61 acesso fixo declarado por domicílio projetado; nos que ficam até 100 km, 0,81. É comparação de médias entre grupos e não mede causa.')
    expect(f[2].texto).toContain('449 municípios têm mais acessos fixos declarados do que domicílios projetados')
    expect(f[3].texto).toBe('Penetração calculada em 5.197 de 5.570 municípios (com ao menos 1.000 domicílios); 372 têm menos que isso e 1 não tem domicílios no Censo.')
    for (const x of f) { expect(x.fonte).not.toBe(''); expect(x.dataRef).toBeTruthy(); expect(x.texto).not.toMatch(PALAVRAS_PROIBIDAS); expect(x.texto).not.toMatch(/sem internet|mal atendid/i) }
  })

  it('com UF no escopo a frase diz a UF; sem município longe (DF) não há frase de distância nem de razão', () => {
    const am = sinteseMunicipios(resumo({ escopo: { uf: 'AM' } }))
    expect(am[0].texto).toContain('do IX.br na UF Amazonas vivem')
    const df = sinteseMunicipios(resumo({ escopo: { uf: 'DF' }, a_mais_de_100km: ag(0, 0, null) }))
    expect(df.some((x) => x.id === 'longe' || x.id === 'razao')).toBe(false)
  })

  it('razão nula de um grupo não vira zero; sem resumo ou sem município a síntese some', () => {
    expect(sinteseMunicipios(resumo({ ate_100km: ag(2, 10, null) })).some((x) => x.id === 'razao')).toBe(false)
    expect(sinteseMunicipios(undefined)).toEqual([])
    expect(sinteseMunicipios(resumo({ total: ag(0, 0, null) }))).toEqual([])
  })
})
