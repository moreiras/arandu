// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { COLETA_ANATEL, faixaHhi, NOTA_ATUALIZACAO_MULTAS, NOTA_COLETA_ANATEL, NOTA_FAIXAS_HHI, NOTA_MULTA_CONSTITUIDA, NOTA_REDE_VIRTUAL, ROTULO_FAIXA_HHI } from './referencias'

describe('referências normativas na tela (D11)', () => {
  it('faixas de HHI: limites do projeto, iguais ao produto (1.500 e 2.500)', () => {
    expect([1, 1499, 1500, 2499, 2500, 10000].map(faixaHhi)).toEqual(['competitivo', 'competitivo', 'moderado', 'moderado', 'concentrado', 'concentrado'])
    expect(Object.values(ROTULO_FAIXA_HHI).join(' ')).not.toMatch(/competitiv|perigo|alto risco/i)
  })

  it('HHI: método do projeto, CADE citado só com ano, sem número de seção', () => {
    expect(NOTA_FAIXAS_HHI).toMatch(/método do projeto/)
    expect(NOTA_FAIXAS_HHI).toMatch(/CADE \(2016\)/)
    expect(NOTA_FAIXAS_HHI).not.toMatch(/seção|item \d|art\./i)
  })

  it('coleta da Anatel: base vigente e Res. 774/2025; sem qualificar infração', () => {
    expect(COLETA_ANATEL).toMatch(/Coleta de Dados/)
    expect(NOTA_COLETA_ANATEL).toMatch(/Resolução Anatel nº 774\/2025/)
    for (const t of [NOTA_COLETA_ANATEL, NOTA_REDE_VIRTUAL, NOTA_ATUALIZACAO_MULTAS, NOTA_MULTA_CONSTITUIDA])
      expect(t).not.toMatch(/omi[s]s|infra[çc]|irregular|sanç|dispensad/i)
  })

  it('rede virtual: acessos declarados pela prestadora de origem (RGST, Res. 777/2025)', () => {
    expect(NOTA_REDE_VIRTUAL).toMatch(/prestadora de origem/)
    expect(NOTA_REDE_VIRTUAL).toMatch(/777\/2025/)
  })

  it('multas: Selic e 0,33% ao dia até 20%', () => {
    expect(NOTA_ATUALIZACAO_MULTAS).toMatch(/Selic/)
    expect(NOTA_ATUALIZACAO_MULTAS).toMatch(/0,33% ao dia até 20%/)
  })
})
