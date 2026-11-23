import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from 'recharts'
import type { BgpStability, AsStability, NoiseCategory, BgpStabilityDeep, BgpStabilityHistoryEntry, BgpStabilityCarga } from '../../types/bgpStability'
import { ClassificationBadge } from './ClassificationBadge'
import { NoiseCategoryBadge }  from './NoiseCategoryBadge'
import { DailySparkline }      from './DailySparkline'
import { BgpActivityChart }    from './BgpActivityChart'
import { CargaBgpSemanas }     from './CargaBgpSemanas'
import { Tip } from './BgpShared'
import { VerDados } from '../ui/VerDados'
import { ThOrdenavel } from '../ui/ThOrdenavel'
import { useOrdenacao } from '../../lib/ordenacao'

function fmtEpppd(v: number): string {
  if (v === 0) return '0'
  if (v < 1)   return v.toFixed(2)
  if (v < 10)  return v.toFixed(1)
  return v.toFixed(0)
}

function EppdCell({ v, ann, wd, attrUpd, days }: {
  v: number; ann: number; wd: number; attrUpd: number; days?: number
}) {
  const color =
    v > 20 ? 'text-perigo-600 font-semibold' :
    v > 5  ? 'text-alerta-500 font-medium' :
    v > 1  ? 'text-aviso-600' :
             'text-gray-600'
  const periodLabel = days ? `em ${days} dias` : 'no período'
  const tip = ann + wd + attrUpd > 0
    ? `${ann.toLocaleString('pt-BR')} anúncios · ${wd.toLocaleString('pt-BR')} retiradas · ${attrUpd.toLocaleString('pt-BR')} attr-updates (total ${periodLabel})`
    : undefined
  return <span className={color} title={tip}>{fmtEpppd(v)}</span>
}

interface DistChartProps {
  data: BgpStability['distribution']['v4']
}

function DistributionChart({ data }: DistChartProps) {
  const chartData = data.buckets.map(b => ({
    label:     b.label,
    asn_count: b.asn_count || null,
  }))

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null
    return (
      <div className="bg-white border border-gray-200 rounded shadow-sm px-3 py-2 text-xs">
        <p className="font-medium">{label} upd/pref/dia</p>
        <p className="text-gray-600">{(payload[0].value ?? 0).toLocaleString('pt-BR')} ASes</p>
      </div>
    )
  }

  return (
    <>
<ResponsiveContainer width="100%" height={180}>
      <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="label" tick={{ fontSize: 10 }} />
        <YAxis
          scale="log"
          domain={[0.5, 'auto']}
          tick={{ fontSize: 10 }}
          width={40}
          tickFormatter={(v: number) => v >= 1000 ? `${v/1000}k` : String(Math.round(v))}
          allowDecimals={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine x={`>${data.p90 < 1 ? data.p90.toFixed(2) : data.p90}`}
          stroke="#f97316" strokeDasharray="3 3" label={{ value: 'P90', fontSize: 9, fill: '#f97316' }} />
        <Bar dataKey="asn_count" fill="#93c5fd" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
    <VerDados dados={chartData as unknown as Record<string, unknown>[]} />
</>
  )
}

// ─── Categoria de ruído ───────────────────────────────────────────────────────

const CATEGORY_ORDER: NoiseCategory[] = ['estavel', 'inquieto', 'barulhento', 'critico']

const CATEGORY_META: Record<NoiseCategory, { label: string; threshold: string }> = {
  estavel:    { label: 'Estável',    threshold: '< mediana' },
  inquieto:   { label: 'Inquieto',   threshold: 'mediana – média' },
  barulhento: { label: 'Barulhento', threshold: 'média – 100× mediana' },
  critico:    { label: 'Crítico',    threshold: '> 100× mediana' },
}

export type ContagemCategorias = Record<NoiseCategory, number> & { total: number }

/** Conta os ASes por categoria de ruído (ASes sem categoria contam como estáveis). */
export function contarCategorias(entries: AsStability[]): ContagemCategorias {
  const m = { estavel: 0, inquieto: 0, barulhento: 0, critico: 0, total: entries.length } as ContagemCategorias
  for (const e of entries) {
    const cat = e.noise_category ?? 'estavel'
    m[cat] = (m[cat] ?? 0) + 1
  }
  return m
}

interface CategoryTableProps {
  counts:   ContagemCategorias
  stats:    { median: number; mean: number; max: number }
}

function CategoryTable({ counts, stats }: CategoryTableProps) {
  const total = counts.total

  return (
    <div className="space-y-3">
      {/* Estatísticas globais */}
      <div className="flex flex-wrap gap-4 text-xs">
        <span className="text-gray-500">
          Mediana: <b className="text-gray-800">{fmtEpppd(stats.median)}</b>
        </span>
        <span className="text-gray-500">
          Média: <b className="text-gray-800">{fmtEpppd(stats.mean)}</b>
        </span>
        <span className="text-gray-500">
          Máximo: <b className="text-gray-800">{fmtEpppd(stats.max)}</b>
        </span>
        <span className="text-gray-500">
          100× mediana: <b className="text-gray-800">{fmtEpppd(stats.median * 100)}</b>
        </span>
      </div>

      {/* Tabela de categorias */}
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="border-b border-gray-200 text-left text-gray-500">
            <th className="py-1.5 pr-3">Nível</th>
            <th className="py-1.5 pr-3">Faixa (upd/pref/dia)</th>
            <th className="py-1.5 pr-2 text-right">ASes</th>
            <th className="py-1.5 text-right">%</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {CATEGORY_ORDER.map(cat => {
            const n = counts[cat]
            const pct = total > 0 ? (n / total * 100).toFixed(1) : '0.0'
            return (
              <tr key={cat} className="hover:bg-gray-50">
                <td className="py-1.5 pr-3">
                  <NoiseCategoryBadge category={cat} size="xs" />
                </td>
                <td className="py-1.5 pr-3 text-gray-500">{CATEGORY_META[cat].threshold}</td>
                <td className="py-1.5 pr-2 text-right tabular-nums font-medium text-gray-700">
                  {n.toLocaleString('pt-BR')}
                </td>
                <td className="py-1.5 text-right tabular-nums text-gray-500">{pct}%</td>
              </tr>
            )
          })}
          <tr className="border-t border-gray-200 text-gray-500">
            <td className="py-1.5 pr-3 font-medium text-gray-700" colSpan={2}>Total</td>
            <td className="py-1.5 pr-2 text-right tabular-nums font-medium text-gray-700">
              {total.toLocaleString('pt-BR')}
            </td>
            <td className="py-1.5 text-right text-gray-400">100%</td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

// ─── Linha da tabela Top 10 ───────────────────────────────────────────────────

function StabilityRow({ entry }: { entry: AsStability }) {
  const dailyTotals = entry.daily.map(d => d.total_events)
  const { period: p } = entry

  return (
    <tr className="hover:bg-gray-50">
      <td className="py-1.5 pr-2 text-gray-400">{entry.rank}</td>
      <td className="py-1.5 pr-3">
        <Link to={`/asn/${entry.asn}`} className="text-primario-600 hover:underline font-mono">
          AS{entry.asn}
        </Link>
      </td>
      <td className="py-1.5 pr-3 text-gray-700 max-w-[200px] truncate">{entry.name || '—'}</td>
      <td className="py-1.5 pr-2 text-right">
        <EppdCell
          v={p.events_per_prefix_per_day}
          ann={p.announcements}
          wd={p.withdrawals}
          attrUpd={p.attribute_updates ?? 0}
          days={7}
        />
      </td>
      <td className="py-1.5 pr-2 text-right">
        {entry.prefix_count_v6 > 0
          ? <EppdCell
              v={p.events_per_prefix_per_day_v6}
              ann={p.announcements_v6 ?? 0}
              wd={p.withdrawals_v6 ?? 0}
              attrUpd={p.attribute_updates_v6 ?? 0}
              days={7}
            />
          : <span className="text-gray-300">—</span>}
      </td>
      <td className="py-1.5 pr-2 text-right">
        {entry.prefix_count_v4 > 0
          ? <EppdCell
              v={p.events_per_prefix_per_day_v4}
              ann={p.announcements_v4 ?? 0}
              wd={p.withdrawals_v4 ?? 0}
              attrUpd={p.attribute_updates_v4 ?? 0}
              days={7}
            />
          : <span className="text-gray-300">—</span>}
      </td>
      <td className="py-1.5 pr-2">
        {entry.noise_category
          ? <NoiseCategoryBadge category={entry.noise_category} size="xs" />
          : <ClassificationBadge classification={entry.classification} severity={entry.severity} size="xs" />}
      </td>
      <td className="py-1.5 pr-3">
        <ClassificationBadge classification={entry.classification} severity={entry.severity} size="xs" />
      </td>
      <td className="py-1.5 pr-2 text-right text-gray-500">
        {p.flapping_prefixes}/{entry.prefix_count_v4 + entry.prefix_count_v6}
      </td>
      <td className="py-1.5"><DailySparkline values={dailyTotals} /></td>
    </tr>
  )
}

// ─── Ordenação da tabela ──────────────────────────────────────────────────────

type TableSortKey = 'rank' | 'epppd' | 'epppd_v6' | 'epppd_v4' | 'flap'

function sortEntries(entries: AsStability[], key: TableSortKey, desc: boolean): AsStability[] {
  const getValue = (a: AsStability): number => {
    switch (key) {
      case 'rank':    return a.rank ?? 0
      case 'epppd':   return a.period.events_per_prefix_per_day ?? 0
      case 'epppd_v6': return a.period.events_per_prefix_per_day_v6 ?? 0
      case 'epppd_v4': return a.period.events_per_prefix_per_day_v4 ?? 0
      case 'flap':    return a.period.flapping_prefixes ?? 0
    }
  }
  return [...entries].sort((a, b) => {
    const diff = getValue(a) - getValue(b)
    return desc ? -diff : diff
  })
}

function SortArrow({ active, desc }: { active: boolean; desc: boolean }) {
  if (!active) return <span className="text-gray-400 ml-0.5 text-xs">↕</span>
  return <span className="text-primario-600 ml-0.5 text-xs">{desc ? '↓' : '↑'}</span>
}

// ─── Componente principal ─────────────────────────────────────────────────────

interface Props {
  data:      BgpStability
  deepData?: BgpStabilityDeep
  history?:  BgpStabilityHistoryEntry[]
  /** ASes com mais updates nas semanas do gráfico de atividade (`/bgp-stability/carga`); sem ele a grade não aparece. */
  carga?: BgpStabilityCarga
  /** Contagem por categoria já calculada (visão geral); sem ela conta em `data.as_stability`. */
  categorias?: ContagemCategorias
  /** Quantos ASes têm severidade média ou maior, quando `data.as_stability` traz só o top (visão geral). */
  totalMedioOuMaior?: number
  /** Chamado quando o visitante pede "Ver todos" e `data.as_stability` é só o top: a página busca a lista completa. */
  onPedirTodos?: () => void
  carregandoTodos?: boolean
}

export function StabilitySection({ data, deepData, history, carga, categorias, totalMedioOuMaior, onPedirTodos, carregandoTodos }: Props) {
  const [afi, setAfi] = useState<'v4' | 'v6'>('v6')   // D6: IPv6 primeiro
  const [showAll, setShowAll] = useState(false)
  const [sortKey, setSortKey] = useState<TableSortKey>('rank')
  const [sortDesc, setSortDesc] = useState(false)
  const upstreams = useOrdenacao(deepData?.suspected_upstreams, {
    asn: { valor: (u) => u.asn, primeiro: 'asc' },
    nome: (u) => u.name || null,
    afetados: (u) => u.affected_origin_ases.length,
    eventos: (u) => u.events_attributed,
    pico: (u) => u.peak_hour_utc,
  })

  const allMed = useMemo(
    () => data.as_stability.filter(a => ['critical','high','medium'].includes(a.severity)),
    [data],
  )
  const contagem = useMemo(() => categorias ?? contarCategorias(data.as_stability), [categorias, data])
  const totalMed = totalMedioOuMaior ?? allMed.length
  const listaCompleta = totalMed <= allMed.length   // só o top: a lista completa vem sob demanda
  // A tabela recolhida mostra as 10 primeiras linhas da MESMA ordem da lista inteira (severidade média ou maior). Com a lista inteira em
  // mãos, ordena e corta; com só a visão geral, usa as `ordens` que a API calculou sobre a lista inteira. Ordenar as 10 linhas da visão
  // geral escondia quem lidera outra coluna (os mais instáveis em IPv4, por exemplo).
  const rows = useMemo(() => {
    if (showAll && listaCompleta) return sortEntries(allMed, sortKey, sortDesc)
    if (listaCompleta) {
      return sortKey === 'rank' && !sortDesc ? data.as_stability.slice(0, 10) : sortEntries(allMed, sortKey, sortDesc).slice(0, 10)
    }
    const ordem = data.ordens?.[sortKey]?.[sortDesc ? 'desc' : 'asc']
    if (ordem) {
      const porAsn = new Map([...data.as_stability, ...(data.as_stability_ordens ?? [])].map((a) => [a.asn, a]))
      return ordem.map((asn) => porAsn.get(asn)).filter((a): a is AsStability => !!a)
    }
    return sortEntries(data.as_stability.slice(0, 10), sortKey, sortDesc)   // API sem `ordens`
  }, [data, allMed, listaCompleta, showAll, sortKey, sortDesc])

  const dist = data.distribution[afi]
  const { period } = data
  const stats = data.epppd_stats

  function handleSort(key: TableSortKey) {
    if (sortKey === key) {
      setSortDesc(d => !d)
    } else {
      setSortKey(key)
      setSortDesc(true)
    }
  }

  return (
    <div className="space-y-6">
      {/* Gráfico de distribuição */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-gray-700">
            Distribuição de updates/prefixo/dia
            <Tip text="Histograma de todos os ASes BR por volume de updates BGP normalizado pelo número de prefixos anunciados. Eixo Y logarítmico — a cauda direita representa os ASes mais ruidosos." />
          </h3>
          <div className="flex text-xs rounded border border-gray-200 overflow-hidden">
            {(['v6', 'v4'] as const).map(a => (
              <button
                key={a}
                onClick={() => setAfi(a)}
                className={`px-2.5 py-1 ${afi === a ? 'bg-primario-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
              >
                IPv{a === 'v4' ? '4' : '6'}
              </button>
            ))}
          </div>
        </div>

        <DistributionChart data={dist} />

        <div className="flex gap-4 mt-2 text-xs text-gray-500">
          <span>P50: <b className="text-gray-700">{dist.p50}</b></span>
          <span>P90: <b className="text-gray-700">{dist.p90}</b></span>
          <span>P95: <b className="text-gray-700">{dist.p95}</b></span>
          <span>P99: <b className="text-gray-700">{dist.p99}</b></span>
          <span>Máx: <b className="text-gray-700">{dist.max}</b></span>
          <span className="ml-auto">{dist.asn_count_total} ASes BR com dados</span>
        </div>
        <p className="text-xs text-gray-400 mt-1">
          Baseado em {period.files_processed} arquivos de update do {period.collector},
          período {period.start} a {period.end}.{' '}
          IPv6: {(period.br_events_v6 ?? 0).toLocaleString('pt-BR')} eventos ·
          IPv4: {(period.br_events_v4 ?? 0).toLocaleString('pt-BR')} eventos.
          {period.dedup_rate_pct != null && (
            <> · {period.dedup_rate_pct}% de mensagens deduplicadas (ruído multi-peer).</>
          )}
        </p>
      </div>

      {/* Estatísticas e categorias de ruído */}
      {stats && (
        <div className="border border-gray-100 rounded-lg p-4 bg-gray-50">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            Classificação de ruído BGP
            <Tip text="Classificação de todos os ASes BR por nível de ruído, usando a mediana e a média do conjunto como limiares. 100× a mediana define o limiar crítico." />
          </h3>
          <CategoryTable counts={contagem} stats={stats} />
        </div>
      )}

      {/* Gráfico de atividade horária */}
      {(history?.length || data.hourly_global) && (
        <div className="border border-gray-100 rounded-lg p-3">
          <BgpActivityChart weeks={history?.length ? history : [{ date: '', data }]} />
        </div>
      )}

      {/* ASes com mais updates nas mesmas semanas */}
      {carga && (
        <div className="border border-gray-100 rounded-lg p-3">
          <CargaBgpSemanas data={carga} />
        </div>
      )}

      {/* Top ASes mais ruidosos */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          {showAll && listaCompleta ? `${allMed.length} ASes com severidade média ou maior` : 'Top 10 ASes mais ruidosos'}
          <Tip text="Ordenados por events/prefixo/dia no período de 7 dias (v6+v4 combinados). Clique nos cabeçalhos para ordenar. O Sparkline mostra os 7 dias — barras uniformes indicam problema crônico; barra isolada indica evento pontual." />
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="border-b border-gray-200 text-left text-gray-500">
                <th
                  className="py-1.5 pr-2 w-7 cursor-pointer hover:text-primario-600 select-none"
                  onClick={() => handleSort('rank')}
                >
                  <span className="flex items-center gap-0.5">#<SortArrow active={sortKey === 'rank'} desc={sortDesc} /></span>
                </th>
                <th className="py-1.5 pr-3">ASN</th>
                <th className="py-1.5 pr-3">Organização</th>
                <th
                  className="py-1.5 pr-2 text-right cursor-pointer hover:text-primario-600 select-none"
                  onClick={() => handleSort('epppd')}
                >
                  <span className="flex items-center justify-end gap-0.5">
                    Upd/Pref/Dia<SortArrow active={sortKey === 'epppd'} desc={sortDesc} />
                  </span>
                </th>
                <th
                  className="py-1.5 pr-2 text-right cursor-pointer hover:text-primario-600 select-none"
                  onClick={() => handleSort('epppd_v6')}
                >
                  <span className="flex items-center justify-end gap-0.5">
                    v6<SortArrow active={sortKey === 'epppd_v6'} desc={sortDesc} />
                  </span>
                </th>
                <th
                  className="py-1.5 pr-2 text-right cursor-pointer hover:text-primario-600 select-none"
                  onClick={() => handleSort('epppd_v4')}
                >
                  <span className="flex items-center justify-end gap-0.5">
                    v4<SortArrow active={sortKey === 'epppd_v4'} desc={sortDesc} />
                  </span>
                </th>
                <th className="py-1.5 pr-2">Nível</th>
                <th className="py-1.5 pr-3">Tipo</th>
                <th
                  className="py-1.5 pr-2 text-right cursor-pointer hover:text-primario-600 select-none"
                  onClick={() => handleSort('flap')}
                >
                  <span className="flex items-center justify-end gap-0.5">
                    Pref. c/flap<SortArrow active={sortKey === 'flap'} desc={sortDesc} />
                  </span>
                </th>
                <th className="py-1.5">7 dias</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map(a => (
                <StabilityRow key={a.asn} entry={a} />
              ))}
            </tbody>
          </table>
        </div>
        {!showAll && totalMed > 10 && (
          <button
            onClick={() => { setShowAll(true); if (!listaCompleta) onPedirTodos?.() }}
            className="mt-2 text-xs text-primario-600 hover:underline"
          >
            Ver todos os {totalMed.toLocaleString('pt-BR')} ASes com severidade média ou maior →
          </button>
        )}
        {showAll && !listaCompleta && (
          <p className="mt-2 text-xs text-gray-400" role="status">
            {carregandoTodos ? 'Carregando a lista completa (documento grande)…' : 'Lista completa indisponível no momento.'}
          </p>
        )}
        {showAll && (
          <button
            onClick={() => setShowAll(false)}
            className="mt-2 text-xs text-primario-600 hover:underline"
          >
            Recolher
          </button>
        )}
      </div>

      {/* Upstreams suspeitos (diagnóstico cross-AS, etapa 2) */}
      {deepData && deepData.suspected_upstreams.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Upstreams suspeitos — correlação cross-AS
            <Tip text="ASes de trânsito que aparecem como upstream dominante em múltiplos ASes ruidosos simultaneamente. Quando dois ou mais ASes flapam em sincronia e compartilham o mesmo upstream, o problema provavelmente está no provedor de trânsito." />
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="border-b border-gray-200 text-left text-gray-500">
                  <ThOrdenavel {...upstreams.props('asn')} className="py-1.5 pr-3">Upstream</ThOrdenavel>
                  <ThOrdenavel {...upstreams.props('nome')} className="py-1.5 pr-3">Organização</ThOrdenavel>
                  <ThOrdenavel {...upstreams.props('afetados')} alinhar="right" className="py-1.5 pr-2 text-right">ASes afetados</ThOrdenavel>
                  <ThOrdenavel {...upstreams.props('eventos')} alinhar="right" className="py-1.5 pr-2 text-right">Eventos atribuídos</ThOrdenavel>
                  <ThOrdenavel {...upstreams.props('pico')} className="py-1.5">Pico UTC</ThOrdenavel>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {upstreams.ordenados.map(u => (
                  <tr key={u.asn} className="hover:bg-gray-50">
                    <td className="py-1.5 pr-3">
                      <Link to={`/asn/${u.asn}`} className="font-mono text-primario-700 hover:underline">
                        AS{u.asn}
                      </Link>
                    </td>
                    <td className="py-1.5 pr-3 text-gray-600">{u.name || '—'}</td>
                    <td className="py-1.5 pr-2 text-right tabular-nums">
                      <span title={u.affected_origin_ases.map(a => `AS${a}`).join(', ')}>
                        {u.affected_origin_ases.length}
                      </span>
                    </td>
                    <td className="py-1.5 pr-2 text-right tabular-nums">
                      {u.events_attributed.toLocaleString('pt-BR')}
                    </td>
                    <td className="py-1.5 text-gray-500">
                      {u.peak_hour_utc.replace('T', ' ')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Análise dos top {deepData.top_n} ASes mais ruidosos. Gerado em {deepData.generated_at?.slice(0, 10)}.
          </p>
        </div>
      )}
    </div>
  )
}
