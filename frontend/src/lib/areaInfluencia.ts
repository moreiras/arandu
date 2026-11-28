// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { COR_SEM_DADO } from '../components/maps/coresCoropletico'
import { palavra } from './sintese'
import type { AreaInfluenciaVisao, VisaoArea, VisaoAreaPtt } from '../types/areaInfluencia'

/** Faixa de um município num PTT: 1 até o P50 (onde atua a maioria), 2 do P50 ao P80 (quase todos), 3 além do P80 (os restantes). */
export type Faixa = 1 | 2 | 3

export const ROTULO_VISAO: Record<VisaoArea, string> = { diretos: 'Só diretamente conectados', todos: 'Todos que anunciam no PTT' }
/** As quatro visões da página do PTT, na ordem do seletor. */
export const VISOES_PTT: VisaoAreaPtt[] = ['diretos', 'todos', 'alcance_diretos', 'alcance_todos']
export const ROTULO_VISAO_PTT: Record<VisaoAreaPtt, string> = {
  diretos: 'Influência provável dos diretamente conectados', todos: 'Influência provável de todos que anunciam',
  alcance_diretos: 'Alcance dos diretamente conectados', alcance_todos: 'Alcance de todos que anunciam',
}
export const ehAlcance = (v: VisaoAreaPtt): boolean => v === 'alcance_diretos' || v === 'alcance_todos'
export const ROTULO_FAIXA: Record<Faixa, string> = { 1: 'Até o P50 (onde atua a maioria)', 2: 'Do P50 ao P80 (quase todos)', 3: 'Além do P80 (os restantes)' }
export const ROTULO_FAIXA_CURTO: Record<Faixa, string> = { 1: 'até o P50', 2: 'do P50 ao P80', 3: 'além do P80' }

/** Um só tom (azul) em três intensidades, da mais escura (perto) à mais clara (longe); a intensidade ordena, não julga. */
export const TONS_UM_MATIZ: Record<Faixa, string> = { 1: '#1e4f8c', 2: '#6a9fd4', 3: '#c3d9f0' }

/** Matizes (graus HSL) das cores de identidade dos PTTs no mapa nacional: sem vermelho, que leria como alerta. */
export const MATIZES = [210, 30, 280, 175, 48, 330, 245, 100, 195] as const
const L_FAIXA: Record<Faixa, number> = { 1: 36, 2: 56, 3: 78 }

/** Cor de um PTT numa faixa: o matiz identifica o PTT e a luminosidade, a faixa. */
export const corPtt = (matiz: number, faixa: Faixa): string => `hsl(${matiz}, 62%, ${L_FAIXA[faixa]}%)`

const km = (v: number) => v < 1 ? 'menos de 1 km' : `${Math.round(v).toLocaleString('pt-BR')} km`
export { km as formatarKm }

function haversine(a: [number, number], b: [number, number]): number {
  const r = (g: number) => (g * Math.PI) / 180
  const h = Math.sin(r(b[0] - a[0]) / 2) ** 2 + Math.cos(r(a[0])) * Math.cos(r(b[0])) * Math.sin(r(b[1] - a[1]) / 2) ** 2
  return 2 * 6371 * Math.asin(Math.sqrt(h))
}

/**
 * Matiz de cada PTT, de modo que PTTs vizinhos não repitam o matiz: gulosa, dos PTTs com mais municípios aos menores, cada um com o matiz
 * menos usado entre os 6 PTTs mais próximos já coloridos (desempate: o menos usado no total, depois a ordem da lista). Determinística.
 */
export function matizesPorPtt(ptts: Record<string, { ponto: [number, number] | null; municipios: number }>): Record<string, number> {
  const codigos = Object.keys(ptts).sort((a, b) => ptts[b].municipios - ptts[a].municipios || a.localeCompare(b))
  const dado: Record<string, number> = {}
  const uso = MATIZES.map(() => 0)
  for (const c of codigos) {
    const ponto = ptts[c].ponto
    const vizinhos = ponto
      ? Object.keys(dado).filter((o) => ptts[o].ponto).sort((x, y) => haversine(ponto, ptts[x].ponto!) - haversine(ponto, ptts[y].ponto!) || x.localeCompare(y)).slice(0, 6)
      : []
    let melhor = 0, melhorCusto = Infinity
    MATIZES.forEach((m, i) => {
      const custo = vizinhos.reduce((s, o, k) => s + (dado[o] === m ? 100 / (k + 1) : 0), 0) + uso[i] / 1000
      if (custo < melhorCusto) { melhorCusto = custo; melhor = i }
    })
    dado[c] = MATIZES[melhor]; uso[melhor] += 1
  }
  return dado
}

type Ramos = unknown[]
function expressao(chave: string, grupos: Map<string, { cor: string; ids: string[] }>): unknown {
  const ramos: Ramos = []
  for (const { cor, ids } of grupos.values()) ramos.push(ids, cor)
  return ramos.length ? ['match', ['get', chave], ...ramos, COR_SEM_DADO] : COR_SEM_DADO
}

/** Expressão de cor do mapa de um PTT: cada município com acessos atribuídos recebe o tom da sua faixa; o resto fica cinza. */
export function expressaoFaixas(municipios: Record<string, [number, number]>): unknown {
  const grupos = new Map<string, { cor: string; ids: string[] }>()
  for (const [ibge, [, faixa]] of Object.entries(municipios)) {
    const f = faixa as Faixa
    const g = grupos.get(String(f)) ?? { cor: TONS_UM_MATIZ[f], ids: [] }
    g.ids.push(ibge); grupos.set(String(f), g)
  }
  return expressao('ibge', grupos)
}

/** Expressão de cor do mapa nacional: o matiz é o do PTT principal do município e o tom, a faixa dele nesse PTT. */
export function expressaoPrincipal(municipios: Record<string, [string, number, ...number[]]>, matizes: Record<string, number>): unknown {
  const grupos = new Map<string, { cor: string; ids: string[] }>()
  for (const [ibge, [ptt, faixa]] of Object.entries(municipios)) {
    const m = matizes[ptt]
    if (m === undefined) continue
    const k = `${ptt}|${faixa}`
    const g = grupos.get(k) ?? { cor: corPtt(m, faixa as Faixa), ids: [] }
    g.ids.push(ibge); grupos.set(k, g)
  }
  return expressao('ibge', grupos)
}

/** Frases do bloco do PTT, com os números das duas visões. Visão sem acessos atribuídos diz isso, sem inventar distância. */
export function frasesArea(diretos: AreaInfluenciaVisao | null | undefined, todos: AreaInfluenciaVisao | null | undefined): { diretos: string; todos: string; mediana: string | null } {
  const dirs = diretos
    ? `Os participantes diretamente conectados atuam, na maior parte (P50), a até ${km(diretos.p50_km)}; quase todos (P80), a até ${km(diretos.p80_km)}; os restantes, além disso (o P90 é ${km(diretos.p90_km)}).`
    : 'Nenhum participante diretamente conectado com prefixo próprio visto neste PTT tem acessos de banda larga fixa atribuídos a ele.'
  const tod = todos
    ? `Considerando também quem anuncia pelo PTT sem estar conectado, a área chega a ${km(todos.p80_km)} para quase todos os acessos (P80) e a ${km(todos.p90_km)} no P90; a maior parte (P50) está a até ${km(todos.p50_km)}.`
      + (diretos ? ` Entram na conta ${todos.operadoras.toLocaleString('pt-BR')} ${palavra(todos.operadoras, 'operadora', 'operadoras')} em ${todos.municipios.toLocaleString('pt-BR')} ${palavra(todos.municipios, 'município', 'municípios')}, contra ${diretos.operadoras.toLocaleString('pt-BR')} em ${diretos.municipios.toLocaleString('pt-BR')} só com os conectados.` : '')
    : 'Nenhum ASN com prefixo próprio visto neste PTT tem acessos de banda larga fixa atribuídos a ele.'
  const med = todos ?? diretos
  const mediana = med
    ? `A mediana por operadora é de ${km(med.mediana_operadora_km)} (cada operadora conta uma vez). Ela mede outra população que o P50, que pesa por acessos.`
    : null
  return { diretos: dirs, todos: tod, mediana }
}

/** Frases das visões de alcance (sem descontar PTTs mais próximos). Visão sem operadoras diz isso, sem inventar distância. */
export function frasesAlcance(diretos: AreaInfluenciaVisao | null | undefined, todos: AreaInfluenciaVisao | null | undefined): { diretos: string; todos: string; mediana: string | null } {
  const dirs = diretos
    ? `Considerando todos os municípios onde atuam as operadoras diretamente conectadas, sem descontar PTTs mais próximos, a maioria (P50) está a até ${km(diretos.p50_km)}; quase todos (P80), a até ${km(diretos.p80_km)}; o P90 é ${km(diretos.p90_km)}.`
    : 'Nenhum participante diretamente conectado com prefixo próprio visto neste PTT tem acessos de banda larga fixa no alcance dele.'
  const tod = todos
    ? `Considerando todos os municípios onde atuam as operadoras que anunciam pelo PTT, diretas e indiretas, sem descontar PTTs mais próximos, a maioria (P50) está a até ${km(todos.p50_km)}; quase todos (P80), a até ${km(todos.p80_km)}; o P90 é ${km(todos.p90_km)}.`
      + ` O alcance reúne ${todos.operadoras.toLocaleString('pt-BR')} ${palavra(todos.operadoras, 'operadora', 'operadoras')} em ${todos.municipios.toLocaleString('pt-BR')} ${palavra(todos.municipios, 'município', 'municípios')}`
      + (diretos ? `, contra ${diretos.operadoras.toLocaleString('pt-BR')} em ${diretos.municipios.toLocaleString('pt-BR')} só com as conectadas.` : '.')
    : 'Nenhum ASN com prefixo próprio visto neste PTT tem acessos de banda larga fixa no alcance dele.'
  const med = todos ?? diretos
  const mediana = med
    ? `No alcance, a mediana por operadora é de ${km(med.mediana_operadora_km)} (cada operadora conta uma vez). Ela mede outra população que o P50, que pesa por acessos.`
    : null
  return { diretos: dirs, todos: tod, mediana }
}

/** Percentual de `parte` em `total`, com uma casa. */
export const pct = (parte: number, total: number): string => (total ? ((100 * parte) / total).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) : '0') + '%'
