// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import dados from './cartoes.json'

export type Consulta =
  | { tipo: 'query'; colecao: string; corpo: Record<string, unknown> }
  | { tipo: 'get'; caminho: string; params?: Record<string, string | number | boolean> }
  /** Resposta montada no navegador a partir de uma ou duas consultas (`derivados.ts`): distância até o PTT, cruzamento de coleções. */
  | { tipo: 'derivado'; id: string; consultas: Array<{ colecao: string; corpo: Record<string, unknown> }> }

export interface Cartao {
  id: string
  titulo: string
  pergunta: string
  consulta: Consulta
  /** Como mostrar cada linha: o campo do rótulo (e um complemento opcional), o do valor, a unidade e o link (com `{campo}`). */
  linha: { rotulo: string; complemento?: string; valor: string; unidade: string; link: string }
  destino: { to: string; rotulo: string }
  fontes: string[]
}

export const CARTOES = (dados as unknown as { cartoes: Cartao[] }).cartoes

/** Troca `{campo}` do link pelo valor da linha. */
export function linkDaLinha(modelo: string, item: Record<string, unknown>): string {
  return modelo.replace(/\{(\w+)\}/g, (_, k) => encodeURIComponent(String(item[k] ?? '')))
}

export function formatarValor(v: unknown): string {
  if (typeof v !== 'number') return v == null ? '—' : String(v)
  return v.toLocaleString('pt-BR', { maximumFractionDigits: Number.isInteger(v) ? 0 : 1 })
}
