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
  fontes: string[]
  fontesEntradas?: FonteEntrada[] | null
  snapshot?: string | null
  /** Endereço permanente (com ?date= do snapshot e o âncora do bloco). */
  url: string
  /** Data do acesso; o chamador passa a de hoje. */
  acessoEm: Date
}

/** Link permanente: a mesma página, no snapshot citado (`?date=`), com a aba e a âncora do bloco; a referência não muda quando um snapshot novo sai. */
export function linkPermanente(origem: string, caminho: string, busca: string, snapshot: string | null | undefined, blocoId?: string): string {
  const p = new URLSearchParams(busca)
  if (snapshot) p.set('date', snapshot)
  const q = p.toString()
  return `${origem}${caminho}${q ? `?${q}` : ''}${blocoId ? `#bloco-${blocoId}` : ''}`
}

const dataBr = (d: Date) => d.toLocaleDateString('pt-BR')

/** Texto de citação pronto, em português, sem inventar nada: o que está no bloco (entidade, fonte, referência da fonte, snapshot) e o endereço. */
export function montarCitacao(c: DadosCitacao): string {
  const refs = c.fontes.map((id) => {
    const f = c.fontesEntradas?.find((x) => x.id === id)
    return f?.as_of ? `${id} (referência ${formatarReferencia(f.as_of)})` : id
  })
  return [
    `${SITE.nome}. ${c.entidade}: ${c.bloco}${c.valor ? ` — ${c.valor}` : ''}.`,
    refs.length ? `Fonte${refs.length > 1 ? 's' : ''}: ${refs.join('; ')}.` : null,
    c.snapshot ? `Snapshot de ${formatarReferencia(c.snapshot)}.` : null,
    `Disponível em: ${c.url}.`,
    `Acesso em: ${dataBr(c.acessoEm)}.`,
  ].filter(Boolean).join(' ')
}
