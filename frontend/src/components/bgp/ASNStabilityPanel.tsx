import type { AsStability, EppdStats } from '../../types/bgpStability'
import { ClassificationBadge }    from './ClassificationBadge'
import { NoiseCategoryBadge }     from './NoiseCategoryBadge'
import { HourlyActivityChart, type WeekSeries } from './HourlyActivityChart'
import { palavra } from '../../lib/sintese'

function fmtDuration(sec: number): string {
  if (sec <= 0) return '—'
  if (sec < 60)  return `${sec}s`
  if (sec < 3600) return `${Math.floor(sec / 60)}min ${sec % 60}s`
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  return `${h}h${m > 0 ? ` ${m}min` : ''}`
}

function fmtEpppd(v: number): string {
  if (v <= 0) return '0'
  if (v < 1)  return v.toFixed(2)
  if (v < 10) return v.toFixed(1)
  return v.toFixed(0)
}

const SEVERITY_COLORS = {
  critical: { bg: 'bg-perigo-50',    border: 'border-perigo-300',    text: 'text-perigo-800',    dot: 'bg-perigo-500'    },
  high:     { bg: 'bg-alerta-50', border: 'border-alerta-300', text: 'text-alerta-800', dot: 'bg-alerta-400' },
  medium:   { bg: 'bg-aviso-50', border: 'border-aviso-300', text: 'text-aviso-800', dot: 'bg-aviso-500' },
  low:      { bg: 'bg-gray-50',   border: 'border-gray-200',   text: 'text-gray-700',   dot: 'bg-gray-400'   },
}

interface MetricCardProps {
  label:    string
  value:    string | number
  sub?:     string
}

function MetricCard({ label, value, sub }: MetricCardProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-3">
      <p className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">{label}</p>
      <p className="text-lg font-semibold text-gray-800 leading-tight">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  )
}

interface Props {
  stability:    AsStability
  eppdStats?:   EppdStats
  timestamps?:  string[]
  /** Séries horárias das últimas semanas em que este AS teve dado de hourly disponível */
  weeks?:       WeekSeries[]
}

export function ASNStabilityPanel({ stability, eppdStats, timestamps, weeks }: Props) {
  const { period: p, daily, top_prefixes, rank, classification, severity, noise_category } = stability
  const colors = SEVERITY_COLORS[severity]

  const medianRatio = eppdStats && eppdStats.median > 0
    ? p.events_per_prefix_per_day / eppdStats.median
    : null

  const showAlert = rank <= 50

  return (
    <div className="space-y-4">
      {/* Alerta de ranking */}
      {showAlert && (
        <div className={`rounded-lg border px-4 py-3 ${colors.bg} ${colors.border}`}>
          <div className="flex items-start gap-3">
            <span className={`inline-block mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${colors.dot}`} />
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-medium ${colors.text}`}>
                Este AS está entre os <strong>{rank}º mais ruidosos</strong> do universo BR
                em anúncios BGP — {fmtEpppd(p.events_per_prefix_per_day)} updates/prefixo/dia
                nos últimos 7 dias.
              </p>
              <div className="mt-1">
                <ClassificationBadge classification={classification} severity={severity} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Header da seção */}
      <div>
        <h2 className="text-base font-semibold text-gray-800">Estabilidade de anúncios BGP</h2>
        <p className="text-xs text-gray-500 mt-0.5">
          Análise dos últimos 7 dias (período {daily[0]?.date} a {daily[daily.length - 1]?.date}).
          {!showAlert && (
            <> Posição no ranking: <strong>#{rank}</strong>.</>
          )}
        </p>
      </div>

      {/* Nível de ruído */}
      <div className="flex items-center gap-2 flex-wrap">
        {noise_category && <NoiseCategoryBadge category={noise_category} />}
        {medianRatio !== null && (
          <span className="text-xs text-gray-500">
            {medianRatio >= 1
              ? <><b className="text-gray-700">{medianRatio.toFixed(1)}×</b> a mediana BR ({fmtEpppd(eppdStats!.median)} upd/pref/dia)</>
              : <>abaixo da mediana BR (<b className="text-gray-700">{fmtEpppd(eppdStats!.median)}</b> upd/pref/dia)</>
            }
          </span>
        )}
      </div>

      {/* Cards de métricas */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <MetricCard
          label="Updates/Pref/Dia"
          value={fmtEpppd(p.events_per_prefix_per_day)}
          sub={[
            stability.prefix_count_v6 > 0 ? `v6: ${fmtEpppd(p.events_per_prefix_per_day_v6)}` : null,
            stability.prefix_count_v4 > 0 ? `v4: ${fmtEpppd(p.events_per_prefix_per_day_v4)}` : null,
          ].filter(Boolean).join(' · ') || undefined}
        />
        <MetricCard
          label="Ciclos de flap"
          value={p.max_flap_cycles > 0 ? `${p.max_flap_cycles} máx.` : '0'}
          sub={p.flapping_prefixes > 0 ? `${p.flapping_prefixes} ${palavra(p.flapping_prefixes, 'prefixo instável', 'prefixos instáveis')}` : undefined}
        />
        <MetricCard
          label="Tempo médio anunciado"
          value={fmtDuration(p.mean_hold_time_sec)}
          sub="entre anúncio e retirada"
        />
        <MetricCard
          label="Pref. instáveis"
          value={`${p.flapping_prefixes} / ${stability.prefix_count_v4 + stability.prefix_count_v6}`}
          sub={[
            stability.prefix_count_v6 > 0 ? `v6: ${stability.prefix_count_v6}` : null,
            stability.prefix_count_v4 > 0 ? `v4: ${stability.prefix_count_v4}` : null,
          ].filter(Boolean).join(' · ') || undefined}
        />
      </div>

      {/* Gráfico horário (quando disponível) */}
      {(() => {
        const series = weeks?.length
          ? weeks
          : (timestamps && stability.hourly)
            ? [{ date: '', timestamps, series: stability.hourly }]
            : null
        if (!series) return null
        const rangeLabel = series.length > 1 ? ` — últimas ${series.length} semanas` : ''
        return (
          <div className="border border-gray-100 rounded-lg p-3">
            <HourlyActivityChart
              weeks={series}
              title={`Atividade horária — AS${stability.asn}${rangeLabel}`}
              tipText="Série temporal de updates BGP com resolução horária. Disponível apenas para as semanas em que este AS teve severidade média ou maior."
              height={180}
            />
          </div>
        )
      })()}

      {/* Tabela de prefixos instáveis */}
      {top_prefixes.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-600 mb-2">Prefixos mais instáveis</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="border-b border-gray-200 text-left text-gray-500">
                  <th className="py-1.5 pr-3">Prefixo</th>
                  <th className="py-1.5 pr-2">AFI</th>
                  <th className="py-1.5 pr-2 text-right">Eventos (7d)</th>
                  <th className="py-1.5 pr-2 text-right">Ciclos flap</th>
                  <th className="py-1.5 pr-2 text-right">Tempo médio up</th>
                  <th className="py-1.5 pr-2 text-right">Concentração</th>
                  <th className="py-1.5">Pico de atividade</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {top_prefixes.map(pfx => (
                  <tr key={pfx.prefix} className="hover:bg-gray-50">
                    <td className="py-1.5 pr-3 font-mono text-primario-700">{pfx.prefix}</td>
                    <td className="py-1.5 pr-2 text-gray-500">{pfx.afi.toUpperCase()}</td>
                    <td className="py-1.5 pr-2 text-right tabular-nums">{pfx.total_events.toLocaleString('pt-BR')}</td>
                    <td className="py-1.5 pr-2 text-right tabular-nums">{pfx.flap_cycles}</td>
                    <td className="py-1.5 pr-2 text-right">{fmtDuration(pfx.mean_hold_time_sec)}</td>
                    <td className="py-1.5 pr-2 text-right tabular-nums">
                      {(pfx.burst_concentration_1h * 100).toFixed(0)}%
                    </td>
                    <td className="py-1.5 text-gray-500">
                      {pfx.burst_peak_utc ? pfx.burst_peak_utc.replace('T', ' ').replace('Z', ' UTC').slice(0, 19) + ' UTC' : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
