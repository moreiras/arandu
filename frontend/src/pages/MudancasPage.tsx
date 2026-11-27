// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Link } from '../components/layout/LinkDatado'
import { useQuery } from '@tanstack/react-query'
import { fetchMudancas, fetchMudancasResumo } from '../services/api'
import { useSnapshots } from '../hooks/useSnapshot'
import { useAuth } from '../auth/AuthContext'
import { EstadoDados } from '../components/ui/EstadoDados'
import { fraseEvento, inicioDosSnapshots, ROTULO_ESTADO, TIPOS_DA_PAGINA } from '../features/historico/rotulos'
import { UFS, nomeUf } from '../lib/ufs'
import { NotaRevisao } from '../components/ui/NotaRevisao'
import { ComoLer } from '../components/ui/ComoLer'
import { VerDados } from '../components/ui/VerDados'
import { notasParaTipos } from '../lib/notasRevisao'

const POR_PAGINA = 100

function alvo(e: { entidade: string; asn?: number }): { to: string; texto: string } | null {
  if (e.entidade.startsWith('asn:')) return { to: `/asn/${e.entidade.slice(4)}`, texto: `AS${e.entidade.slice(4)}` }
  if (e.entidade.startsWith('prefixo:') && e.asn) return { to: `/asn/${e.asn}`, texto: `AS${e.asn}` }
  if (e.entidade.startsWith('cnpj:')) return { to: `/operadora/${e.entidade.slice(5)}`, texto: e.entidade.slice(5) }
  return null
}

/**
 * `/mudancas` — O que mudou: diferenças observadas entre snapshots consecutivos, por tipo e UF, só as confirmadas por padrão.
 * Linguagem de evidência: é o que as duas fotografias mostram, sem causa nem intenção e sem nome de empresa. Eventos de provedor (ARC v1,
 * inferência) ficam fora. Sem login a API entrega só a partir do penúltimo snapshot; com login, tudo que há.
 */
export function MudancasPage() {
  const { anon, loading } = useAuth()
  const [params] = useSearchParams()
  const tipoInicial = params.get('tipo') ?? ''
  const [tipo, setTipo] = useState(TIPOS_DA_PAGINA.includes(tipoInicial) ? tipoInicial : '')
  const [uf, setUf] = useState('')
  const [pendentes, setPendentes] = useState(false)
  const [pagina, setPagina] = useState(0)
  const snaps = useSnapshots()
  const recentes = (snaps.data?.snapshots ?? []).slice(-2)
  const inicio = inicioDosSnapshots(snaps.data?.snapshots)
  const limitado = !!anon
  const from = limitado ? recentes[0] : undefined
  const pronto = !loading && !!snaps.data
  const tipos = tipo || TIPOS_DA_PAGINA.join(',')
  const estado = pendentes ? 'confirmado,pendente' : 'confirmado'

  const lista = useQuery({
    queryKey: ['mudancas', from ?? 'tudo', tipos, uf, estado, pagina],
    queryFn: () => fetchMudancas({ from, tipo: tipos, uf: uf || undefined, estado, limit: POR_PAGINA, offset: pagina * POR_PAGINA }),
    enabled: pronto, staleTime: 5 * 60 * 1000, retry: false,
  })
  const resumo = useQuery({ queryKey: ['mudancas-resumo', from ?? 'tudo'], queryFn: () => fetchMudancasResumo(from), enabled: pronto, staleTime: 5 * 60 * 1000, retry: false })

  const itens = lista.data?.items ?? []
  const total = lista.data?.total ?? 0
  // agrupado por tipo: a ordem é a do primeiro evento de cada tipo, que a API já entrega do mais recente ao mais antigo
  const grupos = [...itens.reduce((m, e) => m.set(e.tipo, [...(m.get(e.tipo) ?? []), e]), new Map<string, typeof itens>())]
  const novoFiltro = (f: () => void) => { f(); setPagina(0) }
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-titulo-1 text-gray-900">O que mudou</h1>
        <p className="text-sm text-gray-500 mt-1">
          Diferenças observadas entre snapshots consecutivos: ASes que passaram a aparecer ou sumiram, entradas e saídas de PTTs, prefixos cuja origem mudou,
          ROAs, RPKI e outorgas. Cada item é o que as duas fotografias mostram, sem causa nem intenção atribuída. Por padrão só entram os confirmados:
          entradas e saídas do cadastro de PTTs, ROAs ganhos ou perdidos, ASPA e outorgas novas contam como confirmados no snapshot em que aparecem;
          os demais tipos, quando o novo estado se mantém no snapshot seguinte.{inicio && ` Os snapshots publicados começam em ${inicio}.`}{' '}
          <a href="/api/v1/feed/mudancas.atom" className="text-primario-600 hover:underline">Assinar por feed (Atom)</a>.
        </p>
      </div>
      {limitado && (
        <p className="text-sm text-aviso-700 bg-aviso-50 border border-aviso-200 rounded px-3 py-2">
          Sem login você vê as mudanças dos 2 snapshots mais recentes. <Link to="/login" className="underline">Entre</Link> para ver todo o histórico.
        </p>
      )}
      <div className="flex flex-wrap items-end gap-3 text-sm">
        <label className="flex flex-col gap-0.5">
          <span className="text-xs text-gray-500">Tipo</span>
          <select value={tipo} onChange={(e) => novoFiltro(() => setTipo(e.target.value))} className="border border-gray-200 rounded px-2 py-1 bg-white">
            <option value="">Todos</option>
            {TIPOS_DA_PAGINA.map((t) => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-0.5">
          <span className="text-xs text-gray-500">UF</span>
          <select value={uf} onChange={(e) => novoFiltro(() => setUf(e.target.value))} className="border border-gray-200 rounded px-2 py-1 bg-white">
            <option value="">Todas</option>
            {Object.keys(UFS).map((u) => <option key={u} value={u}>{u} ({nomeUf(u)})</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1.5 pb-1">
          <input type="checkbox" checked={pendentes} onChange={(e) => novoFiltro(() => setPendentes(e.target.checked))} />
          <span>Incluir os ainda em confirmação</span>
        </label>
      </div>
      {notasParaTipos(tipo ? [tipo] : []).map((n) => <NotaRevisao key={n.id} nota={n} aberta />)}
      {resumo.data && (
        <p className="text-xs text-gray-500">
          {resumo.data.snapshots_com_historico} snapshots com histórico · {Object.keys(resumo.data.por_data).length} datas com mudanças · {total.toLocaleString('pt-BR')} resultados com este filtro.
        </p>
      )}
      {resumo.data && Object.keys(resumo.data.por_data).length > 0 && (
        <section className="space-y-1" aria-label="Eventos por data" data-testid="mudancas-por-data">
          {Object.entries(resumo.data.datas_atipicas ?? {}).map(([d, a]) => (
            <p key={d} className="text-xs text-aviso-700" data-testid="data-atipica">
              Data atípica marcada, {d}: os eventos de {a.tipos.map((t) => t.replace(/_/g, ' ')).join(', ')} dessa data têm uma ressalva ({a.motivo}). A contagem foi mantida e não deve ser comparada com a das outras datas.
            </p>
          ))}
          <VerDados titulo="Ver eventos por data (tabela)" rotulos={{ data: 'Data', eventos: 'Eventos (todos os estados)', marca: 'Marca' }} campos={['data', 'eventos', 'marca']}
            dados={Object.entries(resumo.data.por_data).sort(([a], [b]) => (a < b ? 1 : -1)).map(([d, n]) => ({ data: d, eventos: n, marca: resumo.data?.datas_atipicas?.[d] ? 'data atípica' : '' }))} />
          <ComoLer>
            <p>A contagem por data soma todos os estados e os tipos de evento do filtro da API (sem eventos de provedor). Datas atípicas ficam na série, marcadas, e não são comparadas com as demais: a regra de comparabilidade é a mesma das séries do site, e o texto completo dela está em Comparar datas e nas séries.</p>
          </ComoLer>
        </section>
      )}
      {resumo.isError && !lista.isError && <EstadoDados erro={resumo.error} oQue="o resumo das mudanças" mensagem="O resumo das mudanças não está publicado." />}
      {lista.isLoading && <p className="text-sm text-gray-400" role="status">Carregando…</p>}
      {lista.isError && <EstadoDados erro={lista.error} oQue="as mudanças" mensagem="Não há mudanças publicadas para este filtro." aoTentarDeNovo={() => void lista.refetch()} />}
      {!lista.isLoading && !lista.isError && itens.length === 0 && <p className="text-sm text-gray-500" role="status">Nenhuma mudança com este filtro nos snapshots com histórico.</p>}
      {itens.length > 0 && (
        <div className="space-y-3" data-testid="mudancas-por-tipo">
          {grupos.map(([t, lista], i) => (
            <details key={t} open={i < 3 || tipo !== ''} className="bg-white border border-gray-200 rounded-lg">
              <summary className="cursor-pointer px-3 py-2 text-sm font-semibold text-gray-800">
                {t.replace(/_/g, ' ')} <span className="font-normal text-gray-500">· {lista.length}{total > itens.length ? ' nesta página' : ''}</span>
              </summary>
              <ul className="divide-y divide-gray-100 border-t border-gray-100">
                {lista.map((e) => {
                  const a = alvo(e)
                  return (
                    <li key={`${e.data}-${e.tipo}-${e.entidade}-${e.chave}`} className="px-3 py-2 flex flex-wrap items-baseline gap-x-3 text-sm">
                      <time className="text-xs text-gray-500 tabular-nums w-24">{e.data}</time>
                      <span className="flex-1 min-w-[16rem]">{fraseEvento(e)}</span>
                      {a && <Link to={a.to} className="text-primario-600 hover:underline">{a.texto}</Link>}
                      {e.uf && <span className="text-xs text-gray-500">{e.uf}</span>}
                      {e.destaque && <span className="text-xs text-aviso-700">novo estado: RPKI inválido</span>}
                      <span className={`text-xs ${e.estado === 'pendente' ? 'text-gray-500 italic' : 'text-gray-400'}`}>{ROTULO_ESTADO[e.estado]}</span>
                    </li>
                  )
                })}
              </ul>
            </details>
          ))}
        </div>
      )}
      {total > POR_PAGINA && (
        <div className="flex items-center gap-3 text-sm">
          <button disabled={pagina === 0} onClick={() => setPagina(pagina - 1)} className="px-2 py-1 border rounded disabled:opacity-40">Anterior</button>
          <span className="text-gray-500">Página {pagina + 1} de {Math.ceil(total / POR_PAGINA)}</span>
          <button disabled={(pagina + 1) * POR_PAGINA >= total} onClick={() => setPagina(pagina + 1)} className="px-2 py-1 border rounded disabled:opacity-40">Próxima</button>
        </div>
      )}
    </div>
  )
}
