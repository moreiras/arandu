// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Tipos do `catalogo.json` (gerado por `scripts/gen_docs.py` a partir do catálogo; servido em `/catalogo.json`). */
export interface CampoCatalogo { nome: string; tipo: string; significado: string; tratamento?: string }

export interface FonteCatalogo {
  id: string
  nome: string
  tipo: string
  ativa: boolean
  modulo: string
  descricao: string
  origem: { url?: string; formato?: string; licenca?: string; termos?: string; uso_comercial?: string; nota?: string }
  cadencia: { fonte_atualiza?: string; coleta?: string; coleta_atual?: string; frescor_maximo?: string }
  politica_falha?: string
  nao_verificado: string[]
  uso_comercial_efetivo?: string
  campos: CampoCatalogo[]
}

export interface ProdutoCatalogo { id: string; nome: string; descricao: string; modulo: string; limites?: string; pendencias: string[]; campos: CampoCatalogo[] }

export interface Catalogo { versao_esquema: number; fontes: FonteCatalogo[]; produtos: ProdutoCatalogo[] }

const TIPOS: Record<string, string> = { bruta: 'Coletada', derivada: 'Derivada', curada: 'Curada à mão' }

export function rotuloTipo(t: string): string {
  return TIPOS[t] ?? t
}

/** "a fonte atualiza: mensal · coletamos: semanal" a partir da cadência declarada. */
export function descreverCadencia(c: FonteCatalogo['cadencia']): string {
  const partes = []
  if (c.fonte_atualiza) partes.push(`a fonte atualiza: ${c.fonte_atualiza}`)
  if (c.coleta_atual) partes.push(`coletamos: ${c.coleta_atual}`)
  return partes.join(' · ') || '—'
}
