// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { montarLongeDePtt, montarSemSici } from './derivados'

const ptts = [{ codigo: 'vix', nome: 'Vitória', lonlat: [-40.3, -20.3] as [number, number] }]
const g = (ibge: string, acessos: number) => ({ key: { ibge, municipio: `M${ibge}`, uf: 'XX' }, acessos })

describe('montarLongeDePtt', () => {
  it('fica só com quem passa de 100 km, ordena por acessos e conta o total', () => {
    const cent = { a: [-40.34, -20.31], b: [-64.8, -3.2], c: [-60, -3], d: [-45, -20] } as Record<string, [number, number]>
    const r = montarLongeDePtt([g('a', 90000), g('b', 6000), g('c', 20000), g('d', 7000)], cent, ptts)
    expect(r.items.map((i) => i.ibge)).toEqual(['c', 'd', 'b'])
    expect(r.total).toBe(3)
    expect(r.items[0].km).toBeGreaterThan(100)
  })
  it('município sem centróide não entra; sem PTT ou sem centróides devolve vazio', () => {
    expect(montarLongeDePtt([g('z', 1)], { a: [0, 0] }, ptts).items).toEqual([])
    expect(montarLongeDePtt([g('a', 1)], undefined, ptts).total).toBe(0)
    expect(montarLongeDePtt([g('a', 1)], { a: [0, 0] }, []).total).toBe(0)
  })
  it('limita a cinco linhas e informa o total', () => {
    const cent = Object.fromEntries(Array.from({ length: 8 }, (_, i) => [`m${i}`, [-60, -3] as [number, number]]))
    const r = montarLongeDePtt(Array.from({ length: 8 }, (_, i) => g(`m${i}`, 1000 + i)), cent, ptts)
    expect(r.items).toHaveLength(5)
    expect(r.total).toBe(8)
  })
})

describe('montarSemSici', () => {
  it('cruza por CNPJ, ordena por usuários e usa o AS maior de cada CNPJ', () => {
    const asns = [
      { asn: 1, cnpj: 'A', apnic_users: 10 }, { asn: 2, cnpj: 'A', apnic_users: 500 },
      { asn: 3, cnpj: 'B', apnic_users: 300 }, { asn: 4, cnpj: 'C', apnic_users: 9000 },
    ]
    const r = montarSemSici(asns, [{ cnpj: 'A', razao_social: 'Alfa' }, { cnpj: 'B' }])
    expect(r.items.map((i) => [i.cnpj, i.apnic_users, i.empresa])).toEqual([['A', 500, 'Alfa'], ['B', 300, 'B']])
    expect(r.total).toBe(2)
  })
})
