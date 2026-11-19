// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Entrada de `sources[]` do manifesto (core/store/manifesto.py): de onde veio cada fonte neste snapshot. */
export interface FonteEntrada {
  id: string
  /** Referência do dado (data da coleta ou mês de referência, como no SICI). */
  as_of: string | null
  coletado_em?: string | null
  hash?: string | null
  versao?: string | null
  origem?: 'armazem' | 'legado' | 'ausente' | string
  legado?: boolean
  frescor?: 'ok' | 'defasada' | 'desconhecido' | 'ausente' | string
}

/** Natureza do dado exibido (AGENTS.md, honestidade semântica): inferido e estimado nunca se passam por fato. */
export type Selo = 'fato' | 'inferido' | 'estimado'

export const ROTULO_SELO: Record<Selo, string> = { fato: 'Fato', inferido: 'Inferido', estimado: 'Estimado' }

export const DESCRICAO_SELO: Record<Selo, string> = {
  fato: 'Dado declarado ou medido na fonte.',
  inferido: 'Derivado de outros dados por uma regra; pode estar errado.',
  estimado: 'Valor aproximado (amostragem ou modelo).',
}

/** Declaração de um bloco: de que fontes (ids do catálogo) ele depende e como o dado deve ser lido. */
export interface ProvenienciaBloco {
  fontes: string[]
  selo?: Selo
  /** Texto livre curto (ex.: "janela de 60 dias"). */
  nota?: string
}

export function fonteDe(fontes: FonteEntrada[] | null | undefined, id: string): FonteEntrada | undefined {
  return fontes?.find((f) => f.id === id)
}

const FRESCOR: Record<string, string> = {
  ok: 'em dia',
  defasada: 'defasada',
  desconhecido: 'frescor desconhecido',
  ausente: 'sem dado neste snapshot',
}

export function rotuloFrescor(f: FonteEntrada | undefined): string {
  // O manifesto (`compor_fontes`) deixa de fora, por desenho, as fontes curadas e as de coleta manual: não é falha de coleta.
  if (!f) return 'sem coleta registrada no manifesto (fonte curada pelo projeto)'
  return FRESCOR[f.frescor ?? 'desconhecido'] ?? String(f.frescor)
}

/** Data `AAAA-MM-DD` (ou mês `AAAA-MM`) em formato brasileiro; devolve o texto original se não for uma data. */
export function formatarReferencia(v: string | null | undefined): string {
  if (!v) return '—'
  const m = /^(\d{4})-(\d{2})(?:-(\d{2}))?/.exec(v)
  if (!m) return v
  return m[3] ? `${m[3]}/${m[2]}/${m[1]}` : `${m[2]}/${m[1]}`
}
