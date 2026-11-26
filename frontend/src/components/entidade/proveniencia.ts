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
  /** Vocabulário do backend (`core/store/manifesto.py`): `ok`, `atrasado`, `sem_limite`, `desconhecido`, `ausente`. `defasada` é o nome antigo de `atrasado`. */
  frescor?: 'ok' | 'atrasado' | 'sem_limite' | 'defasada' | 'desconhecido' | 'ausente' | string
  /** Data (AAAA-MM-DD) em que o frescor foi medido: a última coleta que confirmou a versão, que pode ser mais nova que `coletado_em`. */
  verificado_em?: string | null
  /** Limite de frescor do catálogo, em dias; ausente em snapshot anterior ao PT-16. */
  limite_dias?: number | null
  /** Só em `origem: 'ausente'`: `false` = fonte desativada no catálogo (não é falha de coleta). */
  ativa?: boolean
}

/** O que o catálogo diz da fonte (`/catalogo.json`); dá o texto certo para a fonte que o manifesto não traz. */
export interface ContextoFonte { tipo?: string; ativa?: boolean; coleta_atual?: string; frescor_maximo?: string }

/** Natureza do dado exibido (AGENTS.md, honestidade semântica): inferido e estimado nunca se passam por fato. */
export type Selo = 'fato' | 'inferido' | 'estimado'

export const ROTULO_SELO: Record<Selo, string> = { fato: 'Fato', inferido: 'Inferido', estimado: 'Estimado' }

export const DESCRICAO_SELO: Record<Selo, string> = {
  fato: 'Declarado pela fonte ou medido diretamente.',
  inferido: 'Deduzido de outros dados por uma regra pública; pode não corresponder à realidade.',
  estimado: 'Valor aproximado, obtido por amostragem ou modelo.',
}

/** Nome acessível do selo, com o significado ("Fato: declarado pela fonte ou medido diretamente"), montado do rótulo e da frase acima. */
export function nomeAcessivelSelo(selo: Selo): string {
  const frase = (DESCRICAO_SELO[selo] ?? '').replace(/\.$/, '')
  return `${ROTULO_SELO[selo] ?? String(selo)}${frase ? `: ${frase.charAt(0).toLowerCase()}${frase.slice(1)}` : ''}`
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
  sem_limite: 'sem limite de frescor definido',
  desconhecido: 'frescor desconhecido (dado legado)',
}

/** Dias de `frescor_maximo` do catálogo (`2d`, `8d`, `2w`, `48h`); nulo se o formato não for esse. */
export function limiteEmDias(maximo: string | undefined): number | null {
  const m = /^(\d+)([dhw])$/.exec(maximo ?? '')
  if (!m) return null
  const k = Number(m[1])
  return m[2] === 'w' ? k * 7 : m[2] === 'd' ? k : Math.max(1, Math.floor(k / 24))
}

/**
 * Texto do estado da coleta de uma fonte neste snapshot. Sem entrada no manifesto: fonte desativada, curadoria, coleta manual ou, se o catálogo diz que a fonte é coletada,
 * "sem versão coletada"; sem o catálogo (rodapé de bloco) só se afirma o que o manifesto sabe, sem chamar de "curada" o que pode ser coleta manual.
 */
export function rotuloFrescor(f: FonteEntrada | undefined, ctx?: ContextoFonte): string {
  if (!f) {
    if (!ctx) return 'fora do registro de coleta do manifesto (curadoria ou coleta manual)'
    if (ctx.ativa === false) return 'fonte desativada'
    if (ctx.tipo === 'curada') return 'curadoria do projeto, fora do registro de coleta'
    if (ctx.coleta_atual === 'manual') return 'coleta manual, fora do registro de coleta'
    return 'sem versão coletada para este snapshot'
  }
  const fr = f.frescor ?? 'desconhecido'
  if (fr === 'ausente') return f.ativa === false || ctx?.ativa === false ? 'fonte desativada' : 'sem versão coletada para este snapshot'
  if (fr === 'atrasado' || fr === 'defasada') {
    const limite = f.limite_dias ?? limiteEmDias(ctx?.frescor_maximo)
    return limite ? `atrasada (limite ${limite} ${limite === 1 ? 'dia' : 'dias'})` : 'atrasada'
  }
  return FRESCOR[fr] ?? fr
}

/** Data `AAAA-MM-DD` (ou mês `AAAA-MM`) em formato brasileiro; devolve o texto original se não for uma data. */
export function formatarReferencia(v: string | null | undefined): string {
  if (!v) return '—'
  const m = /^(\d{4})-(\d{2})(?:-(\d{2}))?/.exec(v)
  if (!m) return v
  return m[3] ? `${m[3]}/${m[2]}/${m[1]}` : `${m[2]}/${m[1]}`
}
