// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { EmptyState, formatarReferencia, rotuloFrescor, type FonteEntrada } from '../components/entidade'
import { descreverCadencia, rotuloTipo, type Catalogo, type CampoCatalogo, type FonteCatalogo } from '../features/fontes/catalogo'
import { useFontes } from '../hooks/entidades'

/** Quantas fontes aparecem antes de "mostrar todas" (a tabela completa ocupa 8 telas; a meta é ≤ 4). */
const TAMANHO_LOTE = 18

function CartaoFonte({ f, entrada, temSnapshot }: { f: FonteCatalogo; entrada?: FonteEntrada; temSnapshot: boolean }) {
  return (
    <li className="bg-white rounded-lg border border-gray-200 p-3 flex flex-col">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="font-medium text-gray-900 leading-snug">{f.nome}</div>
          <div className="text-xs text-gray-400 font-mono truncate">{f.id}</div>
        </div>
        <span className="text-xs rounded bg-gray-100 text-gray-600 px-1.5 py-0.5 shrink-0">{rotuloTipo(f.tipo)}</span>
      </div>
      <dl className="mt-2 space-y-1 text-xs text-gray-600">
        <div><dt className="inline text-gray-400">Licença: </dt><dd className="inline">{f.origem.licenca ?? <span className="text-aviso-700">não verificada</span>} · uso comercial: {f.uso_comercial_efetivo ?? 'não verificado'}</dd></div>
        <div><dt className="inline text-gray-400">Periodicidade: </dt><dd className="inline">{descreverCadencia(f.cadencia)}</dd></div>
        <div><dt className="inline text-gray-400">Última coleta: </dt><dd className="inline">{entrada
          ? <>ref. {formatarReferencia(entrada.as_of)}{entrada.coletado_em ? ` · coletado em ${formatarReferencia(entrada.coletado_em)}` : ''} <span className="text-gray-400">({rotuloFrescor(entrada)})</span></>
          : <span className="text-gray-400">{temSnapshot ? 'sem versão neste snapshot' : '—'}</span>}</dd></div>
      </dl>
      <details className="mt-2 text-xs">
        <summary className="cursor-pointer text-primario-600 hover:underline">Detalhes e campos ({f.campos.length})</summary>
        <div className="mt-2"><DetalheFonte f={f} /></div>
      </details>
    </li>
  )
}

function Campos({ campos }: { campos: CampoCatalogo[] }) {
  if (campos.length === 0) return <p className="text-xs text-gray-500">Sem campos documentados.</p>
  return (
    <table className="w-full text-xs">
      <thead><tr className="text-left text-gray-400 border-b border-gray-100"><th className="py-1 pr-3">Campo</th><th className="pr-3">Tipo</th><th className="pr-3">O que significa</th><th>Como é tratado</th></tr></thead>
      <tbody className="divide-y divide-gray-50">
        {campos.map((c, i) => (
          <tr key={`${i}-${c.nome}`} className="align-top"><td className="py-1 pr-3 font-mono">{c.nome}</td><td className="pr-3 text-gray-500">{c.tipo}</td><td className="pr-3">{c.significado}</td><td className="text-gray-600">{c.tratamento ?? '—'}</td></tr>
        ))}
      </tbody>
    </table>
  )
}

function DetalheFonte({ f }: { f: FonteCatalogo }) {
  return (
    <div className="space-y-2 text-sm">
      <p className="break-words">{f.descricao}</p>
      <dl className="grid md:grid-cols-2 gap-x-6 gap-y-1 text-xs text-gray-600">
        <div><dt className="inline text-gray-400">Origem: </dt><dd className="inline">{f.origem.url ? <a href={f.origem.url} target="_blank" rel="noopener noreferrer" className="text-primario-600 hover:underline break-all">{f.origem.url}</a> : '—'}</dd></div>
        <div><dt className="inline text-gray-400">Formato: </dt><dd className="inline">{f.origem.formato ?? '—'}</dd></div>
        <div><dt className="inline text-gray-400">Termos: </dt><dd className="inline">{f.origem.termos ? <a href={f.origem.termos} target="_blank" rel="noopener noreferrer" className="text-primario-600 hover:underline break-all">{f.origem.termos}</a> : '—'}</dd></div>
        <div><dt className="inline text-gray-400">Frescor máximo tolerado: </dt><dd className="inline">{f.cadencia.frescor_maximo ?? '—'}</dd></div>
      </dl>
      {f.origem.nota && <p className="text-xs text-gray-500 break-words">{f.origem.nota}</p>}
      {f.nao_verificado.length > 0 && <p className="text-xs text-aviso-700 bg-aviso-50 border border-aviso-200 rounded px-2 py-1">Ainda não verificado: {f.nao_verificado.join(', ')}.</p>}
      <Campos campos={f.campos} />
    </div>
  )
}

/** `/fontes`: gerada do catálogo — cada fonte com licença, periodicidade, última coleta no snapshot ativo e os campos que produz; depois os produtos e seus limites. */
export function FontesPage() {
  const cat = useQuery<Catalogo>({ queryKey: ['catalogo'], queryFn: () => fetch('/catalogo.json').then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() }), staleTime: Infinity, gcTime: Infinity, retry: false })
  const { fontes, snapshot } = useFontes()
  const [busca, setBusca] = useState('')
  const [tipo, setTipo] = useState('')

  const porId = useMemo(() => new Map<string, FonteEntrada>((fontes ?? []).map((f) => [f.id, f])), [fontes])
  const lista = useMemo(() => (cat.data?.fontes ?? []).filter((f) => (!tipo || f.tipo === tipo)
    && (!busca || `${f.id} ${f.nome} ${f.descricao}`.toLowerCase().includes(busca.toLowerCase()))), [cat.data, busca, tipo])

  const [limite, setLimite] = useState(TAMANHO_LOTE)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Fontes de dados</h1>
        <p className="text-sm text-gray-500 mt-1">
          De onde vem cada número, sob qual licença e com que frequência é atualizado. Esta página é gerada do catálogo de fontes do projeto; a coluna “última coleta”
          vem do snapshot {snapshot ?? 'ativo'}.
        </p>
      </div>

      {cat.isLoading && <p className="text-sm text-gray-400" role="status">Carregando o catálogo…</p>}
      {cat.isError && <EmptyState mensagem="Catálogo indisponível" detalhe="O arquivo /catalogo.json não pôde ser carregado." />}

      {cat.data && (
        <section aria-labelledby="fontes-titulo">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <h2 id="fontes-titulo" className="text-base font-semibold text-gray-800">Fontes ({lista.length} de {cat.data.fontes.length})</h2>
            <input type="search" aria-label="Buscar fonte" placeholder="Buscar fonte…" value={busca} onChange={(e) => { setBusca(e.target.value); setLimite(TAMANHO_LOTE) }} className="ml-auto border border-gray-300 rounded-md px-3 py-1 text-sm" />
            <select aria-label="Tipo de fonte" value={tipo} onChange={(e) => setTipo(e.target.value)} className="border border-gray-300 rounded-md px-2 py-1 text-sm">
              <option value="">Todos os tipos</option>
              {[...new Set(cat.data.fontes.map((f) => f.tipo))].map((t) => <option key={t} value={t}>{rotuloTipo(t)}</option>)}
            </select>
          </div>
          {lista.length === 0 ? <EmptyState mensagem="Nenhuma fonte com esse filtro" /> : (
            <>
              <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3" aria-label="Fontes de dados">
                {lista.slice(0, limite).map((f) => <CartaoFonte key={f.id} f={f} entrada={porId.get(f.id)} temSnapshot={!!fontes} />)}
              </ul>
              {lista.length > limite && (
                <button type="button" onClick={() => setLimite(lista.length)} className="mt-3 rounded border border-gray-300 px-3 py-1 text-sm text-gray-700 hover:bg-gray-50">
                  Mostrar todas as fontes ({lista.length - limite} restantes)
                </button>
              )}
            </>
          )}
        </section>
      )}

      {cat.data && (
        <section aria-labelledby="produtos-titulo">
          <details>
          <summary className="cursor-pointer"><h2 id="produtos-titulo" className="inline text-base font-semibold text-gray-800">Produtos e indicadores ({cat.data.produtos.length})</h2></summary>
          <div className="space-y-2 mt-2">
            {cat.data.produtos.map((p) => (
              <details key={p.id} className="bg-white rounded-lg border border-gray-200 px-4 py-2">
                <summary className="cursor-pointer font-medium text-gray-800">{p.nome} <span className="text-xs text-gray-400 font-mono ml-1">{p.id}</span></summary>
                <div className="mt-2 space-y-2 text-sm">
                  <p>{p.descricao}</p>
                  {p.limites && <p className="text-xs text-gray-600"><strong>Limites:</strong> {p.limites}</p>}
                  {p.pendencias.length > 0 && <p className="text-xs text-aviso-700"><strong>Pendências:</strong> {p.pendencias.join('; ')}</p>}
                  <Campos campos={p.campos} />
                </div>
              </details>
            ))}
          </div>
          </details>
        </section>
      )}
    </div>
  )
}
