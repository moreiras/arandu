import type { BgpStabilityHistoryEntry } from '../../types/bgpStability'
import { HourlyActivityChart } from './HourlyActivityChart'

interface Props {
  weeks: BgpStabilityHistoryEntry[]
}

export function BgpActivityChart({ weeks }: Props) {
  const series = weeks.map(w => ({
    date:       w.date,
    timestamps: w.data.hourly_global.timestamps,
    series:     w.data.hourly_global,
  }))
  const rangeLabel = weeks.length > 1
    ? `, últimas ${weeks.length} semanas`
    : ''
  return (
    <HourlyActivityChart
      weeks={series}
      title={`Atividade BGP: eventos por hora (todos os ASes BR)${rangeLabel}`}
      tipText="Série temporal de updates BGP (anúncios, retiradas, attr-updates) com resolução horária, uma semana por snapshot semanal disponível. Eventos deduplicados: múltiplos peers reportando o mesmo evento dentro de 90s são contados uma única vez."
    />
  )
}
