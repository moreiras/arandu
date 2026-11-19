// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Fragment, useEffect, useState, type ReactNode } from 'react'
import {
  flexRender, getCoreRowModel, getExpandedRowModel, getPaginationRowModel, getSortedRowModel, useReactTable,
  type ColumnDef, type Row, type SortingState,
} from '@tanstack/react-table'
import { EmptyState } from '../entidade/EmptyState'
import { Dica } from './Dica'

/** Metadados de coluna aceitos pela tabela (`columnDef.meta`). */
export interface MetaColuna {
  /** Explicação da coluna, aberta pelo ⓘ do cabeçalho (T2). */
  dica?: ReactNode
  /** Alinhamento das células e do cabeçalho; números à direita. */
  alinhar?: 'left' | 'right' | 'center'
  /** `false` tira a coluna do cartão do celular; a primeira coluna do cartão vira o título. */
  cartao?: boolean
}

/** Verdadeiro quando a tela é estreita (< 640 px). Sem `matchMedia` (testes) devolve falso e a tabela fica em modo tabela. */
export function useTelaEstreita(): boolean {
  const consulta = '(max-width: 639px)'
  const [estreita, setEstreita] = useState(() => typeof window !== 'undefined' && !!window.matchMedia && window.matchMedia(consulta).matches)
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    const m = window.matchMedia(consulta)
    const f = () => setEstreita(m.matches)
    f()
    m.addEventListener('change', f)
    return () => m.removeEventListener('change', f)
  }, [])
  return estreita
}

const ALINHAR = { left: 'text-left', right: 'text-right', center: 'text-center' } as const

/**
 * Tabela padrão do site, no modelo da tabela de ASes:
 *  - cabeçalho fixo ao rolar (a caixa rola por dentro, até 75% da altura da tela, então funciona também com rolagem horizontal);
 *  - ordenação por botão no cabeçalho (teclado incluso), com `aria-sort` e seta;
 *  - ⓘ com a explicação de cada coluna (`meta.dica`);
 *  - paginação local com seletor de linhas por página e total de linhas;
 *  - rótulo obrigatório (NBR 17225 5.6.5) e, no celular, cartões com até 4 campos;
 *  - linhas expansíveis (`linhaExpandida`) e ações no topo (`acoes`, ex.: CSV).
 * Paginar ou expandir listas com mais de 100 itens no servidor continua sendo regra de acesso (`login`): esta tabela só pagina o que já recebeu.
 */
export function TabelaDados<T>({ colunas, dados, rotulo, tamanhoPagina = 25, tamanhos = [25, 50, 100, 250], linhaExpandida, snapshot, vazio, acoes, forcarCartao, semCartao }: {
  colunas: ColumnDef<T, any>[]
  dados: T[]
  rotulo: string
  tamanhoPagina?: number
  /** Opções do seletor de linhas por página ([] esconde o seletor). */
  tamanhos?: number[]
  linhaExpandida?: (linha: Row<T>) => ReactNode
  snapshot?: string | null
  vazio?: string
  acoes?: ReactNode
  /** Cartões em qualquer largura (testes, páginas estreitas). */
  forcarCartao?: boolean
  /** Nunca vira cartão (tabelas cujo sentido depende da grade). */
  semCartao?: boolean
}) {
  const [sorting, setSorting] = useState<SortingState>([])
  const estreita = useTelaEstreita()
  const tabela = useReactTable({
    data: dados, columns: colunas, state: { sorting }, onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(), getSortedRowModel: getSortedRowModel(), getPaginationRowModel: getPaginationRowModel(),
    getExpandedRowModel: getExpandedRowModel(), getRowCanExpand: () => !!linhaExpandida,
    initialState: { pagination: { pageSize: tamanhoPagina } },
  })
  if (dados.length === 0) return <EmptyState mensagem={vazio} snapshot={snapshot} />

  const { pageIndex, pageSize } = tabela.getState().pagination
  const paginas = tabela.getPageCount()
  const linhas = tabela.getRowModel().rows
  const cartao = !semCartao && (forcarCartao || estreita)
  const meta = (c: { columnDef: { meta?: unknown } }) => (c.columnDef.meta ?? {}) as MetaColuna
  // Tamanhos úteis: cada um cujo anterior ainda não mostra todas as linhas (com 30 linhas: 25 e 50).
  const opcoes = tamanhos.filter((n, i) => i === 0 || tamanhos[i - 1] < dados.length || n === pageSize)

  return (
    <div>
      {acoes && <div className="mb-2 flex justify-end">{acoes}</div>}
      {cartao ? (
        <ul className="space-y-2" aria-label={rotulo}>
          {linhas.map((r) => {
            const campos = r.getVisibleCells().filter((c) => meta(c.column).cartao !== false).slice(0, 4)
            const [titulo, ...resto] = campos
            return (
              <li key={r.id} className="rounded-lg border border-gray-200 bg-white p-3" data-testid="cartao">
                {titulo && <div className="font-medium text-gray-900">{flexRender(titulo.column.columnDef.cell, titulo.getContext())}</div>}
                <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-sm">
                  {resto.map((c) => (
                    <div key={c.id} className="contents">
                      <dt className="text-xs text-gray-500">{typeof c.column.columnDef.header === 'string' ? c.column.columnDef.header : c.column.id}</dt>
                      <dd className="min-w-0 break-words text-gray-800">{flexRender(c.column.columnDef.cell, c.getContext())}</dd>
                    </div>
                  ))}
                </dl>
                {linhaExpandida && <div className="mt-2 border-t border-gray-100 pt-2 text-sm">{linhaExpandida(r)}</div>}
              </li>
            )
          })}
        </ul>
      ) : (
        <div className="max-h-[75vh] overflow-auto rounded border border-gray-200 bg-white" data-testid="tabela-dados">
          <table className="min-w-full text-sm" aria-label={rotulo}>
            <thead className="sticky top-0 z-10 bg-gray-50 shadow-[0_1px_0_0_#e5e7eb]">
              {tabela.getHeaderGroups().map((g) => (
                <tr key={g.id} className="text-left text-xs text-gray-600">
                  {linhaExpandida && <th className="w-6" aria-label="Expandir" />}
                  {g.headers.map((h) => {
                    const m = meta(h.column)
                    const ordenavel = h.column.getCanSort()
                    const sentido = h.column.getIsSorted()
                    const rot = flexRender(h.column.columnDef.header, h.getContext())
                    const texto = typeof h.column.columnDef.header === 'string' ? h.column.columnDef.header : h.column.id
                    return (
                      <th key={h.id} scope="col" className={`whitespace-nowrap px-2 py-1.5 align-bottom font-medium ${ALINHAR[m.alinhar ?? 'left']}`}
                        aria-sort={sentido === 'asc' ? 'ascending' : sentido === 'desc' ? 'descending' : 'none'}>
                        <span className="inline-flex flex-wrap items-center gap-0.5">
                          {ordenavel ? (
                            <button type="button" className="min-h-6 rounded hover:text-gray-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario-500" onClick={h.column.getToggleSortingHandler()}>
                              {rot}<span aria-hidden="true" className={sentido ? 'text-primario-700' : 'text-gray-300'}>{sentido === 'asc' ? ' ▲' : sentido === 'desc' ? ' ▼' : ' ↕'}</span>
                            </button>
                          ) : rot}
                          {m.dica && <Dica texto={m.dica} rotulo={texto} />}
                        </span>
                      </th>
                    )
                  })}
                </tr>
              ))}
            </thead>
            <tbody>
              {linhas.map((r) => (
                <Fragment key={r.id}>
                  <tr className="border-t border-gray-100 hover:bg-gray-50">
                    {linhaExpandida && (
                      <td className="px-1">
                        <button type="button" aria-expanded={r.getIsExpanded()} aria-label={r.getIsExpanded() ? 'Recolher linha' : 'Expandir linha'}
                          className="text-gray-500 hover:text-gray-800" onClick={r.getToggleExpandedHandler()}>
                          {r.getIsExpanded() ? '▾' : '▸'}
                        </button>
                      </td>
                    )}
                    {r.getVisibleCells().map((c) => (
                      <td key={c.id} className={`px-2 py-1 ${ALINHAR[meta(c.column).alinhar ?? 'left']} ${meta(c.column).alinhar === 'right' ? 'tabular-nums' : ''}`}>
                        {flexRender(c.column.columnDef.cell, c.getContext())}
                      </td>
                    ))}
                  </tr>
                  {linhaExpandida && r.getIsExpanded() && (
                    <tr className="bg-gray-50"><td colSpan={r.getVisibleCells().length + 1} className="px-4 py-2">{linhaExpandida(r)}</td></tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {(paginas > 1 || opcoes.length > 1) && (
        <nav className="mt-2 flex flex-wrap items-center gap-2 text-xs text-gray-600" aria-label={`Paginação de ${rotulo}`}>
          <button type="button" className="min-h-8 rounded border border-gray-300 px-3 py-1 hover:bg-gray-50 disabled:opacity-40" onClick={() => tabela.previousPage()} disabled={!tabela.getCanPreviousPage()}>Anterior</button>
          <span aria-live="polite">Página {pageIndex + 1} de {Math.max(paginas, 1)} · {dados.length.toLocaleString('pt-BR')} linhas</span>
          <button type="button" className="min-h-8 rounded border border-gray-300 px-3 py-1 hover:bg-gray-50 disabled:opacity-40" onClick={() => tabela.nextPage()} disabled={!tabela.getCanNextPage()}>Próxima</button>
          {opcoes.length > 1 && (
            <label className="ml-auto flex items-center gap-1">
              Linhas por página
              <select className="min-h-8 rounded border border-gray-300 bg-white px-1" value={pageSize} onChange={(e) => tabela.setPageSize(Number(e.target.value))}>
                {opcoes.map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </label>
          )}
        </nav>
      )}
    </div>
  )
}
