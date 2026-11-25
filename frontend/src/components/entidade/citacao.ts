// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { formatarReferencia, type FonteEntrada } from './proveniencia'
import { SITE } from '../../lib/site'

export interface DadosCitacao {
  /** A entidade, como a página a chama ("AS15169 · Google LLC", "Município de Vitória/ES"). */
  entidade: string
  /** O bloco (título) ou o dado citado. */
  bloco: string
  /** O número ou a frase citada, quando a citação é de um valor e não do bloco inteiro. */
  valor?: string
  /** Os valores que o bloco mostra (rótulo e número, como na tela): a citação os carrega, para valer sozinha quando o link deixar de abrir sem login. */
  valores?: ValorCitado[]
  fontes: string[]
  fontesEntradas?: FonteEntrada[] | null
  snapshot?: string | null
  /** Endereço permanente (com ?date= do snapshot e o âncora do bloco). */
  url: string
  /** Data do acesso; o chamador passa a de hoje. */
  acessoEm: Date
}

export interface ValorCitado { rotulo: string; valor: string }

/** No máximo estes valores entram no texto: a citação é uma referência, não uma cópia do bloco. */
export const MAX_VALORES_CITADOS = 8

/**
 * Link permanente: a mesma página, no snapshot citado (`?date=`), com a aba e a âncora do bloco. O endereço identifica o dado, mas **abre sem
 * login só enquanto o snapshot estiver entre os dois mais recentes** (`access_policy.py`, `recent_dates`); depois exige login. Por isso a citação
 * (`montarCitacao`) leva também os valores, o snapshot e as fontes com as datas.
 */
export function linkPermanente(origem: string, caminho: string, busca: string, snapshot: string | null | undefined, blocoId?: string): string {
  const p = new URLSearchParams(busca)
  if (snapshot) p.set('date', snapshot)
  const q = p.toString()
  return `${origem}${caminho}${q ? `?${q}` : ''}${blocoId ? `#bloco-${blocoId}` : ''}`
}

const dataBr = (d: Date) => d.toLocaleDateString('pt-BR')

/**
 * Aviso sobre o prazo do link (mostrado no "Citar" e repetido no Sobre): sem login, abre enquanto o snapshot é um dos dois mais recentes. Os snapshots
 * são semanais, então o link citado abre em geral por cerca de duas semanas; depois exige login (conta gratuita). `recentes` = os snapshots atuais.
 */
export function avisoLinkCitacao(snapshot: string | null | undefined, recentes?: string[] | null): string {
  if (!snapshot) return 'Sem a data de um snapshot no endereço, o link mostra o snapshot mais recente no momento em que for aberto.'
  const lista = recentes?.length ? recentes : null
  if (lista && !lista.includes(snapshot)) {
    return `O snapshot de ${formatarReferencia(snapshot)} já não está entre os dois mais recentes (${lista.map(formatarReferencia).join(' e ')}): este link exige login. O texto da citação traz os valores e as fontes.`
  }
  const hoje = lista ? ` (hoje: ${lista.map(formatarReferencia).join(' e ')})` : ''
  return `Este link abre sem login enquanto o snapshot de ${formatarReferencia(snapshot)} estiver entre os dois mais recentes${hoje}, em geral cerca de duas semanas, pois os snapshots são semanais. Depois exige login. O texto da citação traz os valores e as fontes.`
}

/** Texto de citação pronto, em português, sem inventar nada: o que está no bloco (entidade, valores, fonte e data da fonte, snapshot) e o endereço. */
export function montarCitacao(c: DadosCitacao): string {
  const refs = c.fontes.map((id) => {
    const f = c.fontesEntradas?.find((x) => x.id === id)
    return f?.as_of ? `${id} (referência ${formatarReferencia(f.as_of)})` : `${id} (data de referência não informada)`
  })
  const valores = (c.valores ?? []).filter((v) => v.valor && v.valor !== '—').slice(0, MAX_VALORES_CITADOS)
  return [
    `${SITE.nome}. ${c.entidade}: ${c.bloco}${c.valor ? ` (${c.valor})` : ''}.`,
    valores.length ? `Valores: ${valores.map((v) => `${v.rotulo}: ${v.valor}`).join('; ')}.` : null,
    refs.length ? `Fonte${refs.length > 1 ? 's' : ''}: ${refs.join('; ')}.` : null,
    c.snapshot ? `Snapshot de ${formatarReferencia(c.snapshot)}.` : null,
    `Disponível em: ${c.url}.`,
    c.snapshot ? 'O endereço abre sem login enquanto o snapshot é um dos dois mais recentes; depois exige login.' : null,
    `Acesso em: ${dataBr(c.acessoEm)}.`,
  ].filter(Boolean).join(' ')
}
