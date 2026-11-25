// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { EmptyState } from '../components/entidade'
import { Construtor } from '../features/explorar/Construtor'
import { Resultado, type RespostaConsulta } from '../features/explorar/Resultado'
import { deUrl, estadoDeReceita, estadoInicial, montarCorpo, paraUrl, type EstadoConsulta, type SchemaConsulta } from '../features/explorar/consulta'
import { useActiveDate } from '../hooks/useSnapshot'
import { AccessError, fetchCaminho, queryColecao } from '../services/api'
import { EstadoDados } from '../components/ui/EstadoDados'

/** O corpo do erro da API vem como `HTTP 400: {"detail": "..."}`; mostra só o detalhe. */
export function detalheDoErro(e: Error | null): string {
  const m = /^HTTP \d+:?\s*([\s\S]*)$/.exec(e?.message ?? '')
  const corpo = (m ? m[1] : e?.message ?? '').trim()
  try {
    const d = (JSON.parse(corpo) as { detail?: unknown }).detail
    if (typeof d === 'string') return d
  } catch { /* corpo não era JSON */ }
  return corpo || 'erro desconhecido'
}

/**
 * `/explorar`: o mesmo motor de consulta do MCP (`POST /query/{collection}`) com um construtor visual montado a partir de `GET /schema`.
 * A consulta inteira fica na URL (`?c=…&q=…`), então é compartilhável; "Receitas" carrega as perguntas prontas do próprio schema.
 */
export function ExplorarPage() {
  const date = useActiveDate()
  const [params, setParams] = useSearchParams()
  const schemaQ = useQuery({ queryKey: ['schema-consulta'], queryFn: () => fetchCaminho<SchemaConsulta>('/api/v1/schema'), staleTime: Infinity, gcTime: Infinity, retry: false })
  const schema = schemaQ.data

  const daUrl = useMemo(() => (schema ? deUrl(params, schema) : null), [params, schema])
  const [estado, setEstado] = useState<EstadoConsulta | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)
  const [erroValor, setErroValor] = useState<string | null>(null)

  // A URL manda: abrir um link (ou voltar no histórico) carrega a consulta e já a executa.
  useEffect(() => { if (daUrl) setEstado(daUrl) }, [daUrl])
  useEffect(() => { if (schema && !params.get('c') && !estado) setEstado(estadoInicial(Object.keys(schema.collections)[0])) }, [schema, params, estado])

  const corpoExecutado = useMemo(() => {
    if (!schema || !daUrl) return null
    try { return montarCorpo(daUrl, schema) } catch { return null }
  }, [schema, daUrl])

  const resultado = useQuery({
    queryKey: ['explorar', daUrl?.colecao, corpoExecutado, date],
    queryFn: () => queryColecao<RespostaConsulta>(daUrl!.colecao, corpoExecutado!, date ?? undefined),
    enabled: !!daUrl && !!corpoExecutado && !!date, staleTime: 5 * 60 * 1000, retry: false,
  })

  function executar(e: EstadoConsulta) {
    if (!schema) return
    try { montarCorpo(e, schema); setErroValor(null) } catch (err) { setErroValor((err as Error).message); return }
    setParams(paraUrl(e, date))
  }

  function carregarReceita(i: string) {
    if (!schema || i === '') return
    const r = schema.recipes.filter((x) => x.args?.collection)[Number(i)]
    const conv = r?.args ? estadoDeReceita(r.args, schema) : null
    if (!conv) { setAviso('Esta receita não usa uma coleção consultável aqui.'); return }
    setAviso(conv.avisos.length ? conv.avisos.join('; ') : null)
    setEstado(conv.estado)
    executar(conv.estado)
  }

  const receitas = useMemo(() => (schema?.recipes ?? []).filter((r) => r.args?.collection), [schema])
  const erro = resultado.error as (Error & { message: string }) | null

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Explorador de consultas</h1>
        <p className="text-sm text-gray-500 mt-1">Filtre, ordene e agrupe qualquer coleção de dados. É o mesmo motor que responde ao servidor MCP; a consulta fica no endereço da página e pode ser compartilhada.</p>
      </div>

      {schemaQ.isLoading && <p className="text-sm text-gray-400" role="status">Carregando o esquema…</p>}
      {schemaQ.isError && <EmptyState mensagem="Esquema indisponível" detalhe="Não foi possível carregar a descrição das coleções." />}

      {schema && estado && (
        <>
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <label className="text-gray-600">Receitas{' '}
              <select aria-label="Receitas" className="border border-gray-300 rounded-md px-2 py-1 text-sm bg-white max-w-[calc(100vw-2rem)] sm:max-w-xl" value="" onChange={(e) => carregarReceita(e.target.value)}>
                <option value="">carregar uma pergunta pronta…</option>
                {receitas.map((r, i) => <option key={r.pergunta} value={i}>{r.pergunta}</option>)}
              </select>
            </label>
            <button type="button" className="text-primario-600 hover:underline" onClick={() => navigator.clipboard?.writeText(window.location.href)}>Copiar link da consulta</button>
          </div>
          {aviso && <p className="text-xs text-aviso-700 bg-aviso-50 border border-aviso-200 rounded px-3 py-2" role="status">{aviso}</p>}
          <Construtor schema={schema} estado={estado} onChange={setEstado} onExecutar={() => executar(estado)} executando={resultado.isFetching} />
          {erroValor && <p className="text-sm text-perigo-700 bg-perigo-50 border border-perigo-200 rounded px-3 py-2" role="alert">{erroValor}</p>}
        </>
      )}

      {resultado.isError && (erro instanceof AccessError ? <EstadoDados erro={erro} oQue="a consulta" /> : (
        <p className="text-sm text-perigo-700 bg-perigo-50 border border-perigo-200 rounded px-3 py-2" role="alert">
          {`A consulta não pôde ser executada: ${detalheDoErro(erro)}`}
        </p>
      ))}
      {resultado.data && daUrl && (
        <Resultado colecao={daUrl.colecao} resposta={resultado.data} pagina={daUrl.pagina} onPagina={(p) => executar({ ...daUrl, pagina: p })}
          ordem={daUrl.ordem} onOrdem={(o) => executar({ ...daUrl, ordem: o, pagina: 1 })}
          camposOrdenaveis={schema ? new Set(schema.collections[daUrl.colecao]?.fields.map((f) => f.name) ?? []) : undefined} />
      )}
      {corpoExecutado && (
        <details className="text-xs text-gray-500">
          <summary className="cursor-pointer">Ver a consulta (para usar na API ou no MCP)</summary>
          <pre aria-label="Corpo da consulta" className="mt-2 bg-gray-900 text-ok-300 rounded-lg p-3 overflow-x-auto">{`curl -s -X POST '${window.location.origin}/api/v1/query/${daUrl?.colecao}${date ? `?date=${date}` : ''}' \\\n  -H 'content-type: application/json' \\\n  -d '${JSON.stringify(corpoExecutado)}'`}</pre>
        </details>
      )}
    </div>
  )
}
