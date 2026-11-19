import { useMemo } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine,
} from 'recharts'
import type { HourlySeries } from '../../types/bgpStability'
import { Tip } from './BgpShared'
import { VerDados } from '../ui/VerDados'

export interface WeekSeries {
  /** Data do snapshot que gerou esta semana (usada como marcador de início de semana) */
  date:       string
  timestamps: string[]
  series:     HourlySeries
}

interface ChartPoint {
  x:         string
  fullLabel: string
  weekTick?: string
  isGap?:    boolean
  ann:       number | null
  wd:        number | null
  attr_upd:  number | null
}

const DAYS_PT = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']
const DAY_MS  = 86_400_000

/** Insere um "buraco" (pontos nulos) entre duas semanas quando a distância
 * entre suas datas de snapshot é maior que ~1 semana, indicando que há
 * snapshots semanais faltando entre elas. */
function gapPointsBetween(prevDate: string, curDate: string, wi: number): ChartPoint[] {
  const diffDays = (new Date(curDate).getTime() - new Date(prevDate).getTime()) / DAY_MS
  const missingWeeks = Math.round(diffDays / 7) - 1
  if (missingWeeks < 1) return []
  const gapCount = Math.min(missingWeeks, 4)
  return Array.from({ length: gapCount }, (_, gi) => ({
    x:         `gap-${wi}-${gi}`,
    fullLabel: 'Sem dados (snapshot ausente)',
    isGap:     true,
    ann:       null,
    wd:        null,
    attr_upd:  null,
  }))
}

export function buildWeeklyPoints(weeks: WeekSeries[]): ChartPoint[] {
  const points: ChartPoint[] = []
  let prevDate: string | null = null
  weeks.forEach((week, wi) => {
    if (prevDate && week.date) {
      points.push(...gapPointsBetween(prevDate, week.date, wi))
    }
    if (week.date) prevDate = week.date

    week.timestamps.forEach((iso, i) => {
      const dt  = new Date(iso)
      const dow = DAYS_PT[dt.getUTCDay()]
      const hh  = String(dt.getUTCHours()).padStart(2, '0')
      const dd  = String(dt.getUTCDate()).padStart(2, '0')
      const mm  = String(dt.getUTCMonth() + 1).padStart(2, '0')
      points.push({
        x:         `${wi}-${i}`,
        fullLabel: `${dow} ${dd}/${mm} ${hh}h`,
        weekTick:  i === 0 ? `${dd}/${mm}` : undefined,
        ann:      week.series.ann[i]      ?? 0,
        wd:       week.series.wd[i]       ?? 0,
        attr_upd: week.series.attr_upd[i] ?? 0,
      })
    })
  })
  return points
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null
  const point = payload[0]?.payload as ChartPoint | undefined
  if (point?.isGap) {
    return (
      <div className="bg-white border border-gray-200 rounded shadow-sm px-3 py-2 text-xs min-w-[160px]">
        <p className="text-gray-500">{point.fullLabel}</p>
      </div>
    )
  }
  const ann      = payload.find((p: any) => p.dataKey === 'ann')?.value      ?? 0
  const wd       = payload.find((p: any) => p.dataKey === 'wd')?.value       ?? 0
  const attr_upd = payload.find((p: any) => p.dataKey === 'attr_upd')?.value ?? 0
  return (
    <div className="bg-white border border-gray-200 rounded shadow-sm px-3 py-2 text-xs space-y-0.5 min-w-[160px]">
      <p className="font-medium text-gray-700 mb-1">{point?.fullLabel}</p>
      <p className="text-primario-600">▲ Anúncios: {ann.toLocaleString('pt-BR')}</p>
      <p className="text-perigo-500">▼ Retiradas: {wd.toLocaleString('pt-BR')}</p>
      <p className="text-alerta-400">~ Attr-updates: {attr_upd.toLocaleString('pt-BR')}</p>
      <p className="text-gray-500 border-t border-gray-100 pt-0.5 mt-0.5">
        Total: {(ann + wd + attr_upd).toLocaleString('pt-BR')}
      </p>
    </div>
  )
}

interface Props {
  weeks:    WeekSeries[]
  title:    string
  tipText?: string
  height?:  number
}

export function HourlyActivityChart({ weeks, title, tipText, height = 220 }: Props) {
  const points = useMemo(() => buildWeeklyPoints(weeks), [weeks])

  const weekTicks = useMemo(
    () => points.filter(p => p.weekTick).map(p => p.x),
    [points],
  )

  const xTickFormatter = (x: string) => {
    const p = points.find(pt => pt.x === x)
    return p?.weekTick ?? ''
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-gray-700">
        {title}
        {tipText && <Tip text={tipText} />}
      </h3>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={points} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="hac-gradAnn" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="hac-gradWd" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#ef4444" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="hac-gradAttr" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#f97316" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#f97316" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="x"
            tick={{ fontSize: 10, fill: '#9ca3af' }}
            tickFormatter={xTickFormatter}
            interval={0}
          />
          <YAxis
            tick={{ fontSize: 10 }}
            width={44}
            tickFormatter={(v: number) =>
              v >= 1_000_000 ? `${(v / 1_000_000).toFixed(1)}M` :
              v >= 1_000     ? `${(v / 1_000).toFixed(0)}k`     : String(v)
            }
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            iconType="square"
            iconSize={8}
            wrapperStyle={{ fontSize: 11 }}
            formatter={(value) =>
              value === 'ann' ? 'Anúncios' : value === 'wd' ? 'Retiradas' : 'Attr-updates'
            }
          />
          {weeks.length > 1 && weekTicks.slice(1).map(x => (
            <ReferenceLine key={x} x={x} stroke="#e5e7eb" strokeDasharray="2 2" />
          ))}
          <Area type="monotone" dataKey="ann"      stackId="1" stroke="#3b82f6" strokeWidth={1.2} fill="url(#hac-gradAnn)"  dot={false} activeDot={false} connectNulls={false} />
          <Area type="monotone" dataKey="wd"       stackId="1" stroke="#ef4444" strokeWidth={1.2} fill="url(#hac-gradWd)"   dot={false} activeDot={false} connectNulls={false} />
          <Area type="monotone" dataKey="attr_upd" stackId="1" stroke="#f97316" strokeWidth={1.2} fill="url(#hac-gradAttr)" dot={false} activeDot={false} connectNulls={false} />
        </AreaChart>
      </ResponsiveContainer>
      <VerDados dados={points as unknown as Record<string, unknown>[]} />
    </div>
  )
}
