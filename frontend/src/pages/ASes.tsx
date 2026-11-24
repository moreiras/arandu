import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchASNs } from '../services/api'
import { useActiveDate } from '../hooks/useSnapshot'
import { OutorgaBadges } from '../components/OutorgaBadge'
import type { ASNIndexEntry } from '../types/api'
type StabilitySummary = { epppd: number | null; epppd_v4: number | null; epppd_v6: number | null }
import { useAuth } from '../auth/AuthContext'
import { PREVIEW_LIMIT } from '../auth/accessPolicy'
import { Dica } from '../components/ui/Dica'
import { EstadoDados } from '../components/ui/EstadoDados'
import { OrganizacoesVariosAsns } from '../components/stats/OrganizacoesVariosAsns'

// ─── Column definitions ───────────────────────────────────────────────────────

type SortField =
  | 'asn' | 'name' | 'cnpj'
  | 'apnic_users' | 'apnic_v6_users' | 'pct_v6'
  | 'ixps_direct_count'
  | 'ixps_origin_v4_count' | 'ixps_origin_v6_count'
  | 'has_rpki' | 'has_aspa' | 'pdb_registered' | 'has_scm' | 'external_ixps_count'
  | 'bgp_stability' | 'prontidao_indice'

type ColKey = SortField | 'cnpj'

interface ColDef {
  key: ColKey
  label: string
  tooltip: string
  align: 'left' | 'right' | 'center'
  /** Tailwind width class for table-fixed layout; omit for the flexible (Nome) column */
  w?: string
  /** Default true; CNPJ não é ordenável */
  sortable?: boolean
}

const COLS: ColDef[] = [
  {
    key: 'asn',
    label: 'ASN',
    tooltip: 'Número do Sistema Autônomo (Autonomous System Number)',
    align: 'left',
    w: 'w-[60px]',
  },
  {
    key: 'name',
    label: 'Nome',
    tooltip: 'Nome da organização registrada no Registro.br',
    align: 'left',
    // flexible — takes remaining space
  },
  {
    key: 'cnpj',
    label: 'CNPJ',
    tooltip: 'CNPJ da organização do AS conforme o Registro.br',
    align: 'left',
    w: 'w-[148px]',  // 18 caracteres em fonte mono (~130 px) + padding: com 124 px o link transbordava para a coluna seguinte
  },
  {
    key: 'apnic_users',
    label: 'Usuários',
    tooltip: 'Estimativa APNIC de usuários totais da rede (janela de 60 dias, baseada em medições ativas)',
    align: 'right',
    w: 'w-[68px]',
  },
  {
    key: 'apnic_v6_users',
    label: 'Usu. v6',
    tooltip: 'Estimativa APNIC de usuários que utilizam IPv6 neste AS (janela de 60 dias)',
    align: 'right',
    w: 'w-[62px]',
  },
  {
    key: 'pct_v6',
    label: '%IPv6',
    tooltip: 'Percentual de usuários com IPv6 = Usu. v6 ÷ Usuários totais × 100 (fonte: APNIC, janela 60 dias). Verde ≥70% · Amarelo 50–70% · Vermelho 20–50% · Cinza 10–20%',
    align: 'right',
    w: 'w-[54px]',
  },
  {
    key: 'ixps_direct_count',
    label: 'Dir. IX.br',
    tooltip: 'Número de PTTs do IX.br em que este AS tem sessão BGP com o route server e anuncia rotas por ele (primeiro AS do caminho nas rotas coletadas). Sessões bilaterais não são observáveis aqui, e membro sem sessão no route server não conta.',
    align: 'right',
    w: 'w-[58px]',
  },
  {
    key: 'ixps_origin_v6_count',
    label: 'Orig. v6',
    tooltip: 'Número de IXPs do IX.br onde este AS origina prefixos IPv6 (aparece como AS de origem em pelo menos um anúncio)',
    align: 'right',
    w: 'w-[54px]',
  },
  {
    key: 'ixps_origin_v4_count',
    label: 'Orig. v4',
    tooltip: 'Número de IXPs do IX.br onde este AS origina prefixos IPv4 (aparece como AS de origem em pelo menos um anúncio)',
    align: 'right',
    w: 'w-[54px]',
  },
  {
    key: 'has_rpki',
    label: 'RPKI',
    tooltip: 'Indica se o AS possui ao menos um ROA (Route Origin Authorization) publicado no RPKI. ROAs permitem validar a legitimidade dos anúncios BGP.',
    align: 'center',
    w: 'w-[48px]',
  },
  {
    key: 'has_aspa',
    label: 'ASPA',
    tooltip: 'Indica se o AS publicou ao menos um objeto ASPA (Autonomous System Provider Authorization) no RPKI. O ASPA declara os upstreams autorizados do AS.',
    align: 'center',
    w: 'w-[48px]',
  },
  {
    key: 'pdb_registered',
    label: 'PeeringDB',
    tooltip: 'Indica se o AS possui cadastro no PeeringDB. Se sim, clique para acessar o perfil.',
    align: 'center',
    w: 'w-[66px]',
  },
  {
    key: 'has_scm',
    label: 'Outorgas',
    tooltip: 'Outorgas Anatel (SCM/SMP/STFC/SeAC) do CNPJ deste AS, por cruzamento de CNPJ. Ordena por SCM.',
    align: 'center',
    w: 'w-[92px]',
  },
  {
    key: 'external_ixps_count',
    label: 'IXPs ext.',
    tooltip: 'Número de outros IXPs (fora do IX.br) onde o AS é membro registrado, conforme dados do PeeringDB',
    align: 'right',
    w: 'w-[58px]',
  },
  {
    key: 'bgp_stability',
    label: 'Upd/Pref/Dia',
    tooltip: 'Updates BGP por prefixo por dia (média dos últimos 7 dias, v6+v4). Indica "ruído" BGP — valores altos podem indicar link instável, sessão oscilante ou configuração incorreta. Vermelho >20 · Laranja 5–20 · Amarelo 1–5.',
    align: 'right',
    w: 'w-[70px]',
  },
]

/** Coluna opcional: a API só devolve o índice quando a lista nominal de prontidão está liberada (aprovação da metodologia). */
const COL_PRONTIDAO: ColDef = {
  key: 'prontidao_indice',
  label: 'Prontidão',
  tooltip: 'Índice de prontidão em segurança de roteamento (0 a 100): soma ponderada de medições de terceiros (ROV, anti-spoofing, IRR/PeeringDB, ROA). Não é veredito sobre a empresa; dado parcial em alguns pilares. Abra o AS para ver os pilares.',
  align: 'right',
  w: 'w-[68px]',
}

const CLASSE_PRONTIDAO: Record<string, string> = {
  pronto: 'bg-ok-100 text-ok-700',
  em_progresso: 'bg-aviso-100 text-aviso-700',
  atrasado: 'bg-perigo-100 text-perigo-700',
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmtN(n: number | null | undefined): string {
  if (n == null) return '—'
  return n.toLocaleString('pt-BR')
}

function fmtCnpj(c: string | null | undefined): string {
  const d = (c ?? '').replace(/\D/g, '')
  if (d.length !== 14) return c || '—'
  return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8,12)}-${d.slice(12)}`
}

function v6PctClass(pct: number): string {
  if (pct >= 70) return 'text-ok-700 font-semibold'
  if (pct >= 50) return 'text-aviso-600 font-semibold'
  if (pct >= 20) return 'text-perigo-600'
  if (pct >= 10) return 'text-gray-500'
  return 'text-gray-400'
}

function SortArrow({ active, desc }: { active: boolean; desc: boolean }) {
  if (!active) return <span className="text-gray-400 ml-0.5">↕</span>
  return <span className="text-primario-600 ml-0.5">{desc ? '↓' : '↑'}</span>
}

// ─── Search bar ──────────────────────────────────────────────────────────────

function ASNSearch({ date, onNavigate }: { date: string | null; onNavigate: () => void }) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const wrapRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  const { data, isFetching } = useQuery({
    queryKey: ['asn-search-ases', query, date],
    queryFn: () => fetchASNs({ q: query, limit: 8, date: date ?? undefined }),
    enabled: query.trim().length >= 2,
    staleTime: 30_000,
    placeholderData: (prev) => prev,
  })

  const results = data?.items ?? []

  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [])

  function select(asn: number) {
    navigate(`/asn/${asn}`)
    onNavigate()
    setOpen(false)
    setQuery('')
  }

  return (
    <div ref={wrapRef} className="relative w-full max-w-md">
      <input
        type="text"
        value={query}
        onChange={(e) => { setQuery(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)}
        placeholder="Buscar por número ou nome (ex: 26599, Claro…)"
        className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primario-500 focus:border-transparent transition"
        autoComplete="off"
        spellCheck={false}
      />
      {open && query.trim().length >= 2 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 overflow-hidden">
          {isFetching && results.length === 0 ? (
            <div className="px-3 py-3 text-sm text-gray-400">Buscando…</div>
          ) : results.length === 0 ? (
            <div className="px-3 py-3 text-sm text-gray-400">Nenhum AS encontrado.</div>
          ) : (
            <ul>
              {results.map((item) => (
                <li key={item.asn}>
                  <button
                    className="w-full text-left px-3 py-2.5 hover:bg-primario-50 flex items-center gap-2 border-b border-gray-100 last:border-0"
                    onClick={() => select(item.asn)}
                  >
                    <span className="font-mono text-primario-700 text-xs w-16 flex-shrink-0">AS{item.asn}</span>
                    <span className="text-sm text-gray-800 truncate flex-1">{item.name}</span>
                    {item.is_br && (
                      <span className="text-xs text-gray-400 flex-shrink-0 bg-gray-100 px-1.5 py-0.5 rounded">BR</span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Table row ───────────────────────────────────────────────────────────────

function eppdColor(v: number): string {
  if (v > 20) return 'text-perigo-600 font-semibold'
  if (v > 5)  return 'text-alerta-500 font-medium'
  if (v > 1)  return 'text-aviso-600'
  return 'text-gray-500'
}

function ASRow({ entry, stability, comProntidao }: { entry: ASNIndexEntry; stability?: StabilitySummary; comProntidao?: boolean }) {
  const pct = entry.pct_v6 ?? null
  const epppd = stability?.epppd ?? null

  return (
    <tr className="hover:bg-tecnico-100 transition-colors text-xs">
      <td className="px-2 py-1.5 font-mono text-primario-700 whitespace-nowrap">
        <Link to={`/asn/${entry.asn}`} className="hover:underline">
          AS{entry.asn}
        </Link>
      </td>
      <td className="px-2 py-1.5 text-gray-800 truncate overflow-hidden" title={entry.name}>
        {/* block + truncate: o link tem a largura da célula; inline, ele passava por baixo da coluna CNPJ (alvo coberto, NBR 5.8.7) */}
        <Link to={`/asn/${entry.asn}`} className="block truncate hover:underline">
          {entry.name || '—'}
        </Link>
      </td>
      <td className="px-2 py-1.5 font-mono text-gray-500 whitespace-nowrap" title={fmtCnpj(entry.cnpj)}>
        {entry.cnpj
          ? <Link to={`/operadora/${entry.cnpj}`} className="hover:text-primario-600 hover:underline">
              {fmtCnpj(entry.cnpj)}
            </Link>
          : <span className="text-gray-300">—</span>}
      </td>
      <td className="px-2 py-1.5 text-right tabular-nums text-gray-700">
        {fmtN(entry.apnic_users)}
      </td>
      <td className="px-2 py-1.5 text-right tabular-nums text-gray-700">
        {fmtN(entry.apnic_v6_users)}
      </td>
      <td className="px-2 py-1.5 text-right tabular-nums">
        {pct == null ? (
          <span className="text-gray-400">—</span>
        ) : (
          <span className={v6PctClass(pct)}>
            {pct.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%
          </span>
        )}
      </td>
      <td className="px-2 py-1.5 text-right tabular-nums">
        {entry.ixps_direct_count > 0 ? (
          <span className="text-primario-700 font-medium">{entry.ixps_direct_count}</span>
        ) : (
          <span className="text-gray-400">—</span>
        )}
      </td>
      <td className="px-2 py-1.5 text-right tabular-nums">
        {(entry.ixps_origin_v6_count ?? 0) > 0 ? (
          <span className="text-v6-700 font-medium">{entry.ixps_origin_v6_count}</span>
        ) : (
          <span className="text-gray-400">—</span>
        )}
      </td>
      <td className="px-2 py-1.5 text-right tabular-nums">
        {(entry.ixps_origin_v4_count ?? 0) > 0 ? (
          <span className="text-ok-700 font-medium">{entry.ixps_origin_v4_count}</span>
        ) : (
          <span className="text-gray-400">—</span>
        )}
      </td>
      <td className="px-2 py-1.5 text-center">
        {entry.has_rpki == null ? (
          <span className="text-gray-400 text-xs">—</span>
        ) : entry.has_rpki ? (
          <span className="inline-block px-1.5 py-0.5 rounded text-xs font-semibold bg-ok-100 text-ok-700">sim</span>
        ) : (
          <span className="inline-block px-1.5 py-0.5 rounded text-xs bg-gray-100 text-gray-400">não</span>
        )}
      </td>
      <td className="px-2 py-1.5 text-center">
        {entry.has_aspa == null ? (
          <span className="text-gray-400 text-xs">—</span>
        ) : entry.has_aspa ? (
          <span className="inline-block px-1.5 py-0.5 rounded text-xs font-semibold bg-primario-100 text-primario-700">sim</span>
        ) : (
          <span className="inline-block px-1.5 py-0.5 rounded text-xs bg-gray-100 text-gray-400">não</span>
        )}
      </td>
      <td className="px-2 py-1.5 text-center">
        {entry.pdb_registered == null ? (
          <span className="text-gray-400 text-xs">—</span>
        ) : entry.pdb_registered ? (
          <a
            href={`https://www.peeringdb.com/asn/${entry.asn}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block px-1.5 py-0.5 rounded text-xs font-semibold bg-tecnico-100 text-tecnico-700 hover:bg-tecnico-200 transition-colors"
            onClick={e => e.stopPropagation()}
          >
            sim ↗
          </a>
        ) : (
          <span className="inline-block px-1.5 py-0.5 rounded text-xs bg-gray-100 text-gray-400">não</span>
        )}
      </td>
      <td className="px-2 py-1.5 text-center">
        {entry.has_scm || entry.has_smp || entry.has_stfc || entry.has_seac ? (
          <OutorgaBadges flags={entry} />
        ) : (
          <span className="text-gray-400 text-xs">—</span>
        )}
      </td>
      <td className="px-2 py-1.5 text-right tabular-nums">
        {(entry.external_ixps_count ?? 0) > 0 ? (
          <span className="text-aviso-700 font-medium">{entry.external_ixps_count}</span>
        ) : (
          <span className="text-gray-400">—</span>
        )}
      </td>
      <td className="px-2 py-1.5 text-right tabular-nums">
        {epppd == null ? (
          <span className="text-gray-300">—</span>
        ) : (
          <span
            className={eppdColor(epppd)}
            title={stability ? `v6: ${stability.epppd_v6} · v4: ${stability.epppd_v4}` : undefined}
          >
            {epppd < 1 ? epppd.toFixed(2) : epppd < 10 ? epppd.toFixed(1) : epppd.toFixed(0)}
          </span>
        )}
      </td>
      {comProntidao && (
        <td className="px-2 py-1.5 text-right tabular-nums">
          {entry.prontidao_indice == null ? (
            <span className="text-gray-300">—</span>
          ) : (
            <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-semibold ${CLASSE_PRONTIDAO[entry.prontidao_classe ?? ''] ?? 'bg-gray-100 text-gray-500'}`} title={entry.prontidao_classe?.replace('_', ' ')}>
              {entry.prontidao_indice.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
            </span>
          )}
        </td>
      )}
    </tr>
  )
}

// ─── Main page ───────────────────────────────────────────────────────────────

/** Colunas cujo primeiro clique ordena em ordem crescente. */
const CRESCENTE_PRIMEIRO = new Set<SortField>(['asn', 'name', 'cnpj'])

export function ASes() {
  const date = useActiveDate()
  const secao = useSearchParams()[0].get('secao')
  const [page, setPage] = useState(1)
  // 100 linhas por página, com seletor para quem está logado (acima de 100 exige login).
  const [tamanho, setTamanho] = useState(100)
  const { user, requireLogin } = useAuth()
  const [sortBy, setSortBy] = useState<SortField>('apnic_users')
  const [sortDesc, setSortDesc] = useState(true)

  function handleSort(field: SortField) {
    if (sortBy === field) {
      setSortDesc((d) => !d)
    } else {
      setSortBy(field)
      // identificador e texto começam em ordem crescente (A→Z); métricas, da maior para a menor
      setSortDesc(!CRESCENTE_PRIMEIRO.has(field))
    }
    setPage(1)
  }

  const { data, isLoading, isFetching, isError, error } = useQuery({
    queryKey: ['ases-table', date, page, sortBy, sortDesc, !!user, tamanho],
    queryFn: () =>
      fetchASNs({
        date: date ?? undefined,
        br_only: true,
        page,
        // Anônimo recebe só a prévia (1ª página); a lista completa exige login.
        limit: user ? tamanho : PREVIEW_LIMIT,
        // Estabilidade BGP junto da lista: a página deixa de baixar o resumo de todos os ASes e ordena no servidor
        sort_by: sortBy === 'bgp_stability' ? 'epppd' : sortBy,
        sort_desc: sortDesc,
        include: 'bgp_stability,prontidao',
      }),
    staleTime: 60_000,
    placeholderData: (prev) => prev,
  })

  const items = data?.items ?? []
  const comProntidao = items.some((i) => i.prontidao_classe != null)
  const cols = comProntidao ? [...COLS, COL_PRONTIDAO] : COLS
  const total = data?.total ?? 0
  const pages = data?.pages ?? 0

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-baseline gap-3 flex-wrap">
        <h1 className="text-titulo-1 text-gray-900">ASes Brasileiros</h1>
        {total > 0 && (
          <span className="text-sm text-gray-500">
            {total.toLocaleString('pt-BR')} ASNs
          </span>
        )}
      </div>

      {/* Search */}
      <ASNSearch date={date} onNavigate={() => {}} />

      {/* Table */}
      <div className="relative">
        {isFetching && !isLoading && (
          <div role="status" className="absolute top-0 right-0 text-xs text-gray-500 py-1 px-2">atualizando…</div>
        )}

        <div className="overflow-x-auto lg:overflow-x-clip rounded-lg border border-gray-200 bg-white">
          <table className="w-full table-fixed text-xs min-w-[1150px]">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                {cols.map((col) => {
                  const sortable = col.sortable !== false
                  return (
                    <th
                      key={col.key}
                      aria-sort={sortBy === col.key ? (sortDesc ? 'descending' : 'ascending') : 'none'}
                      className={`lg:sticky lg:top-[var(--altura-topo,89px)] z-10 px-1.5 py-1.5 font-medium select-none leading-tight align-bottom transition-colors border-b border-gray-200 bg-gray-50 ${col.w ?? ''} ${
                        col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'
                      } ${sortable ? 'cursor-pointer' : ''} ${
                        sortBy === col.key ? 'text-primario-700 bg-primario-50' : `text-gray-500 ${sortable ? 'hover:bg-gray-100' : ''}`
                      }`}
                    >
                      <span className="inline-flex flex-wrap items-center">
                        {sortable ? (
                          <button type="button" className="min-h-6 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario-500" onClick={() => handleSort(col.key as SortField)}>
                            {col.label}<SortArrow active={sortBy === col.key} desc={sortDesc} />
                          </button>
                        ) : col.label}
                        <Dica texto={col.tooltip} rotulo={col.label} />
                      </span>
                    </th>
                  )
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {isLoading ? (
                Array.from({ length: 20 }).map((_, i) => (
                  <tr key={i}>
                    {cols.map((c) => (
                      <td key={c.key} className="px-2 py-1.5">
                        <div className="h-3 bg-gray-100 rounded animate-pulse" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : isError ? (
                <tr>
                  <td colSpan={cols.length} className="px-4 py-8 text-sm">
                    <EstadoDados erro={error} oQue="a lista de ASes" mensagem="A lista de ASes não está publicada neste snapshot." />
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={cols.length} className="px-4 py-8 text-center text-gray-400">
                    Nenhum AS encontrado.
                  </td>
                </tr>
              ) : (
                items.map((entry) => (
                  <ASRow key={entry.asn} comProntidao={comProntidao} entry={entry} stability={{ epppd: entry.epppd ?? null, epppd_v4: entry.epppd_v4 ?? null, epppd_v6: entry.epppd_v6 ?? null }} />
                ))
              )}
            </tbody>
          </table>
        </div>

        {!user && total > PREVIEW_LIMIT && (
          <p className="mt-3 text-xs text-gray-500">
            Prévia: {PREVIEW_LIMIT} maiores de {total.toLocaleString('pt-BR')} ASNs BR.{' '}
            <button className="text-primario-600 hover:underline" onClick={() => requireLogin('lista-expandida')}>
              Entre para ver a lista completa.
            </button>
          </p>
        )}

        {/* Pagination */}
        {pages > 1 && (
          <div className="flex items-center justify-between mt-3 text-sm">
            <span className="text-gray-500 text-xs flex flex-wrap items-center gap-2">
              Página {page} de {pages} · {total.toLocaleString('pt-BR')} ASNs BR
              {user && (
                <label className="flex items-center gap-1">
                  Linhas por página
                  <select className="min-h-8 rounded border border-gray-300 bg-white px-1" value={tamanho} onChange={(e) => { setTamanho(Number(e.target.value)); setPage(1) }}>
                    {[50, 100, 250, 500, 1000].map((n) => <option key={n} value={n}>{n}</option>)}
                  </select>
                </label>
              )}
            </span>
            <div className="flex flex-wrap gap-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 rounded border border-gray-300 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                ← Anterior
              </button>
              {Array.from({ length: Math.min(pages, 7) }, (_, i) => {
                const p = pages <= 7 ? i + 1 : page <= 4 ? i + 1 : page >= pages - 3 ? pages - 6 + i : page - 3 + i
                return (
                  <button
                    key={p}
                    onClick={() => { if (p > 1 && !requireLogin('lista-expandida')) return; setPage(p) }}
                    className={`px-2.5 py-1 rounded border text-xs ${
                      p === page
                        ? 'bg-primario-600 border-primario-600 text-white font-medium'
                        : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    {p}{!user && p > 1 && <span aria-hidden="true"> 🔒</span>}
                    {!user && p > 1 && <span className="sr-only"> (exige login)</span>}
                  </button>
                )
              })}
              <button
                onClick={() => { if (!requireLogin('lista-expandida')) return; setPage((p) => Math.min(pages, p + 1)) }}
                disabled={page === pages}
                className="px-3 py-1 rounded border border-gray-300 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Próxima →
              </button>
            </div>
          </div>
        )}
      </div>

      <OrganizacoesVariosAsns date={date ?? undefined} ancorar={secao === 'organizacoes'} />
    </div>
  )
}
