// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { eventosDaSerie } from './eventosSerie'
import type { SerieMercadoMunicipio } from '../../types/api'

const serie = (over: Partial<SerieMercadoMunicipio>): SerieMercadoMunicipio => ({ snapshot_date: '2026-11-22', mes_referencia: '2026-09', meses: ['2026-07', '2026-08', '2026-09'], fonte: 'x', parametros: { meses: 3, lideres: 4 },
  acessos: [100, 100, 100], hhi: [1, 1, 1], lideres: [], ...over })

describe('eventosDaSerie', () => {
  it('marca o mês em que o CNPJ deixa de declarar e o mês em que volta', () => {
    const s = serie({ meses: ['2026-06', '2026-07', '2026-08', '2026-09'], acessos: [100, 100, 100, 100], lideres: [{ cnpj: '1', empresa: 'XZOON', share: [97, 97, null, 90] }] })
    expect(eventosDaSerie(s).map((e) => [e.mes, e.tipo])).toEqual([['2026-08', 'sem_declaracao'], ['2026-09', 'declarou_de_novo']])
    expect(eventosDaSerie(s)[0].texto).toBe('XZOON: sem declaração em 2026-08')
  })
  it('mês sem dado no município não é evento', () => {
    const s = serie({ acessos: [100, null, 100], lideres: [{ cnpj: '1', empresa: '', share: [50, null, 50] }] })
    expect(eventosDaSerie(s)).toEqual([])
  })
  it('sem ponto vazio, sem evento', () => {
    expect(eventosDaSerie(serie({ lideres: [{ cnpj: '1', empresa: 'A', share: [50, 51, 52] }] }))).toEqual([])
  })
})
