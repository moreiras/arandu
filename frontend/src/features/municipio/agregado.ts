// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { PerfilMunicipio, SiciOperador, ErbsMunicipio, FustMunicipio, IndicadoresMunicipio, TerritorioMunicipio, SiciMunicipioDetalhe, MovelMunicipioDetalhe, ErbsGeracoes } from '../../types/api'
import type { MunicipioCtx } from './contexto'

type Fixo = NonNullable<PerfilMunicipio['fixo']>
type Movel = NonNullable<PerfilMunicipio['movel']>

const soma = (xs: Array<number | null | undefined>) => xs.reduce<number>((t, x) => t + (x ?? 0), 0)
const r1 = (v: number) => Math.round(v * 10) / 10

/** Junta os operadores por CNPJ (acessos somados, ASNs unidos) e recalcula a participação sobre o total do conjunto. */
function juntarOperadores(listas: SiciOperador[][]): { operadores: SiciOperador[]; total: number; hhi: number; shareMaior: number } {
  const por = new Map<string, SiciOperador>()
  for (const op of listas.flat()) {
    const a = por.get(op.cnpj)
    if (!a) por.set(op.cnpj, { ...op, asns: [...op.asns] })
    else { a.acessos += op.acessos; for (const n of op.asns) if (!a.asns.includes(n)) a.asns.push(n); if (!a.empresa && op.empresa) a.empresa = op.empresa }
  }
  const total = soma([...por.values()].map((o) => o.acessos))
  const ordenados = [...por.values()].sort((x, y) => y.acessos - x.acessos || x.cnpj.localeCompare(y.cnpj))
  const shares = ordenados.map((o) => (total ? (100 * o.acessos) / total : 0))
  return {
    operadores: ordenados.map((o, i) => ({ ...o, share: r1(shares[i]) })), total,
    hhi: Math.round(soma(shares.map((s) => s * s))), shareMaior: shares.length ? r1(Math.max(...shares)) : 0,
  }
}

function somaMapas(ms: Array<Record<string, number> | undefined>): Record<string, number> {
  const r: Record<string, number> = {}
  for (const m of ms) for (const [k, v] of Object.entries(m ?? {})) r[k] = (r[k] ?? 0) + v
  return r
}

function agregarFixo(central: PerfilMunicipio, rotulo: string, itens: Fixo[]): SiciMunicipioDetalhe | undefined {
  if (itens.length === 0) return undefined
  const j = juntarOperadores(itens.map((f) => f.operadores))
  const comFibra = itens.filter((f) => f.fibra != null)
  const acessosComFibra = soma(comFibra.map((f) => f.acessos))
  const fibra = soma(comFibra.map((f) => f.fibra))
  return {
    snapshot_date: central.snapshot_date, mes_referencia: itens[0].mes_referencia, ibge: central.ibge, nome: rotulo, uf: central.uf,
    acessos: soma(itens.map((f) => f.acessos)), pf: soma(itens.map((f) => f.pf)), pj: soma(itens.map((f) => f.pj)), capacidade_mbps: soma(itens.map((f) => f.capacidade_mbps)),
    operadores: j.operadores, operadores_count: j.operadores.length, hhi: j.hhi, share_maior: j.shareMaior,
    ...(comFibra.length && acessosComFibra ? { fibra, fibra_pct: r1((100 * fibra) / acessosComFibra) } : {}),
  }
}

function agregarMovel(central: PerfilMunicipio, rotulo: string, itens: Movel[]): MovelMunicipioDetalhe | undefined {
  if (itens.length === 0) return undefined
  const j = juntarOperadores(itens.map((m) => m.operadores))
  return {
    snapshot_date: central.snapshot_date, mes_referencia: itens[0].mes_referencia, ibge: central.ibge, nome: rotulo, uf: central.uf,
    acessos: soma(itens.map((m) => m.acessos)), pf: soma(itens.map((m) => m.pf)), pj: soma(itens.map((m) => m.pj)),
    operadores: j.operadores, operadores_count: j.operadores.length, hhi: j.hhi, share_maior: j.shareMaior,
  }
}

function agregarTerritorio(central: PerfilMunicipio, rotulo: string, itens: TerritorioMunicipio[]): TerritorioMunicipio | undefined {
  if (itens.length === 0) return undefined
  const dom = soma(itens.map((t) => t.domicilios_projetados ?? t.domicilios))
  const acessos = soma(itens.map((t) => t.acessos))
  const acessosPf = soma(itens.map((t) => t.acessos_pf))
  const naoVisto = soma(itens.map((t) => t.nao_visto))
  const com = <K extends keyof TerritorioMunicipio>(k: K) => itens.some((t) => t[k] != null)
  return {
    ...itens[0], nome: rotulo, uf: central.uf, sem_declaracao_sici: itens.every((t) => t.sem_declaracao_sici),
    populacao: com('populacao') ? soma(itens.map((t) => t.populacao)) : undefined,
    populacao_estimada: com('populacao_estimada') ? soma(itens.map((t) => t.populacao_estimada ?? t.populacao)) : undefined,
    domicilios: com('domicilios') ? soma(itens.map((t) => t.domicilios)) : undefined,
    domicilios_projetados: com('domicilios_projetados') ? soma(itens.map((t) => t.domicilios_projetados ?? t.domicilios)) : undefined,
    acessos, acessos_pf: acessosPf,
    penetracao: dom ? acessos / dom : undefined, penetracao_pf: dom ? acessosPf / dom : undefined,
    domicilios_com_internet_est: com('domicilios_com_internet_est') ? soma(itens.map((t) => t.domicilios_com_internet_est)) : undefined,
    nao_visto: naoVisto, nao_visto_pct: dom ? naoVisto / dom : undefined,
    area_km2: com('area_km2') ? soma(itens.map((t) => t.area_km2)) : undefined,
    // distância ao PTT é do município central, não de um conjunto
    ptt_proximo: undefined, km_ptt: undefined, sem_ptt_proximo: undefined,
  }
}

const populacaoDe = (p: PerfilMunicipio) => p.territorio?.populacao_estimada ?? p.territorio?.populacao

/** Por 10 mil habitantes do conjunto; só se todos os municípios com o dado têm população (senão a razão seria enganosa). */
function por10mil(perfis: PerfilMunicipio[], valor: (p: PerfilMunicipio) => number | null | undefined): number | null {
  const com = perfis.filter((p) => valor(p) != null)
  if (com.length === 0 || com.some((p) => !populacaoDe(p))) return null
  const pop = soma(com.map(populacaoDe))
  return pop ? Math.round((soma(com.map(valor)) * 10000) / pop * 100) / 100 : null
}

function agregarErbs(perfis: PerfilMunicipio[]): ErbsMunicipio | undefined {
  const itens = perfis.filter((p) => p.erbs)
  if (itens.length === 0) return undefined
  const e0 = itens[0].erbs!
  const geracoes = somaMapas(itens.map((p) => p.erbs!.geracoes as unknown as Record<string, number>)) as unknown as ErbsGeracoes
  const por = new Map<string, { cnpj: string | null; marca: string; estacoes: number }>()
  for (const p of itens) for (const o of p.erbs!.operadoras) {
    const k = o.cnpj ?? o.marca
    const a = por.get(k)
    if (a) a.estacoes += o.estacoes
    else por.set(k, { ...o })
  }
  return {
    ...e0, estacoes: soma(itens.map((p) => p.erbs!.estacoes)), geracoes,
    por_10mil_hab: por10mil(itens, (p) => p.erbs!.estacoes),
    operadoras: [...por.values()].sort((a, b) => b.estacoes - a.estacoes).slice(0, 15),
    comparacao_uf: null,
  }
}

function agregarFust(perfis: PerfilMunicipio[]): FustMunicipio | undefined {
  const itens = perfis.filter((p) => p.fust)
  if (itens.length === 0) return undefined
  const f0 = itens[0].fust!
  const nomes: Record<string, string> = {}
  for (const p of itens) Object.assign(nomes, p.fust!.programas_nomes)
  const compromissos = soma(itens.map((p) => p.fust!.compromissos))
  const r = por10mil(itens, (p) => p.fust!.compromissos)
  return {
    ...f0, compromissos, atendidos: soma(itens.map((p) => p.fust!.atendidos)), a_vencer: soma(itens.map((p) => p.fust!.a_vencer)),
    em_apuracao: soma(itens.map((p) => p.fust!.em_apuracao)), investimento: soma(itens.map((p) => p.fust!.investimento)),
    programas: somaMapas(itens.map((p) => p.fust!.programas)), tipos: somaMapas(itens.map((p) => p.fust!.tipos)), programas_nomes: nomes,
    por_10mil_hab: r ?? undefined, comparacao_uf: null,
  }
}

/** Variação do conjunto: refaz o mês anterior (ou o de 12 meses antes) de cada município a partir da variação percentual dele. */
function variacao(itens: IndicadoresMunicipio[], campo: 'var_mm_pct' | 'var_aa_pct'): number | null {
  const com = itens.filter((i) => i[campo] != null && i.acessos > 0 && (i[campo] as number) > -100)
  if (com.length === 0) return null
  const atual = soma(com.map((i) => i.acessos))
  const antes = soma(com.map((i) => i.acessos / (1 + (i[campo] as number) / 100)))
  return antes ? Math.round(((atual - antes) / antes) * 10000) / 100 : null
}

function agregarIndicadores(perfis: PerfilMunicipio[], fixo: SiciMunicipioDetalhe | undefined): IndicadoresMunicipio | undefined {
  const itens = perfis.flatMap((p) => (p.indicadores ? [p.indicadores] : []))
  if (itens.length === 0 || !fixo) return undefined
  const lider = fixo.operadores[0]
  return {
    mes_referencia: itens[0].mes_referencia, metodologia: itens[0].metodologia, acessos: soma(itens.map((i) => i.acessos)),
    n_operadoras: fixo.operadores_count, hhi: fixo.hhi,
    ...(lider ? { lider: { cnpj: lider.cnpj, empresa: lider.empresa, share: lider.share } } : {}),
    var_mm_pct: variacao(itens, 'var_mm_pct'), var_aa_pct: variacao(itens, 'var_aa_pct'),
    // ganho/perda de uma operadora no conjunto não se refaz a partir dos maiores de cada município: omitido de propósito
  }
}

/** Rótulo do conjunto para os títulos dos blocos ("Quem oferece banda larga em 18 municípios"). */
export const rotuloConjunto = (n: number) => `${n.toLocaleString('pt-BR')} ${n === 1 ? 'município' : 'municípios'}`

/**
 * Soma os perfis `/municipios/{ibge}` de um conjunto no formato que os blocos de município já leem, de modo que os mesmos blocos servem
 * ao município e ao raio. Soma o que soma (acessos, domicílios, estações, compromissos); refaz o que é razão (participação, HHI, penetração,
 * por 10 mil habitantes, variação) sobre o total do conjunto; não mistura o que não se soma (distância ao PTT fica do município central).
 * Município sem perfil (sem acesso declarado) simplesmente não contribui. `perfis[0]` é o município central.
 */
export function agregarMunicipios(perfis: Array<PerfilMunicipio | null | undefined>): Pick<MunicipioCtx, 'fixo' | 'movel' | 'territorio' | 'erbs' | 'fust' | 'indicadores'> | null {
  const validos = perfis.filter((p): p is PerfilMunicipio => !!p)
  if (validos.length === 0) return null
  const central = validos[0]
  const rotulo = rotuloConjunto(validos.length)
  const fixo = agregarFixo(central, rotulo, validos.flatMap((p) => (p.fixo ? [p.fixo] : [])))
  return {
    fixo, movel: agregarMovel(central, rotulo, validos.flatMap((p) => (p.movel ? [p.movel] : []))),
    territorio: agregarTerritorio(central, rotulo, validos.flatMap((p) => (p.territorio ? [p.territorio] : []))),
    erbs: agregarErbs(validos), fust: agregarFust(validos), indicadores: agregarIndicadores(validos, fixo),
  }
}
