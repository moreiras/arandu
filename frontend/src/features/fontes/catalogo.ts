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
  /** Nível de acesso do que a fonte alimenta (`aberta`, `login`); `decisao_exposicao` e `atribuicao` vêm do catálogo (D9). */
  exposicao?: string
  decisao_exposicao?: string
  atribuicao?: string
  origem: { url?: string; formato?: string; licenca?: string; termos?: string; uso_comercial?: string; nota?: string }
  cadencia: { fonte_atualiza?: string; coleta?: string; coleta_atual?: string; frescor_maximo?: string }
  politica_falha?: string
  /** Quantos valores `nao_verificado` o cadastro da fonte declara (cada um é tarefa aberta do projeto), não uma lista. */
  nao_verificado: number
  uso_comercial_efetivo?: string
  /** Fontes de que esta depende (`entradas` do catálogo); explicam o uso comercial herdado. */
  entradas?: string[]
  campos: CampoCatalogo[]
}

export interface ProdutoCatalogo { id: string; nome: string; descricao: string; modulo: string; limites?: string; pendencias: string[]; campos: CampoCatalogo[] }

export interface Catalogo { versao_esquema: number; fontes: FonteCatalogo[]; produtos: ProdutoCatalogo[] }

const NAO_VERIFICADO = 'nao_verificado'

/** Texto do catálogo para a tela: o token interno `nao_verificado`, onde aparece, vira "não verificado". */
export const legivel = (v: string | undefined): string | undefined => v?.replace(/nao_verificado/g, 'não verificado')

/** Licença legível: o token cru `nao_verificado` (ou ausência) vira "não verificada pelo projeto"; o texto da licença passa como está. */
export function rotuloLicenca(licenca: string | undefined): string {
  return !licenca || licenca === NAO_VERIFICADO ? 'não verificada pelo projeto' : (legivel(licenca) as string)
}

/** Uso comercial pelos termos lidos; `herdado` explica quando o efetivo vem das entradas e não da própria fonte. */
export function rotuloUsoComercial(uso: string | undefined): string {
  if (uso === 'permitido') return 'uso comercial permitido pelos termos lidos'
  if (uso === 'restrito') return 'uso comercial com condições ou restrito (ver termos)'
  return 'termos de uso comercial não verificados pelo projeto'
}

/** "por herança de: a, b" quando o uso comercial efetivo difere do declarado na própria fonte e há entradas. */
export function heranca(f: Pick<FonteCatalogo, 'origem' | 'uso_comercial_efetivo' | 'entradas'>): string | null {
  const proprio = f.origem.uso_comercial
  if (!f.entradas?.length || f.uso_comercial_efetivo === proprio) return null
  return `por herança de: ${f.entradas.join(', ')}`
}

const TIPOS: Record<string, string> = { bruta: 'Coletada', derivada: 'Derivada', curada: 'Curada à mão' }

export function rotuloTipo(t: string): string {
  return TIPOS[t] ?? t
}

/** "a fonte atualiza: mensal · coletamos: semanal" a partir da cadência declarada. */
export function descreverCadencia(c: FonteCatalogo['cadencia']): string {
  const partes = []
  if (c.fonte_atualiza) partes.push(`a fonte atualiza: ${legivel(c.fonte_atualiza)}`)
  if (c.coleta_atual) partes.push(`coletamos: ${c.coleta_atual}`)
  return partes.join(' · ') || '—'
}
