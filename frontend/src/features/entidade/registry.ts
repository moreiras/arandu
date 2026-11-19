// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ComponentType } from 'react'
import type { Selo } from '../../components/entidade'

export type Entidade = 'asn' | 'ixp' | 'operadora' | 'municipio' | 'uf' | 'prefixo' | 'grupo'

/** O que um bloco recebe: os dados da entidade (o tipo concreto é do conjunto de blocos da entidade) e a data do snapshot. */
export interface BlocoProps<D = unknown> {
  dados: D
  snapshot: string | null
}

/**
 * Declaração de um bloco de página de entidade. A página não conhece os blocos: lê o registro da entidade, descarta os não
 * aplicáveis e renderiza cada um dentro de uma `Section` — por isso todo bloco TEM título, fontes e selo (proveniência por construção).
 */
export interface BlocoDef<D = unknown> {
  id: string
  entidade: Entidade
  titulo: string
  subtitulo?: string
  /** Ordem de exibição (crescente). Fontes novas encaixam entre as existentes sem renumerar: use passos de 10. */
  ordem: number
  /** Dados de que o bloco depende (nomes dos hooks/rotas); documenta a dependência e serve ao teste de orçamento de chamadas. */
  depende: string[]
  /** Ids de fonte do catálogo (`catalog/sources`); o teste do registro confere que existem. */
  fontes: string[]
  selo?: Selo
  nota?: string
  /** Falso ⇒ o bloco nem aparece (ex.: ASN sem outorga não mostra o bloco de outorga). */
  aplicavel?: (dados: D) => boolean
  /** Verdadeiro ⇒ mostra o estado vazio com a data do snapshot em vez do conteúdo. */
  vazio?: (dados: D) => boolean
  mensagemVazio?: string
  /** O bloco traz os próprios títulos (colunas IPv6/IPv4 lado a lado): `titulo` vira só o `aria-label`. */
  semTitulo?: boolean
  /** Sem cartão: a página migrada mantém o visual de antes. */
  plana?: boolean
  /** Lente (aba) a que o bloco pertence: um id de `registrarAbas` da entidade. Obrigatório nas entidades que têm abas. */
  aba?: string
  /** "Como ler": uma ou duas frases sobre o que o bloco mostra e o que ele não prova; fica num `<details>` sob o título. */
  comoLer?: string
  /** Começa recolhido (`<details>` fechado, com o título visível): para blocos longos ou de leitura secundária. */
  recolhido?: boolean
  Componente: ComponentType<BlocoProps<D>>
}

const registro = new Map<Entidade, BlocoDef<any>[]>()

export function registrarBloco<D>(def: BlocoDef<D>): BlocoDef<D> {
  const lista = registro.get(def.entidade) ?? []
  if (lista.some((b) => b.id === def.id)) throw new Error(`bloco duplicado: ${def.entidade}/${def.id}`)
  registro.set(def.entidade, [...lista, def].sort((a, b) => a.ordem - b.ordem))
  return def
}

export function blocosDe(entidade: Entidade): BlocoDef<any>[] {
  return registro.get(entidade) ?? []
}

export function todosOsBlocos(): BlocoDef<any>[] {
  return [...registro.values()].flat()
}


/** Uma lente (aba) da página de uma entidade: o `?aba=` da URL guarda o `id`. */
export interface AbaDef {
  id: string
  rotulo: string
  /** Uma linha: a pergunta que a aba responde (aparece sob as abas e como `title`). */
  descricao: string
}

const abas = new Map<Entidade, AbaDef[]>()

/** Declara as abas de uma entidade, na ordem de exibição; a primeira é a padrão. Entidade sem abas mostra todos os blocos numa página só. */
export function registrarAbas(entidade: Entidade, lista: AbaDef[]): void {
  if (new Set(lista.map((a) => a.id)).size !== lista.length) throw new Error(`abas duplicadas: ${entidade}`)
  abas.set(entidade, lista)
}

export function abasDe(entidade: Entidade): AbaDef[] {
  return abas.get(entidade) ?? []
}
