// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Síntese do município: a penetração não pode virar zero falso por arredondamento (MUN-E8). */
import { describe, expect, it } from 'vitest'
import { sinteseMunicipio } from './sintese'

const frase = (penetracao: number) =>
  sinteseMunicipio('X', { ibge: '1', proximos: [], territorio: { penetracao } } as any).find((f) => f.id === 'penetracao')!.texto

describe('penetração na síntese do município (MUN-E8)', () => {
  it('Pedro Régis (0,0033 acesso por domicílio) sai "0,3 acesso fixo", não "0 acessos"', () => {
    expect(frase(0.0033)).toBe('Estimativa: 0,3 acesso fixo para cada 100 domicílios (domicílios projetados a partir do Censo 2022).')
  })
  it('bordas: valor muito pequeno, valor alto com uma casa e zero de verdade', () => {
    expect(frase(0.0002)).toMatch(/^Estimativa: menos de 0,1 acesso fixo para cada 100/)
    expect(frase(0.4159)).toMatch(/^Estimativa: 41,6 acessos fixos para cada 100/)
    expect(frase(0)).toMatch(/^Estimativa: 0 acesso fixo para cada 100/)
  })
})

describe('penetração com declaração incompleta (PT-26, MUN 5.1 e)', () => {
  const com = (eventos: any[]) => sinteseMunicipio('X', { ibge: '1', proximos: [], territorio: { penetracao: 0.0033 }, indicadores: { eventos } } as any).find((f) => f.id === 'penetracao')!.texto
  it('com CNPJ sem declaração no mês a frase avisa que o número descreve o declarado', () => {
    expect(com([{ tipo: 'sem_declaracao_desde', cnpj: '1', empresa: '', mes: '2026-08', acessos: 1, mes_acessos: '2026-07' }])).toMatch(/^Estimativa, com declaração incompleta neste município/)
  })
  it('primeira declaração ou ausência de evento não muda a frase', () => {
    expect(com([{ tipo: 'primeira_declaracao', cnpj: '1', empresa: '', mes: '2026-09', acessos: 1, mes_acessos: '2026-09' }])).toMatch(/^Estimativa: /)
    expect(com([])).toMatch(/^Estimativa: /)
  })
})
