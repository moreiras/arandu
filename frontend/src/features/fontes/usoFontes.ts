// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { AbaDef, BlocoDef, Entidade } from '../entidade/registry'

/** Nome da página de cada entidade, na ordem em que o índice as lista. */
export const PAGINAS_ENTIDADE: Array<[Entidade, string]> = [
  ['asn', 'Página de AS'], ['ixp', 'Página de PTT'], ['operadora', 'Página de operadora'], ['grupo', 'Página de grupo econômico'],
  ['uf', 'Página de UF'], ['municipio', 'Página de município'], ['prefixo', 'Página de prefixo'],
]

export interface UsoEmBloco { entidade: Entidade; pagina: string; blocoId: string; titulo: string; aba?: string }

/**
 * Índice fonte para páginas, derivado do registro de blocos das páginas de entidade (cada bloco declara os ids de fonte do catálogo que o alimentam).
 * Não há lista à mão: bloco novo ou fonte nova entra no índice sozinho. Devolve, para cada fonte do catálogo, os blocos que a declaram; fonte sem bloco
 * fica com lista vazia (aparece em páginas de painel, na API ou no MCP, que este índice não cobre).
 */
export function indiceFontePaginas(blocos: ReadonlyArray<Pick<BlocoDef, 'id' | 'entidade' | 'titulo' | 'fontes' | 'aba'>>, idsDoCatalogo: readonly string[], abas: (e: Entidade) => AbaDef[]): Map<string, UsoEmBloco[]> {
  const ordem = new Map(PAGINAS_ENTIDADE.map(([e], i) => [e, i] as const))
  const nomes = new Map(PAGINAS_ENTIDADE)
  const out = new Map<string, UsoEmBloco[]>(idsDoCatalogo.map((id) => [id, []]))
  for (const b of blocos) {
    for (const f of new Set(b.fontes)) {
      const lista = out.get(f) ?? []
      lista.push({ entidade: b.entidade, pagina: nomes.get(b.entidade) ?? b.entidade, blocoId: b.id, titulo: b.titulo, aba: b.aba ? abas(b.entidade).find((a) => a.id === b.aba)?.rotulo : undefined })
      out.set(f, lista)
    }
  }
  for (const lista of out.values()) lista.sort((a, b) => (ordem.get(a.entidade) ?? 99) - (ordem.get(b.entidade) ?? 99))
  return out
}

/** Os blocos de uma fonte agrupados por página, na ordem do índice. */
export function porPagina(usos: UsoEmBloco[]): Array<{ pagina: string; blocos: UsoEmBloco[] }> {
  const grupos = new Map<string, UsoEmBloco[]>()
  for (const u of usos) grupos.set(u.pagina, [...(grupos.get(u.pagina) ?? []), u])
  return [...grupos].map(([pagina, blocos]) => ({ pagina, blocos }))
}
