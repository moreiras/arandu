// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { compararAs, compararMunicipios, compararOperadoras, idValido, lerIds, tipoEIds, urlComparar } from './entidades'

describe('comparar entidades', () => {
  it('valida os identificadores de cada tipo e limita a 4 sem repetição', () => {
    expect(idValido('asn', 'AS15169')).toBe('15169')
    expect(idValido('operadora', '12.345.678/0001-90')).toBe('12345678000190')
    expect(idValido('operadora', '123')).toBeNull()
    expect(idValido('municipio', '3205309')).toBe('3205309')
    expect(lerIds('asn', '1,2,2,x,3,4,5')).toEqual(['1', '2', '3', '4'])
  })

  it('os aliases ?asn=, ?operadora= e ?municipio= valem como ?tipo=…&ids=…, e sem nada o tipo é PTT (o /comparar de antes)', () => {
    expect(tipoEIds(new URLSearchParams('asn=15169,13335'))).toEqual({ tipo: 'asn', ids: ['15169', '13335'], alias: true })
    expect(tipoEIds(new URLSearchParams('municipio=3205309,3550308'))).toMatchObject({ tipo: 'municipio', ids: ['3205309', '3550308'] })
    expect(tipoEIds(new URLSearchParams('tipo=operadora&ids=12345678000190'))).toMatchObject({ tipo: 'operadora', ids: ['12345678000190'], alias: false })
    expect(tipoEIds(new URLSearchParams(''))).toEqual({ tipo: 'ixp', ids: [], alias: false })
    expect(tipoEIds(new URLSearchParams('tipo=ixp&ids=SP,rj'))).toMatchObject({ tipo: 'ixp', ids: ['sp', 'rj'] })
    expect(urlComparar('asn', ['1', '2'])).toBe('/comparar?tipo=asn&ids=1,2')
  })

  it('AS: linhas com selo e linha sem dado em nenhum AS some', () => {
    const c = compararAs([
      { asn: 1, name: 'A', is_br: true, global_prefixes_v4_count: 10, global_prefixes_v6_count: 2, ixps_direct: ['sp'], apnic_users: 1000, upstreams_v4: [3356] },
      { asn: 2, name: 'B', is_br: false, global_prefixes_v4_count: 5, global_prefixes_v6_count: 0, ixps_direct: [] },
    ] as any)
    expect(c.colunas.map((x) => x.to)).toEqual(['/asn/1', '/asn/2'])
    const u = c.linhas.find((l) => l.id === 'usuarios')!
    expect(u.celulas).toEqual(['1.000', null]); expect(u.selo).toBe('estimado')
    expect(c.linhas.find((l) => l.id === 'transito')!.selo).toBe('inferido')
    expect(c.linhas.find((l) => l.id === 'aspa')).toBeUndefined()
  })

  it('operadora e município montam o quadro com os números do perfil', () => {
    const o = compararOperadoras([{ cnpj: '1', indicadores: { empresa: 'Alfa', acessos: 5000, share_br: 1.25, posicao_br: 7, var_aa: { pct: 3.5 } }, scm: { asns: [1, 2], municipios: 10 } }, { cnpj: '2', indicadores: { empresa: 'Beta', acessos: 100 } }] as any)
    expect(o.colunas[0].nome).toBe('Alfa'); expect(o.linhas.find((l) => l.id === 'var')!.celulas).toEqual(['+3,5%', null]); expect(o.linhas.find((l) => l.id === 'posicao')!.celulas[0]).toBe('7º')
    const m = compararMunicipios([{ ibge: '1', nome: 'X', uf: 'SP', indicadores: { acessos: 1000, hhi: 2500, n_operadoras: 4 }, territorio: { penetracao: 0.8, km_ptt: 12 } }, { ibge: '2', nome: 'Y', uf: 'RJ', fixo: { acessos: 50, hhi: 10000, operadores_count: 1 } }] as any)
    expect(m.linhas.find((l) => l.id === 'penetracao')!.celulas).toEqual(['80', null])
    expect(m.linhas.find((l) => l.id === 'acessos')!.celulas).toEqual(['1.000', '50'])
  })
})
