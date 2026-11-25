import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ScatterChart, Scatter, XAxis, YAxis, ZAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { fetchGruposSocietarios, fetchGrupoPrefixosGeo } from '../services/api'
import { useActiveDate } from '../hooks/useSnapshot'
import { AccessMunicipioMap } from '../components/acessos/AccessMunicipioMap'
import { GrupoPrefixosGeoMap } from '../components/socios/GrupoPrefixosGeoMap'
import { AsnBadge, OutorgaBadges } from '../components/OutorgaBadge'
import type { GrupoSocietarioRow, GrupoClassificacao } from '../types/api'
import { useAuth } from '../auth/AuthContext'

function fmtCnpj(c: string): string {
  const d = (c ?? '').replace(/\D/g, '')
  if (d.length !== 14) return c
  return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8,12)}-${d.slice(12)}`
}

const fmt = (n: number) => n.toLocaleString('pt-BR')
const pct = (n: number, total: number) =>
  total > 0 ? `${(100 * n / total).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}% do total` : ''

const CLASSIFICACAO_LABEL: Record<GrupoClassificacao, string> = {
  total: 'Correspondência total',
  misto: 'Misto',
  parcial: 'Correspondência parcial',
  individual: 'Empresa individual',
}
const CLASSIFICACAO_ORDER: GrupoClassificacao[] = ['total', 'misto', 'parcial', 'individual']
const CLASSIFICACAO_COLOR: Record<GrupoClassificacao, string> = {
  total: '#3b82f6',   // azul
  misto: '#f59e0b',   // âmbar
  parcial: '#9ca3af', // cinza
  individual: '#10b981', // verde
}
const CLASSIFICACAO_BADGE: Record<GrupoClassificacao, string> = {
  total: 'bg-primario-100 text-primario-700',
  misto: 'bg-aviso-100 text-aviso-700',
  parcial: 'bg-gray-100 text-gray-600',
  individual: 'bg-mercado-50 text-mercado-700',
}

// Altura compartilhada entre o scatter e o mapa — o pedido é que os dois
// preencham exatamente a mesma área visual, lado a lado.
const PANEL_HEIGHT = 400

// A tabela pode ter ~18 mil linhas (grupos + empresas individuais) — renderiza
// em páginas incrementais em vez de tudo de uma vez.
const PAGE_SIZE = 200

type Escopo = 'todos' | 'grupos' | 'individuais'
const ESCOPO_LABEL: Record<Escopo, string> = {
  todos: 'Todos',
  grupos: 'Grupos (2+ empresas)',
  individuais: 'Empresas individuais',
}

function norm(t: string): string {
  return t.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
}

/** Indicativo de atividade: usuários APNIC, assinantes SICI ou algum bloco
 *  originado na tabela BGP — basta uma das três. */
function temAtividade(g: GrupoSocietarioRow): boolean {
  return g.usuarios_apnic > 0 || g.assinantes > 0 || g.visibilidade_bgp
}

function StatCard({ label, value, hint }: { label: string; value: number; hint?: string }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 px-4 py-3">
      <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
      <div className="text-2xl font-semibold text-gray-900 tabular-nums">{fmt(value)}</div>
      {hint && <div className="text-xs text-gray-400">{hint}</div>}
    </div>
  )
}

function SimNao({ v }: { v: boolean }) {
  return v
    ? <span className="text-xs font-medium rounded px-1.5 py-0.5 bg-mercado-100 text-mercado-700">Sim</span>
    : <span className="text-xs font-medium rounded px-1.5 py-0.5 bg-gray-100 text-gray-500">Não</span>
}

function tamanhoLabel(g: GrupoSocietarioRow): string {
  return g.tamanho === 1 ? '1 empresa' : `${g.tamanho} empresas`
}

function ClassificacaoBadge({ c }: { c: GrupoClassificacao }) {
  return (
    <span className={`text-xs font-medium rounded px-1.5 py-0.5 whitespace-nowrap ${CLASSIFICACAO_BADGE[c]}`}>
      {CLASSIFICACAO_LABEL[c]}
    </span>
  )
}

/** Primeiras N empresas do grupo (já vêm ordenadas do backend, maior→menor
 *  assinantes), com indicação de quantas ficaram de fora. */
function topEmpresas(grupo: GrupoSocietarioRow, n = 3): string {
  const nomes = grupo.cnpjs.slice(0, n).map(c => c.empresa || fmtCnpj(c.cnpj))
  const resto = grupo.cnpjs.length - nomes.length
  return resto > 0 ? `${nomes.join(', ')} e mais ${resto} ${resto === 1 ? 'CNPJ' : 'CNPJs'}` : nomes.join(', ')
}

interface ScatterPoint {
  x: number
  y: number
  yReal: number
  grupo: GrupoSocietarioRow
}

function ScatterDot({
  cx, cy, fill, payload, focused,
}: {
  cx?: number
  cy?: number
  fill?: string
  payload: ScatterPoint
  focused: boolean
}) {
  if (cx == null || cy == null) return null
  return (
    <circle
      cx={cx} cy={cy}
      r={focused ? 8 : 5}
      fill={fill}
      fillOpacity={focused ? 1 : 0.65}
      stroke={focused ? '#1e3a8a' : 'none'}
      strokeWidth={focused ? 2 : 0}
      // Destaque no hover só por CSS: não passa pelo estado do React, então passar
      // o mouse não re-renderiza a página (gráfico, tabela e mapa).
      className="cursor-pointer hover:[stroke:#1e3a8a] hover:[stroke-width:2px] hover:[fill-opacity:1]"
    />
  )
}

function CnpjChips({ grupo, onSelect }: { grupo: GrupoSocietarioRow; onSelect: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const { requireLogin } = useAuth()
  const LIMIT = 6
  const shown = expanded ? grupo.cnpjs : grupo.cnpjs.slice(0, LIMIT)
  const resto = grupo.cnpjs.length - shown.length
  return (
    <div className="flex flex-wrap gap-1">
      {shown.map(c => (
        <span
          key={c.cnpj}
          className="inline-flex items-center gap-1 bg-gray-50 hover:bg-primario-50 border border-gray-200 rounded px-1.5 py-0.5"
        >
          <Link
            to={`/operadora/${c.cnpj}`}
            title={fmtCnpj(c.cnpj)}
            onClick={e => { e.stopPropagation(); onSelect() }}
            className="text-xs text-gray-600 hover:text-primario-700 whitespace-nowrap"
          >
            {c.empresa || fmtCnpj(c.cnpj)}
          </Link>
          <OutorgaBadges flags={c} />
          <AsnBadge asns={c.asns} />
        </span>
      ))}
      {resto > 0 && (
        <button
          type="button"
          onClick={e => { e.stopPropagation(); if (requireLogin('lista-expandida')) setExpanded(true) }}
          className="text-xs text-primario-600 hover:underline px-1"
        >
          +{resto} outras
        </button>
      )}
    </div>
  )
}

type SortField = 'nome' | 'classificacao' | 'tamanho' | 'assinantes' | 'usuarios_apnic' | 'visibilidade_bgp'

const colacao = new Intl.Collator('pt-BR', { numeric: true, sensitivity: 'base' })
/** O nome mostrado na coluna Grupo (a primeira empresa); é também o que a coluna ordena. */
const nomeGrupo = (g: GrupoSocietarioRow) => g.cnpjs[0]?.empresa ?? g.grupo_id

function SortHeader({
  field, label, align = 'right', sortField, sortDir, onSort,
}: {
  field: SortField
  label: string
  align?: 'left' | 'right'
  sortField: SortField
  sortDir: 'asc' | 'desc'
  onSort: (f: SortField) => void
}) {
  const active = sortField === field
  return (
    <th scope="col" aria-sort={active ? (sortDir === 'desc' ? 'descending' : 'ascending') : 'none'}
      className={`px-4 py-2 font-medium ${align === 'right' ? 'text-right' : 'text-left'}`}>
      <button type="button" onClick={() => onSort(field)} className="hover:text-gray-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario-500">
        {label}
        <span aria-hidden="true" className={`ml-0.5 inline-block ${active ? 'text-primario-600' : 'text-gray-300'}`}>
          {active ? (sortDir === 'desc' ? '↓' : '↑') : '↕'}
        </span>
      </button>
    </th>
  )
}

/**
 * "Grupos de Empresas" — visão global do cruzamento de quadro societário
 * (Receita Federal): scatter (nº empresas × assinantes, escala log, cor por
 * classificação) e mapa ficam fixos (sticky) enquanto a tabela completa dos
 * clusters rola por baixo. O mapa só muda ao CLICAR no ponto do gráfico ou na
 * linha da tabela (seleção). O hover destaca ponto/linha apenas por CSS (sem
 * estado do React): passar o mouse não re-renderiza a página nem recarrega o mapa.
 */
export function GruposPage() {
  const { requireLogin } = useAuth()
  const date = useActiveDate()
  // A seleção mora na URL (?grupo=…): dá para mandar o link do grupo; `replace` para não encher o histórico a cada clique.
  const [params, setParams] = useSearchParams()
  const selectedId = params.get('grupo')
  const setSelectedId = (id: string | null) => {
    const next = new URLSearchParams(params)
    if (id) next.set('grupo', id)
    else next.delete('grupo')
    setParams(next, { replace: true })
  }
  const [sortField, setSortField] = useState<SortField>('assinantes')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  // Escopo na URL (?escopo=todos|individuais); o padrão são só os grupos de 2+ empresas: as individuais empilhadas em x=1 escondem a dispersão.
  const escopoUrl = params.get('escopo')
  const escopo: Escopo = escopoUrl === 'todos' || escopoUrl === 'individuais' ? escopoUrl : 'grupos'
  const setEscopo = (e: Escopo) => {
    const next = new URLSearchParams(params)
    if (e === 'grupos') next.delete('escopo')
    else next.set('escopo', e)
    setParams(next, { replace: true })
  }
  const [busca, setBusca] = useState('')
  const [limite, setLimite] = useState(PAGE_SIZE)

  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortDir(d => (d === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortField(field)
      setSortDir(field === 'nome' ? 'asc' : 'desc')   // nome de A a Z; números do maior
    }
  }

  const { data, isLoading, isError } = useQuery({
    queryKey: ['grupos-societarios', date],
    queryFn: () => fetchGruposSocietarios(date ?? undefined),
    enabled: !!date,
    staleTime: 10 * 60 * 1000,
  })

  const todos = data?.grupos ?? []
  const grupos = useMemo(() => {
    if (escopo === 'todos') return todos
    const individual = escopo === 'individuais'
    return todos.filter(g => (g.classificacao === 'individual') === individual)
  }, [todos, escopo])
  // Destaque (seleção) e grupo exibido no mapa: ambos só mudam ao clicar.
  const highlightId = selectedId
  const focusedId = selectedId

  // Indicadores sobre o snapshot inteiro — independem do filtro e da busca.
  const indicadores = useMemo(() => {
    const out = { grupos: 0, empresasEmGrupos: 0, individuais: 0, gruposAtivos: 0, individuaisAtivas: 0 }
    for (const g of todos) {
      const ativo = temAtividade(g)
      if (g.classificacao === 'individual') {
        out.individuais++
        if (ativo) out.individuaisAtivas++
      } else {
        out.grupos++
        out.empresasEmGrupos += g.tamanho
        if (ativo) out.gruposAtivos++
      }
    }
    return out
  }, [todos])

  // Empresas individuais sem assinantes ficariam todas empilhadas no mesmo
  // ponto (1, 1) — ficam fora do gráfico (continuam na tabela).
  const scatterByClassificacao = useMemo(() => {
    const out: Record<GrupoClassificacao, ScatterPoint[]> = { total: [], misto: [], parcial: [], individual: [] }
    for (const g of grupos) {
      if (g.classificacao === 'individual' && g.assinantes === 0) continue
      out[g.classificacao].push({ x: g.tamanho, y: Math.max(1, g.assinantes), yReal: g.assinantes, grupo: g })
    }
    return out
  }, [grupos])

  const grupoEmFoco = useMemo(() => {
    if (focusedId) {
      const g = todos.find(g => g.grupo_id === focusedId)
      if (g) return g
    }
    if (grupos.length === 0) return null
    return grupos.reduce((max, g) => (g.assinantes > max.assinantes ? g : max), grupos[0])
  }, [focusedId, grupos, todos])

  // Fallback: só busca geo de prefixos quando o grupo em foco não tem NENHUM
  // município vindo do SICI — nunca substitui o mapa de acessos quando ele existe.
  const semSici = !!grupoEmFoco && grupoEmFoco.municipios.length === 0
  const prefixosGeoQuery = useQuery({
    queryKey: ['grupo-prefixos-geo', grupoEmFoco?.grupo_id, date],
    queryFn: () => fetchGrupoPrefixosGeo(grupoEmFoco!.grupo_id, date ?? undefined),
    enabled: semSici,
    staleTime: 10 * 60 * 1000,
  })

  const tabela = useMemo(() => {
    const classifOrdem = new Map(CLASSIFICACAO_ORDER.map((c, i) => [c, i]))
    const dir = sortDir === 'desc' ? -1 : 1
    const q = norm(busca.trim())
    const qDigits = busca.replace(/\D/g, '')
    const filtrados = q
      ? grupos.filter(g => g.cnpjs.some(c =>
          norm(c.empresa || '').includes(q)
          || (qDigits.length >= 4 && c.cnpj.includes(qDigits))
          || (c.asns ?? []).some(a => `as${a}` === q.replace(/\s/g, '') || String(a) === q)))
      : grupos
    return [...filtrados].sort((a, b) => {
      let cmp: number
      if (sortField === 'nome') {
        cmp = colacao.compare(nomeGrupo(a), nomeGrupo(b))
      } else if (sortField === 'classificacao') {
        cmp = classifOrdem.get(a.classificacao)! - classifOrdem.get(b.classificacao)!
      } else if (sortField === 'visibilidade_bgp') {
        cmp = Number(a.visibilidade_bgp) - Number(b.visibilidade_bgp)
      } else {
        cmp = (a[sortField] as number) - (b[sortField] as number)
      }
      return cmp * dir
    })
  }, [grupos, sortField, sortDir, busca])
  const tabelaVisivel = tabela.slice(0, limite)

  if (isLoading) {
    return <div className="max-w-7xl mx-auto px-4 py-6 text-sm text-gray-400">Carregando…</div>
  }
  if (isError || !data) {
    return <div className="max-w-7xl mx-auto px-4 py-6 text-sm text-perigo-500">Falha ao carregar grupos societários.</div>
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="mb-4">
        <h1 className="text-titulo-1 text-gray-900">Grupos de Empresas</h1>
        <p className="text-sm text-gray-500 mt-1">
          Cruzamento de quadro societário entre operadoras (SCM/SMP/STFC/SeAC), a partir
          dos dados abertos de CNPJ da Receita Federal. {fmt(data.total_grupos ?? data.total)} grupos
          identificados neste snapshot ({date}), além de {fmt(data.total_individuais ?? 0)} empresas
          individuais (sem sócio em comum com nenhuma outra operadora), listadas como grupos de
          uma empresa só — sem percentual de participação (a Receita não divulga isso publicamente).
        </p>
      </div>

      {/* gráfico e mapa rolam com a página (fixos no topo, sobraria pouco espaço para a tabela);
          o cabeçalho da tabela é que fica fixo. */}
      <div className="pb-4 grid md:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4 flex flex-col">
          <div className="flex items-center justify-between flex-wrap gap-x-3 gap-y-1 mb-2">
            <h2 className="text-sm font-semibold text-gray-700">
              Nº de empresas × assinantes (escala log)
            </h2>
            <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-xs text-gray-500">
              {CLASSIFICACAO_ORDER.map(c => (
                <span key={c} className="flex items-center gap-1">
                  <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: CLASSIFICACAO_COLOR[c] }} />
                  {CLASSIFICACAO_LABEL[c]}
                </span>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={PANEL_HEIGHT}>
            <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis
                type="number" dataKey="x" name="empresas" scale="log" domain={['auto', 'auto']}
                tick={{ fontSize: 11 }} label={{ value: 'Nº de empresas', position: 'insideBottom', offset: -5, fontSize: 11 }}
              />
              <YAxis
                type="number" dataKey="y" name="assinantes" scale="log" domain={['auto', 'auto']}
                tick={{ fontSize: 11 }} width={70}
                label={{ value: 'Assinantes', angle: -90, position: 'insideLeft', fontSize: 11 }}
              />
              <ZAxis range={[40, 40]} />
              <Tooltip
                cursor={{ strokeDasharray: '3 3' }}
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null
                  const p = payload[0].payload as ScatterPoint
                  return (
                    <div className="bg-white border border-gray-200 rounded shadow-lg px-2.5 py-1.5 text-xs max-w-[260px]">
                      <div className="font-semibold text-gray-800">{topEmpresas(p.grupo)}</div>
                      <div className="text-gray-500">{CLASSIFICACAO_LABEL[p.grupo.classificacao]}</div>
                      <div className="text-gray-500">{tamanhoLabel(p.grupo)} · {fmt(p.yReal)} assinantes</div>
                    </div>
                  )
                }}
              />
              {CLASSIFICACAO_ORDER.map(c => (
                <Scatter
                  key={c}
                  name={CLASSIFICACAO_LABEL[c]}
                  data={scatterByClassificacao[c]}
                  fill={CLASSIFICACAO_COLOR[c]}
                  shape={(props: unknown) => {
                    const p = props as { cx?: number; cy?: number; fill?: string; payload: ScatterPoint }
                    return <ScatterDot {...p} focused={p.payload.grupo.grupo_id === highlightId} />
                  }}
                  onClick={(p: ScatterPoint) => setSelectedId(p.grupo.grupo_id)}
                  cursor="pointer"
                />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
          {/* a alternativa em texto deste gráfico é a tabela de grupos logo abaixo (mesmos dados). */}
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4 flex flex-col">
          <div className="flex items-center justify-between flex-wrap gap-x-3 gap-y-1 mb-2">
            <h2 className="text-sm font-semibold text-gray-700">
              Distribuição municipal {grupoEmFoco ? `— ${topEmpresas(grupoEmFoco, 1)}` : ''}
            </h2>
            <span className="text-xs text-gray-400">
              {grupoEmFoco
                ? `${tamanhoLabel(grupoEmFoco)} · ${fmt(grupoEmFoco.assinantes)} assinantes`
                : 'Sem grupo em foco'}
            </span>
          </div>
          {grupoEmFoco && grupoEmFoco.municipios.length > 0 ? (
            <AccessMunicipioMap municipios={grupoEmFoco.municipios} height={PANEL_HEIGHT} />
          ) : prefixosGeoQuery.data && prefixosGeoQuery.data.features.length > 0 ? (
            <GrupoPrefixosGeoMap features={prefixosGeoQuery.data.features} height={PANEL_HEIGHT} />
          ) : (
            <div style={{ height: PANEL_HEIGHT }} className="flex items-center justify-center text-xs text-gray-400 border border-gray-100 rounded-lg">
              {prefixosGeoQuery.isFetching
                ? 'Carregando blocos IP dos ASNs…'
                : 'Sem acessos declarados ao SICI e sem blocos IP geolocalizados para este grupo.'}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-4">
        <StatCard label="Grupos" value={indicadores.grupos} hint="2 ou mais empresas" />
        <StatCard label="Empresas nos grupos" value={indicadores.empresasEmGrupos} hint="CNPJs básicos" />
        <StatCard label="Empresas individuais" value={indicadores.individuais} hint="sem relação societária" />
        <StatCard label="Grupos com atividade" value={indicadores.gruposAtivos} hint={pct(indicadores.gruposAtivos, indicadores.grupos)} />
        <StatCard label="Individuais com atividade" value={indicadores.individuaisAtivas} hint={pct(indicadores.individuaisAtivas, indicadores.individuais)} />
      </div>
      <p className="text-xs text-gray-400 mt-1.5">
        Atividade = usuários (APNIC) &gt; 0, assinantes &gt; 0 ou visibilidade BGP — basta uma das três.
      </p>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden mt-4">
        <div className="px-4 py-3 border-b border-gray-100 flex items-start justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-sm font-semibold text-gray-700">
              {ESCOPO_LABEL[escopo]} ({fmt(tabela.length)})
            </h2>
            <p className="text-xs text-gray-400">
              Clique no nome para abrir a página do grupo, com indicadores técnicos e de mercado. Clique num cabeçalho para ordenar;
              clique na linha ou use "Ver no mapa" (Enter ou Espaço) para mostrá-la no mapa e no gráfico acima.
            </p>
            {/* anuncia a seleção feita pelo botão ou pelo clique (o mapa e o gráfico mudam fora do foco) */}
            <p className="sr-only" aria-live="polite" data-testid="grupo-selecionado">
              {(() => { const g = selectedId ? todos.find(x => x.grupo_id === selectedId) : null; return g ? `Grupo selecionado: ${nomeGrupo(g)}, ${g.tamanho} empresa${g.tamanho === 1 ? '' : 's'}` : '' })()}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <label className="flex items-center gap-1 text-xs text-gray-600">
              Buscar
              <input
                type="search"
                value={busca}
                onChange={e => { setBusca(e.target.value); setLimite(PAGE_SIZE) }}
                placeholder="Empresa, CNPJ ou ASN"
                className="text-xs border border-gray-200 rounded px-2 py-1 w-48"
              />
            </label>
            <div role="group" aria-label="Escopo da tabela" className="inline-flex rounded border border-gray-200 overflow-hidden text-xs">
              {(Object.keys(ESCOPO_LABEL) as Escopo[]).map(e => (
                <button
                  key={e}
                  type="button"
                  onClick={() => { setEscopo(e); setLimite(PAGE_SIZE) }}
                  aria-pressed={escopo === e}
                  className={`px-2 py-1 ${escopo === e ? 'bg-primario-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
                >
                  {ESCOPO_LABEL[e]}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="overflow-x-auto lg:overflow-x-clip">
          <table className="w-full text-sm" aria-label="Grupos econômicos">
            <thead className="bg-gray-50 text-xs text-gray-600 lg:sticky lg:top-[var(--altura-topo,89px)] z-10 shadow-sm">
              <tr>
                <SortHeader field="nome" label="Grupo" align="left" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                <SortHeader field="classificacao" label="Classificação" align="left" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                <SortHeader field="tamanho" label="Empresas" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                <SortHeader field="assinantes" label="Assinantes" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                <SortHeader field="usuarios_apnic" label="Usuários (APNIC)" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                <SortHeader field="visibilidade_bgp" label="Visibilidade BGP" align="left" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                <th scope="col" className="text-left px-4 py-2 font-medium">CNPJs</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tabelaVisivel.map(g => {
                const isSelected = selectedId === g.grupo_id
                return (
                  <tr
                    key={g.grupo_id}
                    onClick={() => setSelectedId(g.grupo_id)}
                    className={`align-top cursor-pointer transition-colors ${
                      isSelected ? 'bg-primario-50/60 ring-1 ring-inset ring-primario-300' : 'hover:bg-primario-50'
                    }`}
                  >
                    <td className="px-4 py-2.5 min-w-[12rem]">
                      <Link to={`/grupo/${encodeURIComponent(g.grupo_id)}`} onClick={e => e.stopPropagation()} className="font-medium text-primario-700 hover:underline">
                        {nomeGrupo(g)}
                      </Link>
                      {/* GRUPO-E7: `tamanho` conta empresas (raízes de CNPJ); `cnpjs` traz matriz e filiais */}
                      {g.tamanho > 1 && <span className="ml-1 text-xs text-gray-500">e mais {g.tamanho - 1} {g.tamanho - 1 === 1 ? 'empresa' : 'empresas'}</span>}
                      {/* O clique na linha não chega ao teclado: este botão faz a mesma seleção (WCAG 2.1.1). */}
                      <button type="button" aria-pressed={isSelected} onClick={e => { e.stopPropagation(); setSelectedId(g.grupo_id) }}
                        className="ml-2 inline-flex min-h-6 items-center text-xs text-primario-700 underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario-500">
                        Ver no mapa<span className="sr-only">: {nomeGrupo(g)}</span>
                      </button>
                    </td>
                    <td className="px-4 py-2.5 whitespace-nowrap"><ClassificacaoBadge c={g.classificacao} /></td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-gray-700">{g.tamanho}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-gray-700">{fmt(g.assinantes)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-gray-700">{fmt(g.usuarios_apnic)}</td>
                    <td className="px-4 py-2.5"><SimNao v={g.visibilidade_bgp} /></td>
                    <td className="px-4 py-2.5"><CnpjChips grupo={g} onSelect={() => setSelectedId(g.grupo_id)} /></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        {tabela.length > tabelaVisivel.length && (
          <div className="px-4 py-3 border-t border-gray-100 text-center">
            <button
              type="button"
              onClick={() => { if (requireLogin('lista-expandida')) setLimite(l => l + PAGE_SIZE * 5) }}
              className="text-xs text-primario-600 hover:underline"
            >
              Mostrar mais ({fmt(tabela.length - tabelaVisivel.length)} restantes)
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
