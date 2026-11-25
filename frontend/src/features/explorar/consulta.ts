// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Núcleo do explorador de consultas: estado da tela ↔ corpo de `POST /query/{collection}` ↔ URL. Sem React. */

export type Operador = 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'in' | 'nin' | 'contains' | 'ncontains' | 'exists'

export interface CampoSchema { name: string; type: string; description?: string; example?: unknown; enum?: unknown[] }
export interface ColecaoSchema { key?: string; description: string; fields: CampoSchema[]; geo?: { lat: string; lon: string } }
export interface Receita { pergunta: string; ferramenta?: string; args?: Record<string, unknown>; nota?: string }
export interface SchemaConsulta {
  operators: string[]
  aggregate_functions: string[]
  collections: Record<string, ColecaoSchema>
  recipes: Receita[]
}

export interface Condicao { campo: string; op: Operador; valor: string }
export interface Agregado { fn: string; campo: string }

export interface EstadoConsulta {
  colecao: string
  /** `lista` devolve linhas; `agregar` agrupa e calcula. */
  modo: 'lista' | 'agregar'
  juncao: 'and' | 'or'
  condicoes: Condicao[]
  colunas: string[]
  ordem: { campo: string; dir: 'asc' | 'desc' } | null
  limite: number
  pagina: number
  perto: { lugar: string; raio: number } | null
  agrupar: string[]
  agregados: Agregado[]
  /** Início do histórico (AAAA-MM-DD), só para as coleções de `COLECOES_HISTORICO`: sem login o servidor exige `de` (EXP-E4). */
  de?: string
}

/** Coleções de histórico: não dependem de `date`, e o `de` delimita o período. */
export const COLECOES_HISTORICO = ['eventos', 'series_asn']
const DATA_ISO = /^\d{4}-\d{2}-\d{2}$/

export const LIMITES = [10, 25, 50, 100, 250, 500, 1000]

export function estadoInicial(colecao: string): EstadoConsulta {
  return { colecao, modo: 'lista', juncao: 'and', condicoes: [], colunas: [], ordem: null, limite: 25, pagina: 1, perto: null, agrupar: [], agregados: [{ fn: 'count', campo: '' }] }
}

const OPS_TEXTO: Operador[] = ['eq', 'ne', 'contains', 'ncontains', 'in', 'nin', 'exists']
const OPS_NUM: Operador[] = ['eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'nin', 'exists']
const OPS_BOOL: Operador[] = ['eq', 'ne', 'exists']
const OPS_LISTA: Operador[] = ['contains', 'ncontains', 'exists']

export const ROTULO_OP: Record<Operador, string> = {
  eq: 'é igual a', ne: 'é diferente de', gt: 'é maior que', gte: 'é maior ou igual a', lt: 'é menor que', lte: 'é menor ou igual a',
  in: 'está entre (lista)', nin: 'não está entre (lista)', contains: 'contém', ncontains: 'não contém', exists: 'tem valor',
}

/** Famílias de tipo do schema: `string`, `int`, `float`, `number`, `bool`, `array[...]` (ou `array`/`list` sem tipo interno), `object`.
 * `float` caía em texto e o valor ia como string ("0.5"), o que dava zero falso (EXP-E1). */
export function familia(tipo: string): 'texto' | 'numero' | 'bool' | 'lista' | 'objeto' {
  if (tipo.startsWith('array') || tipo === 'list') return 'lista'
  if (tipo === 'int' || tipo === 'float' || tipo === 'number') return 'numero'
  if (tipo === 'bool') return 'bool'
  if (tipo === 'object') return 'objeto'
  return 'texto'
}

export function operadoresDoCampo(c: CampoSchema | undefined): Operador[] {
  if (!c) return OPS_TEXTO
  switch (familia(c.type)) {
    case 'numero': return OPS_NUM
    case 'bool': return OPS_BOOL
    case 'lista': return OPS_LISTA
    case 'objeto': return ['exists']
    default: return OPS_TEXTO
  }
}

/** Tipo dos itens de um campo lista: o de `array[T]`; sem ele (`array`, `list`), o do `example` do catálogo; senão `undefined` (inferir). */
function tipoInterno(c: CampoSchema): string | undefined {
  const m = /^array\[(.+)\]$/.exec(c.type)
  if (m) return m[1]
  const ex = Array.isArray(c.example) ? c.example[0] : undefined
  if (typeof ex === 'number') return 'number'
  if (typeof ex === 'string') return 'string'
  return undefined
}

function escalar(texto: string, c: CampoSchema | undefined, tipoLista?: string): string | number | boolean {
  const lista = !!c && familia(c.type) === 'lista'
  const t = texto.trim()
  // item de lista sem tipo declarado: inteiro vira número (ASNs em `sem_declaracao_sici.asns`, EXP-E2), o resto fica texto
  if (lista && !tipoLista) return /^-?\d+$/.test(t) ? Number(t) : t
  const fam = tipoLista ? familia(tipoLista) : c ? familia(c.type) : 'texto'
  if (fam === 'numero') {
    // vírgula decimal ("0,5") aceita; separador de milhar não (ambíguo)
    const n = t === '' ? NaN : Number(t.replace(',', '.'))
    if (!Number.isFinite(n)) throw new Error(`"${texto}" não é um número`)
    return n
  }
  if (fam === 'bool') return /^(true|sim|1|verdadeiro)$/i.test(t)
  return t
}

/** Valor digitado → valor do predicado (número, booleano, lista…). Lança `Error` com mensagem para o usuário se não converter. */
export function converterValor(c: CampoSchema | undefined, op: Operador, texto: string): unknown {
  if (op === 'exists') return !/^(false|não|nao|0)$/i.test(texto.trim() || 'true')
  const interno = c && familia(c.type) === 'lista' ? tipoInterno(c) : undefined
  if (op === 'in' || op === 'nin') {
    const itens = texto.split(',').map((x) => x.trim()).filter(Boolean)
    if (itens.length === 0) throw new Error('informe ao menos um valor na lista')
    return itens.map((x) => escalar(x, c, interno))
  }
  if (texto.trim() === '' && !(c && familia(c.type) === 'bool')) throw new Error('informe um valor')
  return escalar(texto, c, interno)
}

export interface Predicado { field: string; op: Operador; value: unknown }

/** Cálculos que vão ao servidor (`count` sem campo e os que têm campo) com o nome que a resposta lhes dá (`as`). */
function calculos(e: EstadoConsulta): Array<{ fn: string; field?: string; as?: string }> {
  const ags = e.agregados.filter((a) => a.fn === 'count' || a.campo)
  return (ags.length ? ags : [{ fn: 'count', campo: '' }]).map((a) => (a.campo ? { fn: a.fn, field: a.campo, as: `${a.fn}_${a.campo}` } : { fn: a.fn }))
}

/** Chaves por que a agregação pode ser ordenada: os campos de `group_by` e os nomes dos cálculos (`count`, `sum_acessos`). */
export function chavesDeOrdemNaAgregacao(e: EstadoConsulta): string[] {
  return [...e.agrupar, ...calculos(e).map((c) => c.as ?? c.fn)]
}

/** Estado → corpo da consulta. Condições incompletas (campo vazio) são ignoradas; valores inválidos lançam `Error`. */
export function montarCorpo(e: EstadoConsulta, schema: SchemaConsulta): Record<string, unknown> {
  const col = schema.collections[e.colecao]
  const campo = (n: string) => col?.fields.find((f) => f.name === n)
  const preds: Predicado[] = e.condicoes.filter((c) => c.campo).map((c) => ({ field: c.campo, op: c.op, value: converterValor(campo(c.campo), c.op, c.valor) }))
  const corpo: Record<string, unknown> = {}
  if (preds.length === 1) corpo.filter = preds[0]
  else if (preds.length > 1) corpo.filter = { [e.juncao]: preds }
  if (e.perto && e.perto.lugar.trim()) corpo.near = { place: e.perto.lugar.trim(), radius_km: e.perto.raio }
  if (e.modo === 'agregar') {
    if (e.agrupar.length) corpo.group_by = e.agrupar
    corpo.aggregate = calculos(e)
  } else if (e.colunas.length) corpo.select = e.colunas
  // na agregação o servidor ordena os grupos por campo de `group_by` ou por cálculo; um campo da coleção fora disso seria recusado
  if (e.ordem?.campo && (e.modo !== 'agregar' || chavesDeOrdemNaAgregacao(e).includes(e.ordem.campo))) corpo.sort = [{ field: e.ordem.campo, dir: e.ordem.dir }]
  corpo.limit = e.limite
  if (e.de && COLECOES_HISTORICO.includes(e.colecao)) {
    if (!DATA_ISO.test(e.de)) throw new Error('"a partir de" deve ser uma data AAAA-MM-DD')
    corpo.de = e.de
  }
  if (e.pagina > 1) corpo.page = e.pagina
  return corpo
}

// ---- URL ------------------------------------------------------------------

function paraBase64Url(s: string): string {
  const bytes = new TextEncoder().encode(s)
  let bin = ''
  bytes.forEach((b) => { bin += String.fromCharCode(b) })
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function deBase64Url(s: string): string {
  const bin = atob(s.replace(/-/g, '+').replace(/_/g, '/'))
  return new TextDecoder().decode(Uint8Array.from(bin, (c) => c.charCodeAt(0)))
}

/**
 * Estado → parâmetros de URL (`c` = coleção, `q` = o resto em base64url, `date` = snapshot): a consulta inteira fica no endereço e pode ser
 * compartilhada. Com a data, o link reabre o mesmo snapshot depois que sai um novo.
 */
export function paraUrl(e: EstadoConsulta, date?: string | null): URLSearchParams {
  const { colecao, ...resto } = e
  const p = new URLSearchParams()
  p.set('c', colecao)
  p.set('q', paraBase64Url(JSON.stringify(resto)))
  if (date) p.set('date', date)
  return p
}

/** Parâmetros de URL → estado. Qualquer defeito (parâmetro ausente, JSON quebrado) volta ao estado inicial da coleção, nunca lança. */
export function deUrl(p: URLSearchParams, schema: SchemaConsulta): EstadoConsulta | null {
  const c = p.get('c')
  if (!c || !schema.collections[c]) return null
  const base = estadoInicial(c)
  const q = p.get('q')
  if (!q) return base
  try {
    const o = JSON.parse(deBase64Url(q)) as Partial<EstadoConsulta>
    const nomes = new Set(schema.collections[c].fields.map((f) => f.name))
    return {
      ...base,
      modo: o.modo === 'agregar' ? 'agregar' : 'lista',
      juncao: o.juncao === 'or' ? 'or' : 'and',
      condicoes: (o.condicoes ?? []).filter((x) => x && typeof x.campo === 'string' && nomes.has(x.campo) && typeof x.op === 'string').map((x) => ({ campo: x.campo, op: x.op, valor: String(x.valor ?? '') })),
      colunas: (o.colunas ?? []).filter((n) => nomes.has(n)),
      ordem: o.ordem && nomes.has(o.ordem.campo) ? { campo: o.ordem.campo, dir: o.ordem.dir === 'asc' ? 'asc' : 'desc' } : null,
      limite: LIMITES.includes(Number(o.limite)) ? Number(o.limite) : base.limite,
      pagina: Math.max(1, Number(o.pagina) || 1),
      perto: o.perto && typeof o.perto.lugar === 'string' ? { lugar: o.perto.lugar, raio: Number(o.perto.raio) || 20 } : null,
      agrupar: (o.agrupar ?? []).filter((n) => nomes.has(n)),
      de: typeof o.de === 'string' && DATA_ISO.test(o.de) && COLECOES_HISTORICO.includes(c) ? o.de : undefined,
      agregados: (o.agregados ?? base.agregados).filter((a) => a && typeof a.fn === 'string' && schema.aggregate_functions.includes(a.fn)).map((a) => ({ fn: a.fn, campo: nomes.has(a.campo) ? a.campo : '' })),
    }
  } catch {
    return base
  }
}

// ---- receitas ---------------------------------------------------------------

function achatar(f: unknown): Predicado[] | { junc: 'and' | 'or'; itens: Predicado[] } | null {
  if (!f || typeof f !== 'object') return null
  const o = f as Record<string, unknown>
  if (typeof o.field === 'string') return [{ field: o.field, op: o.op as Operador, value: o.value }]
  for (const j of ['and', 'or'] as const) {
    if (Array.isArray(o[j]) && (o[j] as unknown[]).every((x) => x && typeof (x as Record<string, unknown>).field === 'string')) return { junc: j, itens: o[j] as Predicado[] }
  }
  return null
}

/** Corpo de uma receita do `/schema` → estado da tela (o que não couber — filtros aninhados — vira um aviso, não um erro). */
export function estadoDeReceita(args: Record<string, unknown>, schema: SchemaConsulta): { estado: EstadoConsulta; avisos: string[] } | null {
  const colecao = String(args.collection ?? '')
  if (!schema.collections[colecao]) return null
  const avisos: string[] = []
  const e = estadoInicial(colecao)
  const a = achatar(args.filter)
  if (args.filter && !a) avisos.push('o filtro desta receita é aninhado demais para o construtor e foi ignorado')
  const lista = Array.isArray(a) ? a : a ? a.itens : []
  if (a && !Array.isArray(a)) e.juncao = a.junc
  e.condicoes = lista.map((p) => ({ campo: p.field, op: p.op, valor: Array.isArray(p.value) ? p.value.join(', ') : String(p.value ?? '') }))
  if (Array.isArray(args.select)) e.colunas = args.select.map(String)
  const s = Array.isArray(args.sort) ? (args.sort[0] as { field?: string; dir?: string } | undefined) : undefined
  if (s?.field) e.ordem = { campo: s.field, dir: s.dir === 'asc' ? 'asc' : 'desc' }
  if (LIMITES.includes(Number(args.limit))) e.limite = Number(args.limit)
  else if (typeof args.limit === 'number') e.limite = LIMITES.find((l) => l >= (args.limit as number)) ?? 1000
  const n = args.near as { place?: string; radius_km?: number } | undefined
  if (n?.place) e.perto = { lugar: n.place, raio: n.radius_km ?? 20 }
  else if (args.near) avisos.push('a receita usa um ponto de referência que o construtor não edita; foi ignorado')
  if (Array.isArray(args.group_by) || Array.isArray(args.aggregate)) {
    e.modo = 'agregar'
    e.agrupar = ((args.group_by as string[]) ?? []).map(String)
    const ag = ((args.aggregate as Array<{ fn: string; field?: string }>) ?? []).map((x) => ({ fn: x.fn, campo: x.field ?? '' }))
    if (ag.length) e.agregados = ag
  }
  return { estado: e, avisos }
}

// ---- resultado ----------------------------------------------------------------

/** Para onde leva o valor de um campo-chave (null = sem link). */
export function linkDoCampo(colecao: string, campo: string, valor: unknown): string | null {
  if (valor == null || valor === '') return null
  const v = encodeURIComponent(String(valor))
  if (campo === 'asn') return `/asn/${v}`
  if (campo === 'cnpj') return `/operadora/${v}`
  if (campo === 'ibge') return `/municipio/${v}`
  if (campo === 'code' && colecao === 'ixps') return `/ixp/${v}`
  if (campo === 'code' && colecao === 'external_ixps') return `/ixp-externo/${v}`
  if (campo === 'prefix') return `/prefixo/${String(valor)}`
  return null
}

export function formatarCelula(v: unknown): string {
  if (v == null) return '—'
  if (typeof v === 'number') return v.toLocaleString('pt-BR', { maximumFractionDigits: Number.isInteger(v) ? 0 : 2 })
  if (typeof v === 'boolean') return v ? 'sim' : 'não'
  if (Array.isArray(v)) return v.length > 6 ? `${v.slice(0, 6).join(', ')} … (+${v.length - 6})` : v.join(', ')
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}
