import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { fetchSnapshots } from '../../services/api'
import { useAppStore } from '../../store/app'
import { useAuth } from '../../auth/AuthContext'
import { isHistoricalDate } from '../../auth/accessPolicy'
import { formatarData } from '../../lib/datas'

export function SnapshotSelector() {
  const [params, setParams] = useSearchParams()
  const activeDate = useAppStore((s) => s.activeDate)
  const { requireLogin } = useAuth()
  const { data } = useQuery({
    queryKey: ['snapshots'],
    queryFn: fetchSnapshots,
    staleTime: Infinity, gcTime: Infinity,
  })

  if (!data || data.count === 0) return null

  const current = params.get('date') ?? activeDate ?? data.latest ?? ''

  function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const val = e.target.value
    // Snapshots antigos (histórico) exigem login; o seletor volta ao atual.
    if (isHistoricalDate(val, data?.snapshots) && !requireLogin('historico')) return
    if (val === data?.latest) {
      params.delete('date')
    } else {
      params.set('date', val)
    }
    setParams(params, { replace: true })
  }

  return (
    <div className="flex items-center gap-1.5 text-sm min-w-0">
      <span className="text-gray-400 text-xs hidden sm:inline">Snapshot:</span>
      <select
        value={current}
        onChange={handleChange}
        aria-label="Snapshot"
        className="min-w-0 max-w-[12rem] sm:max-w-none border border-gray-200 rounded px-2 py-0.5 text-sm bg-white focus:outline-none focus:ring-1 focus:ring-primario-400"
      >
        {data.snapshots.map((d) => (
          <option key={d} value={d}>
            {formatarData(d)}
            {d === data.latest ? ' (atual)' : ''}
          </option>
        ))}
      </select>
    </div>
  )
}
