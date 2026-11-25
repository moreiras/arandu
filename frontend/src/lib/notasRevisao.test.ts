// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import relatorio from './notasRevisao.fixture.json'
import { NOTAS_REVISAO, notasParaTipos } from './notasRevisao'

// A fixture é o recorte do relatório da regeneração (relatorio-d7-2026-11-25.json): contagens de 2026-07-05 e a soma das 20 datas.
type Contagem = { antes: number; depois: number }
const emData = relatorio.em_2026_07_05 as Record<string, Contagem>
const total = relatorio.total as Record<string, Contagem>

describe('notas de revisão datadas', () => {
  const nota = NOTAS_REVISAO.find((n) => n.data === '2026-11-25')!

  it('a nota de 2026-11-25 existe e traz a versão da regra do relatório', () => {
    expect(nota).toBeTruthy()
    expect(nota.regra).toBe(relatorio.regra)
    expect(nota.regra).toBe(2)
  })

  it('as contagens de 2026-07-05 batem com o relatório', () => {
    expect(nota.em.data).toBe('2026-07-05')
    expect(nota.em.contagens.length).toBe(Object.keys(emData).length)
    for (const c of nota.em.contagens) expect({ antes: c.antes, depois: c.depois }, c.tipo).toEqual(emData[c.tipo])
  })

  it('as somas das datas regeneradas batem com o relatório', () => {
    expect(nota.total.datas).toBe(relatorio.n_datas)
    expect(`${nota.total.de}..${nota.total.ate}`).toBe(relatorio.datas)
    for (const c of nota.total.contagens) expect({ antes: c.antes, depois: c.depois }, c.tipo).toEqual(total[c.tipo])
  })

  it('só os tipos citados na nota como alterados mudam no relatório', () => {
    const mudam = Object.keys(total).filter((t) => total[t].antes !== total[t].depois).sort()
    expect(nota.total.contagens.map((c) => c.tipo).sort()).toEqual(mudam)
    for (const t of ['aspa_ganho', 'rpki_invalido_novo']) expect(total[t].antes).toBe(total[t].depois)
  })

  it('os tipos afetados cobrem ROA, ASPA e RPKI', () => {
    expect(nota.tipos).toEqual(expect.arrayContaining(Object.keys(total)))
  })

  it('o filtro de tipo decide se a nota aparece', () => {
    expect(notasParaTipos([]).length).toBe(1)
    expect(notasParaTipos(['roa_perdido']).length).toBe(1)
    expect(notasParaTipos(['asn_novo', 'ixp_saida']).length).toBe(0)
  })
})
