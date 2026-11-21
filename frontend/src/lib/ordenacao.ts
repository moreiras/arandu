// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useMemo, useState } from 'react'

/**
 * Ordenação por coluna das tabelas montadas à mão (as que não usam `TabelaDados`).
 *
 * A regra que importa: ordena-se a lista **inteira** e só depois se corta para a versão reduzida (N primeiros). Reordenar só as N
 * linhas visíveis esconderia quem lidera a coluna escolhida. Quando a lista inteira não está no navegador (a API devolve só as N
 * primeiras), a ordem vai ao servidor: use `alternarOrdem` com o estado na consulta, não `useOrdenacao`.
 */
export type Sentido = 'asc' | 'desc'
export interface Ordem<C extends string = string> { campo: C; dir: Sentido }

/** Valor de uma coluna para comparar; `null`/`undefined`/`NaN` vão sempre para o fim, nos dois sentidos. */
export type Valor = number | string | boolean | null | undefined
/** Como ler o valor de uma coluna; `primeiro` é o sentido do primeiro clique (padrão: números do maior, textos de A a Z). */
export type Acessor<T> = ((linha: T) => Valor) | { valor: (linha: T) => Valor; primeiro?: Sentido }

const colacao = new Intl.Collator('pt-BR', { numeric: true, sensitivity: 'base' })
const vazio = (v: Valor) => v == null || (typeof v === 'number' && Number.isNaN(v)) || v === ''

function comparar(a: Valor, b: Valor): number {
  if (typeof a === 'string' || typeof b === 'string') return colacao.compare(String(a), String(b))
  return Number(a) - Number(b)
}

/** Cópia ordenada e estável; vazios no fim. */
export function ordenar<T>(dados: readonly T[], valor: (linha: T) => Valor, dir: Sentido): T[] {
  const s = dir === 'asc' ? 1 : -1
  return dados
    .map((linha, i) => ({ linha, i, v: valor(linha) }))
    .sort((x, y) => {
      const vx = vazio(x.v), vy = vazio(y.v)
      if (vx || vy) return vx === vy ? x.i - y.i : vx ? 1 : -1
      return s * comparar(x.v, y.v) || x.i - y.i
    })
    .map((x) => x.linha)
}

/** Próxima ordem ao clicar em `campo`: outra coluna começa em `primeiro`; a mesma coluna inverte. */
export function alternarOrdem<C extends string>(atual: Ordem<C> | null | undefined, campo: C, primeiro: Sentido = 'desc'): Ordem<C> {
  if (atual?.campo === campo) return { campo, dir: atual.dir === 'asc' ? 'desc' : 'asc' }
  return { campo, dir: primeiro }
}

function ler<T>(a: Acessor<T>): { valor: (linha: T) => Valor; primeiro?: Sentido } {
  return typeof a === 'function' ? { valor: a } : a
}

/** Sentido do primeiro clique: o declarado, ou pelo tipo do primeiro valor não vazio (texto → A a Z; número → maior primeiro). */
function primeiroSentido<T>(dados: readonly T[], a: Acessor<T>): Sentido {
  const { valor, primeiro } = ler(a)
  if (primeiro) return primeiro
  for (const l of dados) {
    const v = valor(l)
    if (!vazio(v)) return typeof v === 'string' ? 'asc' : 'desc'
  }
  return 'desc'
}

/**
 * Estado de ordenação de uma tabela com a lista inteira no navegador. `inicial` nulo mantém a ordem recebida até o primeiro clique.
 * Devolve a lista inteira ordenada (corte depois para a versão reduzida) e `props(campo)` para o `ThOrdenavel`.
 */
export function useOrdenacao<T, C extends string>(dados: readonly T[] | null | undefined, acessores: Record<C, Acessor<T>>, inicial: Ordem<NoInfer<C>> | null = null) {
  const [ordem, setOrdem] = useState<Ordem<C> | null>(inicial)
  const lista = dados ?? []
  const ordenados = useMemo(() => {
    const a = ordem ? acessores[ordem.campo] : undefined
    return ordem && a ? ordenar(lista, ler(a).valor, ordem.dir) : [...lista]
    // `acessores` costuma ser um literal novo a cada render; a ordem só muda com os dados ou com o clique.
  },[lista, ordem?.campo, ordem?.dir])
  const alternar = (campo: C) => setOrdem((o) => alternarOrdem(o, campo, primeiroSentido(lista, acessores[campo])))
  const props = (campo: C) => ({ campo, ordem, onOrdenar: alternar as (c: string) => void })
  return { ordenados, ordem, setOrdem, alternar, props }
}
