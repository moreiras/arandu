// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { useNavigate, Link, Navigate, useSearchParams } from 'react-router-dom'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useActiveDate } from '../hooks/useSnapshot'
import { useAuth } from '../auth/AuthContext'
import { fmtNum, UF_LIST } from '../features/operadoras/formato'
import { MapaAcessos } from '../features/operadoras/MapaAcessos'
import { MapaSede } from '../features/operadoras/MapaSede'
import { RankingsSici } from './RankingsPage'
import { DICAS_COLUNA, ORDEM_SERVICOS, SERVICOS, servicoDe, type Servico, type ServicoId } from '../features/operadoras/servicos'
import { Dica } from '../components/ui/Dica'
import type { ServicoOutorga } from '../services/api'
import { BarraDeAbas } from '../features/entidade/EntityPage'

const TODOS_SERVICOS: ServicoOutorga[] = ['SCM', 'SMP', 'STFC', 'SeAC']
const PORTES = ['Pequeno Porte', 'Grande Porte']

function SortArrow({ active, desc }: { active: boolean; desc: boolean }) {
  if (!active) return <span className="text-gray-300 ml-0.5">↕</span>
  return <span className="text-primario-600 ml-0.5">{desc ? '↓' : '↑'}</span>
}

/** Mapa do serviço: SCM e SMP têm as abas Sede/Acessos (SICI); STFC e SeAC, só a sede (não há declaração de acessos). */
function MapaServico({ servico, date, uf, comAsn }: { servico: Servico; date?: string; uf?: string; comAsn: boolean }) {
  const [modo, setModo] = useState<'sede' | 'sici'>('sici')
  if (!servico.temSici) return <MapaSede servico={servico} date={date} uf={uf} comAsn={comAsn} moldura />
  const botao = (m: 'sede' | 'sici', texto: string) => (
    <button type="button" aria-pressed={modo === m} onClick={() => setModo(m)} className={`px-3 py-1.5 font-medium transition-colors ${modo === m ? 'bg-gray-700 text-white' : 'text-gray-600 hover:bg-gray-50'}`}>{texto}</button>
  )
  return (
    <div className="relative rounded-lg border border-gray-200 overflow-hidden" style={{ height: 420 }}>
      <div role="group" aria-label="Camada do mapa" className="absolute top-3 left-3 z-10 flex text-xs bg-white/95 backdrop-blur rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        {botao('sede', 'Sede')}
        {botao('sici', 'Acessos (SICI)')}
      </div>
      {modo === 'sede' ? <MapaSede servico={servico} date={date} uf={uf} comAsn={comAsn} /> : <MapaAcessos servico={servico} date={date} />}
    </div>
  )
}

/** Lista de um serviço: estatísticas, mapa, filtros (na URL, para compartilhar) e tabela. Recriada a cada troca de serviço (ordenação e página recomeçam). */
function ListaServico({ servico }: { servico: Servico }) {
  const date = useActiveDate()
  const { requireLogin } = useAuth()
  const [params, setParams] = useSearchParams()
  const uf = params.get('uf') ?? ''
  const q = params.get('q') ?? ''
  const comAsn = params.get('com_asn') === '1'
  const ativoParam = params.get('ativo')
  const soAtivos = ativoParam == null ? servico.soAtivosPadrao : ativoParam === '1'
  // aba "Combinar serviços": serviços combináveis (qualquer um ou todos) e porte, também na URL
  const servicos = (params.get('servicos') ?? '').split(',').filter((x): x is ServicoOutorga => (TODOS_SERVICOS as string[]).includes(x))
  const todos = params.get('todos') === '1'
  const porte = params.get('porte') ?? ''

  const [page, setPage] = useState(1)
  const [sortBy, setSortBy] = useState(servico.ordenacaoPadrao.campo)
  const [sortDesc, setSortDesc] = useState(servico.ordenacaoPadrao.desc)
  const limit = 50

  /** Grava um filtro na URL (sem empilhar histórico); valor igual ao padrão sai da URL. */
  function definir(chave: string, valor: string | null) {
    const novo = new URLSearchParams(params)
    if (valor == null || valor === '') novo.delete(chave)
    else novo.set(chave, valor)
    setParams(novo, { replace: true })
    setPage(1)
  }

  const { data: stats } = useQuery({
    queryKey: [`${servico.id}-stats`, date],
    queryFn: () => servico.stats!(date ?? undefined),
    enabled: !!date && !!servico.stats,
    staleTime: 10 * 60 * 1000,
  })

  const { data, isLoading, isError } = useQuery({
    queryKey: [servico.chaveLista, date, page, uf, q, comAsn, soAtivos, sortBy, sortDesc, servicos.join(), todos, porte],
    queryFn: () => servico.listar({ date: date ?? undefined, page, limit, uf: uf || undefined, q: q || undefined, comAsn, soAtivos, sortBy, sortDesc, servicos, todos, porte: porte || undefined }),
    enabled: !!date,
    placeholderData: keepPreviousData,
    staleTime: Infinity, gcTime: Infinity,
  })

  function ordenar(campo: string) {
    if (sortBy === campo) setSortDesc((d) => !d)
    else { setSortBy(campo); setSortDesc(servico.primeiroCliqueDesc) }
    setPage(1)
  }

  if (isError) return (
    <div className="max-w-5xl mx-auto px-4 py-12 text-center">
      <p className="text-gray-500 text-sm">{servico.indisponivel}</p>
    </div>
  )

  const colunas = servico.colunas
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-titulo-1 text-gray-900">{servico.titulo}</h1>
        <p className="text-sm text-gray-500 mt-1">{servico.descricao}</p>
      </div>

      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Outorgas', value: stats.total.toLocaleString('pt-BR') },
            { label: 'CNPJs únicos', value: stats.unique_cnpjs.toLocaleString('pt-BR') },
            { label: 'Geolocalizadas', value: stats.geolocated.toLocaleString('pt-BR') },
            { label: 'CNPJs com ASN', value: stats.cnpjs_with_asn.toLocaleString('pt-BR') },
          ].map((s) => (
            <div key={s.label} className="bg-white rounded-lg border border-gray-200 px-4 py-3">
              <div className="text-xs text-gray-500">{s.label}</div>
              <div className="text-xl font-semibold text-gray-900 mt-0.5">{s.value}</div>
            </div>
          ))}
        </div>
      )}

      {servico.mapa && <MapaServico servico={servico} date={date ?? undefined} uf={uf || undefined} comAsn={comAsn} />}

      <div className="flex flex-wrap gap-2 items-center">
        <input
          type="text" placeholder="Buscar por nome ou CNPJ…" aria-label="Buscar por nome ou CNPJ" value={q}
          onChange={(e) => definir('q', e.target.value)}
          className="border border-gray-300 rounded-md px-3 py-1.5 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-primario-300"
        />
        <select
          value={uf} aria-label="UF" onChange={(e) => definir('uf', e.target.value)}
          className="border border-gray-300 rounded-md px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primario-300"
        >
          <option value="">Todas as UFs</option>
          {UF_LIST.map((u) => <option key={u} value={u}>{u}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
          <input type="checkbox" checked={comAsn} onChange={(e) => definir('com_asn', e.target.checked ? '1' : null)} className="rounded" />
          Apenas com AS identificado
        </label>
        {servico.id === 'todas' && (
          <>
            <fieldset className="flex items-center gap-2 text-sm text-gray-600">
              <legend className="sr-only">Serviços</legend>
              {TODOS_SERVICOS.map((sv) => (
                <label key={sv} className="flex items-center gap-1 cursor-pointer select-none">
                  <input type="checkbox" className="rounded" checked={servicos.includes(sv)}
                    onChange={(e) => definir('servicos', (e.target.checked ? [...servicos, sv] : servicos.filter((x) => x !== sv)).join(',') || null)} />
                  {sv}
                </label>
              ))}
            </fieldset>
            {servicos.length > 1 && (
              <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none" title="Marcado: só quem tem todos os serviços escolhidos; desmarcado: quem tem qualquer um">
                <input type="checkbox" checked={todos} onChange={(e) => definir('todos', e.target.checked ? '1' : null)} className="rounded" />
                Ter todos
              </label>
            )}
            <select value={porte} aria-label="Porte" onChange={(e) => definir('porte', e.target.value)}
              className="border border-gray-300 rounded-md px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primario-300">
              <option value="">Qualquer porte</option>
              {PORTES.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </>
        )}
        {(servico.temSici || servico.id === 'todas') && (
          <span className="flex items-center gap-1">
            <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
              <input type="checkbox" checked={soAtivos} className="rounded"
                onChange={(e) => definir('ativo', e.target.checked === servico.soAtivosPadrao ? null : e.target.checked ? '1' : '0')} />
              Apenas em operação
            </label>
            {/* a explicação ficava só no title do rótulo (teclado e toque não alcançam) */}
            {servico.dicaOperacao && <Dica texto={servico.dicaOperacao} rotulo="Apenas em operação" />}
          </span>
        )}
        {data && (
          <span className="text-xs text-gray-400 ml-auto">
            {data.total.toLocaleString('pt-BR')} resultado{data.total !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      <div className="relative">
        <div className="overflow-x-auto lg:overflow-x-clip rounded-lg border border-gray-200 bg-white">
          <table className="w-full table-fixed text-xs min-w-[720px]" aria-label={servico.titulo}>
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                {colunas.map((col) => (
                  <th
                    key={col.key} scope="col"
                    aria-sort={!col.ordenavel ? undefined : sortBy === col.key ? (sortDesc ? 'descending' : 'ascending') : 'none'}
                    className={`lg:sticky lg:top-[var(--altura-topo,89px)] z-10 px-3 py-1.5 text-left align-bottom font-medium select-none border-b border-gray-200 transition-colors ${col.w} ${col.ordenavel ? 'cursor-pointer' : ''} ${
                      sortBy === col.key ? 'text-primario-700 bg-primario-50' : 'text-gray-500 bg-gray-50 hover:bg-gray-100'
                    }`}
                  >
                    <span className="inline-flex flex-wrap items-center">
                    {col.ordenavel ? (
                      <button type="button" onClick={() => ordenar(col.key)} className="min-h-6 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario-500">
                        {col.label}<SortArrow active={sortBy === col.key} desc={sortDesc} />
                      </button>
                    ) : col.label}
                    {(col.dica ?? DICAS_COLUNA[col.key]) && <Dica texto={col.dica ?? DICAS_COLUNA[col.key]} rotulo={col.label} />}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {isLoading && <tr><td colSpan={colunas.length} className="px-3 py-8 text-center text-gray-400">Carregando…</td></tr>}
              {!isLoading && data?.items.length === 0 && <tr><td colSpan={colunas.length} className="px-3 py-8 text-center text-gray-400">Nenhum resultado encontrado.</td></tr>}
              {data?.items.map((r: any, i: number) => (
                <tr key={`${r.cnpj}-${i}`} className="hover:bg-tecnico-100 transition-colors">
                  {colunas.map((col) => <td key={col.key} className="px-3 py-1.5">{col.render(r)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {data && data.pages > 1 && (
          <div className="flex items-center justify-between mt-3 text-sm">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
              className="px-3 py-1 rounded border border-gray-300 text-xs text-gray-600 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-50"
            >← Anterior</button>
            <span className="text-gray-500 text-xs">Página {data.page} de {data.pages} · {fmtNum(data.total)} {servico.unidade}</span>
            <button
              onClick={() => { if (!requireLogin('lista-expandida')) return; setPage((p) => Math.min(data.pages, p + 1)) }}
              disabled={page >= data.pages}
              className="px-3 py-1 rounded border border-gray-300 text-xs text-gray-600 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-50"
            >Próxima →</button>
          </div>
        )}
      </div>
    </div>
  )
}

/** Ranking do SICI e omissão de declaração (`rdap`: vieram de Rankings): visões da página de operadoras, ao lado das listas por serviço. */
function VisaoSici({ visao }: { visao: 'ranking' | 'omissao' }) {
  const aba = (v: string, rot: string, ativa: boolean) => <Link to={v === 'lista' ? '/operadoras' : `/operadoras?visao=${v}`} aria-current={ativa ? 'page' : undefined} className={`px-4 py-2 text-sm -mb-px border-b-2 transition-colors ${ativa ? 'border-primario-600 text-primario-700 font-medium' : 'border-transparent text-gray-500 hover:text-gray-800'}`}>{rot}</Link>
  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      <nav aria-label="Visão das operadoras" className="flex gap-1 border-b border-gray-200">
        {aba('lista', 'Listas por serviço', false)}{aba('ranking', 'Ranking do SICI', visao === 'ranking')}{aba('omissao', 'Sem declaração ao SICI', visao === 'omissao')}
      </nav>
      <h1 className="text-titulo-1 text-gray-900">{visao === 'ranking' ? 'Operadoras por acessos declarados (SICI)' : 'Outorgas sem declaração ao SICI'}</h1>
      <RankingsSici abaFixa={visao === 'ranking' ? 'operadoras' : 'omissao'} />
    </div>
  )
}

/** `/operadoras?servico=scm|smp|stfc|seac`: as quatro páginas de outorga numa só, com abas por serviço. */
export function OperadorasPage() {
  const [params] = useSearchParams()
  const visao = params.get('visao')
  if (visao === 'ranking' || visao === 'omissao') return <VisaoSici visao={visao} />
  const servico = servicoDe(params.get('servico'))
  const outros = new URLSearchParams(params)
  outros.delete('servico')
  const aba = (id: ServicoId) => `/operadoras?servico=${id}`
  const navigate = useNavigate()
  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* a barra de abas única do site (setas do teclado); trocar de aba troca a URL. */}
      <BarraDeAbas abas={ORDEM_SERVICOS.map((id) => ({ id, rotulo: SERVICOS[id].rotulo }))} ativa={servico.id} aoEscolher={(id) => navigate(aba(id as ServicoId))} rotulo="Serviço outorgado" />
      <div role="tabpanel" id={`painel-${servico.id}`} aria-labelledby={`aba-${servico.id}`} className="space-y-6">
        <ListaServico key={servico.id} servico={servico} />
      </div>
    </div>
  )
}

/** Rotas antigas (`/scms`, `/smps`, `/stfcs`, `/seacs`): redirecionam para a aba do serviço preservando a query. */
export function RedirecionaServico({ servico }: { servico: ServicoId }) {
  const [params] = useSearchParams()
  const novo = new URLSearchParams(params)
  novo.set('servico', servico)
  return <Navigate to={`/operadoras?${novo.toString()}`} replace />
}

