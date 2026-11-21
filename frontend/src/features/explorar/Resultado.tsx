// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import type { ColumnDef } from '@tanstack/react-table'
import { DataTable, EmptyState } from '../../components/entidade'
import type { OrdemServidor } from '../../components/ui/TabelaDados'
import { formatarCelula, linkDoCampo } from './consulta'

export interface RespostaConsulta {
  mode: 'list' | 'aggregate'
  snapshot_date?: string
  collection?: string
  total?: number
  page?: number
  pages?: number
  limit?: number
  items?: Array<Record<string, unknown>>
  matched?: number
  groups?: Array<{ key: Record<string, unknown>; [k: string]: unknown }>
}

function Celula({ colecao, campo, valor }: { colecao: string; campo: string; valor: unknown }) {
  const link = linkDoCampo(colecao, campo, valor)
  const texto = formatarCelula(valor)
  return link ? <Link to={link} className="text-primario-600 hover:underline">{texto}</Link> : <span className={typeof valor === 'number' ? 'tabular-nums' : ''}>{texto}</span>
}

/**
 * Resultado da consulta: tabela (lista ou grupos) com links nos campos-chave e paginação do servidor. Com o resultado inteiro na tela, a
 * ordenação é local; com só uma página dele (mais de uma página, ou o limite do anônimo), o clique no cabeçalho refaz a consulta com
 * `sort` no servidor (`onOrdem`), senão reordenaria só a página e esconderia quem lidera a coluna. Só ordenam os campos da coleção.
 */
export function Resultado({ colecao, resposta, pagina, onPagina, ordem, onOrdem, camposOrdenaveis }: {
  colecao: string; resposta: RespostaConsulta; pagina: number; onPagina: (p: number) => void
  ordem?: OrdemServidor | null; onOrdem?: (o: OrdemServidor | null) => void; camposOrdenaveis?: Set<string>
}) {
  const parcial = resposta.mode === 'list' && ((resposta.pages ?? 1) > 1 || (resposta.total ?? 0) > (resposta.items?.length ?? 0))
  const noServidor = parcial && !!onOrdem
  const linhas = useMemo(() => (resposta.mode === 'aggregate'
    ? (resposta.groups ?? []).map(({ key, ...resto }) => ({ ...key, ...resto }))
    : (resposta.items ?? [])), [resposta])
  const colunas = useMemo<ColumnDef<Record<string, unknown>, any>[]>(() => {
    const nomes: string[] = []
    for (const l of linhas.slice(0, 50)) for (const k of Object.keys(l)) if (!nomes.includes(k)) nomes.push(k)
    return nomes.map((n) => ({ id: n, header: n, accessorFn: (r) => r[n], cell: (c) => <Celula colecao={colecao} campo={n} valor={c.getValue()} />,
      enableSorting: !noServidor || !camposOrdenaveis || camposOrdenaveis.has(n),
      sortingFn: (a, b) => { const x = a.original[n], y = b.original[n]; return typeof x === 'number' && typeof y === 'number' ? x - y : String(x ?? '').localeCompare(String(y ?? '')) } }))
  }, [linhas, colecao, noServidor, camposOrdenaveis])

  const total = resposta.mode === 'aggregate' ? (resposta.groups?.length ?? 0) : resposta.total ?? linhas.length
  return (
    <section aria-label="Resultado da consulta" className="space-y-2">
      <div className="text-sm text-gray-600" role="status">
        {resposta.mode === 'aggregate'
          ? `${total.toLocaleString('pt-BR')} grupo${total !== 1 ? 's' : ''} (${(resposta.matched ?? 0).toLocaleString('pt-BR')} linhas consideradas)`
          : `${total.toLocaleString('pt-BR')} resultado${total !== 1 ? 's' : ''}${resposta.pages && resposta.pages > 1 ? ` · página ${resposta.page} de ${resposta.pages}` : ''}`}
        {resposta.snapshot_date && <span className="text-gray-400"> · snapshot {resposta.snapshot_date}</span>}
      </div>
      <div className="bg-white rounded-lg border border-gray-200 p-3 overflow-x-auto">
        {linhas.length === 0
          ? <EmptyState mensagem="Nenhuma linha atende à consulta" snapshot={resposta.snapshot_date} />
          : <DataTable rotulo="Resultado" colunas={colunas} dados={linhas} tamanhoPagina={1000}
              {...(noServidor ? { ordemServidor: ordem ?? null, onOrdemServidor: onOrdem } : {})} />}
      </div>
      {resposta.mode === 'list' && (resposta.pages ?? 1) > 1 && (
        <nav className="flex items-center gap-2 text-sm" aria-label="Páginas do resultado">
          <button type="button" className="rounded border px-3 py-1 disabled:opacity-40" disabled={pagina <= 1} onClick={() => onPagina(pagina - 1)}>← Anterior</button>
          <span className="text-gray-500">Página {pagina} de {resposta.pages}</span>
          <button type="button" className="rounded border px-3 py-1 disabled:opacity-40" disabled={pagina >= (resposta.pages ?? 1)} onClick={() => onPagina(pagina + 1)}>Próxima →</button>
        </nav>
      )}
    </section>
  )
}
