// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import {
  converterValor, deUrl, estadoDeReceita, estadoInicial, familia, formatarCelula, linkDoCampo, montarCorpo, operadoresDoCampo, paraUrl,
  type SchemaConsulta,
} from './consulta'

const schema: SchemaConsulta = {
  operators: ['eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'nin', 'contains', 'ncontains', 'exists'],
  aggregate_functions: ['avg', 'count', 'distinct', 'max', 'min', 'sum'],
  recipes: [],
  collections: {
    operadoras: {
      key: 'cnpj', description: 'Operadoras', geo: { lat: 'lat', lon: 'lon' },
      fields: [
        { name: 'cnpj', type: 'string' }, { name: 'empresa', type: 'string' }, { name: 'acessos', type: 'int' }, { name: 'com_asn', type: 'bool' },
        { name: 'velocidade_media_mbps', type: 'number' }, { name: 'asns', type: 'array[int]' }, { name: 'meio', type: 'string', enum: ['Fibra', 'Rádio'] },
      ],
    },
    ixps: { key: 'code', description: 'PTTs', fields: [{ name: 'code', type: 'string' }, { name: 'uf', type: 'string' }] },
  },
}
const campo = (n: string) => schema.collections.operadoras.fields.find((f) => f.name === n)

describe('tipos e operadores', () => {
  it('famílias', () => {
    expect(familia('int')).toBe('numero'); expect(familia('number')).toBe('numero'); expect(familia('bool')).toBe('bool')
    expect(familia('array[int]')).toBe('lista'); expect(familia('string')).toBe('texto'); expect(familia('object')).toBe('objeto')
  })
  it('cada tipo só oferece operadores que fazem sentido', () => {
    expect(operadoresDoCampo(campo('acessos'))).toContain('gte')
    expect(operadoresDoCampo(campo('empresa'))).not.toContain('gt')
    expect(operadoresDoCampo(campo('com_asn'))).toEqual(['eq', 'ne', 'exists'])
    expect(operadoresDoCampo(campo('asns'))).toEqual(['contains', 'ncontains', 'exists'])
  })
})

describe('conversão de valores', () => {
  it('número, vírgula decimal, booleano, lista e exists', () => {
    expect(converterValor(campo('acessos'), 'gte', '5000')).toBe(5000)
    expect(converterValor(campo('velocidade_media_mbps'), 'lt', '12,5')).toBe(12.5)
    expect(converterValor(campo('com_asn'), 'eq', 'false')).toBe(false)
    expect(converterValor(campo('com_asn'), 'eq', 'sim')).toBe(true)
    expect(converterValor(campo('meio'), 'in', 'Fibra, Rádio')).toEqual(['Fibra', 'Rádio'])
    expect(converterValor(campo('acessos'), 'in', '1, 2,3')).toEqual([1, 2, 3])
    expect(converterValor(campo('asns'), 'contains', '265394')).toBe(265394)     // pertinência em array[int] compara número
    expect(converterValor(campo('empresa'), 'exists', 'false')).toBe(false)
    expect(converterValor(campo('empresa'), 'exists', '')).toBe(true)
  })
  it('valor que não converte vira mensagem para o usuário', () => {
    expect(() => converterValor(campo('acessos'), 'gte', 'muitos')).toThrow(/não é um número/)
    expect(() => converterValor(campo('empresa'), 'eq', '  ')).toThrow(/informe um valor/)
    expect(() => converterValor(campo('meio'), 'in', ' , ')).toThrow(/ao menos um valor/)
  })
})

describe('montarCorpo', () => {
  it('uma condição vira predicado; várias, and/or; incompletas somem', () => {
    const e = estadoInicial('operadoras')
    e.condicoes = [{ campo: 'acessos', op: 'gte', valor: '5000' }, { campo: '', op: 'eq', valor: 'x' }]
    expect(montarCorpo(e, schema).filter).toEqual({ field: 'acessos', op: 'gte', value: 5000 })
    e.condicoes.push({ campo: 'com_asn', op: 'eq', valor: 'false' })
    e.juncao = 'or'
    expect((montarCorpo(e, schema).filter as { or: unknown[] }).or).toHaveLength(2)
  })
  it('select, sort, limit, page e near', () => {
    const e = estadoInicial('operadoras')
    e.colunas = ['empresa', 'acessos']; e.ordem = { campo: 'acessos', dir: 'desc' }; e.limite = 50; e.pagina = 3; e.perto = { lugar: ' Vitória ', raio: 20 }
    expect(montarCorpo(e, schema)).toEqual({ select: ['empresa', 'acessos'], sort: [{ field: 'acessos', dir: 'desc' }], limit: 50, page: 3, near: { place: 'Vitória', radius_km: 20 } })
  })
  it('agregação: group_by e funções; count não precisa de campo; página 1 não vai no corpo', () => {
    const e = estadoInicial('operadoras')
    e.modo = 'agregar'; e.agrupar = ['meio']; e.agregados = [{ fn: 'count', campo: '' }, { fn: 'sum', campo: 'acessos' }, { fn: 'avg', campo: '' }]
    const c = montarCorpo(e, schema)
    expect(c.group_by).toEqual(['meio'])
    expect(c.aggregate).toEqual([{ fn: 'count' }, { fn: 'sum', field: 'acessos', as: 'sum_acessos' }])
    expect(c).not.toHaveProperty('select')
    expect(c).not.toHaveProperty('page')
  })
})

describe('URL', () => {
  it('ida e volta preserva a consulta (inclusive acentos)', () => {
    const e = estadoInicial('operadoras')
    e.condicoes = [{ campo: 'empresa', op: 'contains', valor: 'Fibra São José' }]
    e.colunas = ['empresa']; e.ordem = { campo: 'acessos', dir: 'asc' }; e.limite = 100; e.perto = { lugar: 'Vitória', raio: 30 }
    const volta = deUrl(paraUrl(e), schema)
    expect(volta).toEqual(e)
  })
  it('defeitos nunca lançam: coleção desconhecida = null; lixo no q = consulta inicial; campos inexistentes são descartados', () => {
    expect(deUrl(new URLSearchParams('c=nada'), schema)).toBeNull()
    expect(deUrl(new URLSearchParams(''), schema)).toBeNull()
    expect(deUrl(new URLSearchParams('c=ixps&q=%%%'), schema)).toEqual(estadoInicial('ixps'))
    const e = estadoInicial('ixps'); e.condicoes = [{ campo: 'uf', op: 'eq', valor: 'ES' }, { campo: 'fantasma', op: 'eq', valor: '1' }]; e.colunas = ['code', 'fantasma']
    const v = deUrl(paraUrl(e), schema)!
    expect(v.condicoes).toHaveLength(1)
    expect(v.colunas).toEqual(['code'])
  })
  it('limite fora da lista volta ao padrão', () => {
    const e = { ...estadoInicial('ixps'), limite: 7 }
    expect(deUrl(paraUrl(e), schema)!.limite).toBe(25)
  })
})

describe('receitas', () => {
  it('filtro composto, select, sort e limit viram o estado da tela', () => {
    const r = estadoDeReceita({
      collection: 'operadoras', filter: { and: [{ field: 'acessos', op: 'gte', value: 5000 }, { field: 'com_asn', op: 'eq', value: false }] },
      select: ['empresa', 'cnpj'], sort: [{ field: 'acessos', dir: 'desc' }], limit: 50,
    }, schema)!
    expect(r.avisos).toEqual([])
    expect(r.estado.condicoes).toEqual([{ campo: 'acessos', op: 'gte', valor: '5000' }, { campo: 'com_asn', op: 'eq', valor: 'false' }])
    expect(r.estado.ordem).toEqual({ campo: 'acessos', dir: 'desc' })
    expect(r.estado.limite).toBe(50)
    expect(montarCorpo(r.estado, schema).filter).toEqual({ and: [{ field: 'acessos', op: 'gte', value: 5000 }, { field: 'com_asn', op: 'eq', value: false }] })
  })
  it('near por lugar entra; filtro aninhado e coleção desconhecida são tratados sem erro', () => {
    expect(estadoDeReceita({ collection: 'ixps', near: { place: 'Vitória', radius_km: 20 } }, schema)!.estado.perto).toEqual({ lugar: 'Vitória', raio: 20 })
    const aninhado = estadoDeReceita({ collection: 'ixps', filter: { and: [{ or: [{ field: 'uf', op: 'eq', value: 'ES' }] }] } }, schema)!
    expect(aninhado.avisos[0]).toMatch(/aninhado/)
    expect(estadoDeReceita({ collection: 'inexistente' }, schema)).toBeNull()
  })
  it('agregação da receita liga o modo agregar', () => {
    const r = estadoDeReceita({ collection: 'operadoras', group_by: ['meio'], aggregate: [{ fn: 'count' }, { fn: 'avg', field: 'acessos' }] }, schema)!
    expect(r.estado.modo).toBe('agregar')
    expect(r.estado.agrupar).toEqual(['meio'])
    expect(r.estado.agregados).toEqual([{ fn: 'count', campo: '' }, { fn: 'avg', campo: 'acessos' }])
  })
})

describe('resultado', () => {
  it('links por campo-chave', () => {
    expect(linkDoCampo('asns', 'asn', 8167)).toBe('/asn/8167')
    expect(linkDoCampo('operadoras', 'cnpj', '04573288000144')).toBe('/operadora/04573288000144')
    expect(linkDoCampo('acessos_municipio', 'ibge', '3550308')).toBe('/municipio/3550308')
    expect(linkDoCampo('ixps', 'code', 'sp')).toBe('/ixp/sp')
    expect(linkDoCampo('external_ixps', 'code', 'amsix')).toBe('/ixp-externo/amsix')
    expect(linkDoCampo('prefixes', 'prefix', '177.75.0.0/16')).toBe('/prefixo/177.75.0.0/16')
    expect(linkDoCampo('operadoras', 'empresa', 'X')).toBeNull()
    expect(linkDoCampo('asns', 'asn', null)).toBeNull()
  })
  it('células', () => {
    expect(formatarCelula(null)).toBe('—'); expect(formatarCelula(true)).toBe('sim'); expect(formatarCelula(12345)).toBe('12.345')
    expect(formatarCelula(1.2345)).toBe('1,23'); expect(formatarCelula([1, 2, 3])).toBe('1, 2, 3')
    expect(formatarCelula([1, 2, 3, 4, 5, 6, 7, 8])).toBe('1, 2, 3, 4, 5, 6 … (+2)')
  })
})

describe('float, array sem tipo interno e list (EXP-E1, EXP-E2)', () => {
  const f = (name: string, type: string, extra: Record<string, unknown> = {}) => ({ name, type, ...extra })
  it('float é número: operadores de comparação e valor numérico (receita 20: penetracao lt 0.5)', () => {
    expect(familia('float')).toBe('numero')
    expect(operadoresDoCampo(f('penetracao', 'float'))).toContain('lt')
    expect(converterValor(f('penetracao', 'float'), 'lt', '0.5')).toBe(0.5)
    expect(converterValor(f('rov_validates_pct', 'float'), 'gt', '90')).toBe(90)
  })
  it('bordas do float: vírgula decimal, lista `in` com números, valor vazio e texto inválido', () => {
    expect(converterValor(f('penetracao', 'float'), 'lt', '0,5')).toBe(0.5)
    expect(converterValor(f('penetracao', 'float'), 'in', '0.5, 1')).toEqual([0.5, 1])
    expect(() => converterValor(f('penetracao', 'float'), 'lt', '')).toThrow(/informe um valor/)
    expect(() => converterValor(f('penetracao', 'float'), 'lt', 'abc')).toThrow(/não é um número/)
  })
  it('array sem tipo interno: inteiro vira número (omissao_sici.asns contém 28198), o resto fica texto', () => {
    expect(converterValor(f('asns', 'array'), 'contains', '28198')).toBe(28198)
    expect(converterValor(f('sinais', 'array'), 'contains', 'S1')).toBe('S1')
    expect(converterValor(f('asns', 'array[int]'), 'contains', '28198')).toBe(28198)
    expect(converterValor(f('raizes', 'array[string]'), 'contains', '01234567')).toBe('01234567')
  })
  it('o exemplo do catálogo dá o tipo interno de um array sem tipo', () => {
    expect(converterValor(f('raizes', 'array', { example: ['01234567'] }), 'contains', '01234567')).toBe('01234567')
    expect(converterValor(f('asns', 'array', { example: [64500] }), 'contains', '64501')).toBe(64501)
  })
  it('list é lista: `contém` disponível', () => {
    expect(familia('list')).toBe('lista')
    expect(operadoresDoCampo(f('prefixos_amostra', 'list'))).toEqual(['contains', 'ncontains', 'exists'])
  })
})
