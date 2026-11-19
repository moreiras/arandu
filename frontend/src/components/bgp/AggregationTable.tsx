import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import type { AggregationEntry } from '../../types/routingAnalysis'
import { Tip, SortIcon, type SortDir } from './BgpShared'

interface Props {
  data: AggregationEntry[]
  date?: string
}

type SortKey = 'savings_origin' | 'savings_path_pct' | 'current' | 'asn'

function fmt(n: number) { return n.toLocaleString('pt-BR') }

function toCsv(rows: AggregationEntry[]): string {
  const header = 'ASN,Nome,AFI,Rotas atuais,Após colapso,Redução,Redução %'
  const lines  = rows.map((r) =>
    `${r.asn},"${r.name}",${r.afi},${r.current},${r.by_origin},${r.savings_origin},${r.savings_path_pct}`
  )
  return [header, ...lines].join('\n')
}

export function AggregationTable({ data, date }: Props) {
  const navigate = useNavigate()
  const [sortKey, setSortKey]   = useState<SortKey>('savings_origin')
  const [sortDir, setSortDir]   = useState<SortDir>('desc')
  const [afiFilter, setAfiFilter] = useState<'all' | 'v6' | 'v4'>('all')
  const [page, setPage] = useState(0)
  const PAGE = 20

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
    setPage(0)
  }

  const filtered = useMemo(() => {
    const rows = data.filter((r) => afiFilter === 'all' || r.afi === afiFilter)
    rows.sort((a, b) => {
      const aVal = a[sortKey] as number
      const bVal = b[sortKey] as number
      return sortDir === 'desc' ? bVal - aVal : aVal - bVal
    })
    return rows
  }, [data, afiFilter, sortKey, sortDir])

  const visible = filtered.slice(page * PAGE, (page + 1) * PAGE)

  function download() {
    const blob = new Blob([toCsv(filtered)], { type: 'text/csv' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = 'agregacao.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  function SortTh({ k, label, right, tooltip }: {
    k: SortKey; label: string; right?: boolean; tooltip: string
  }) {
    const active = sortKey === k
    return (
      <th
        onClick={() => handleSort(k)}
        className={[
          'text-xs font-medium pb-1.5 px-2 cursor-pointer select-none whitespace-nowrap',
          right ? 'text-right' : 'text-left',
          active ? 'text-primario-600' : 'text-gray-500 hover:text-gray-700',
        ].join(' ')}
      >
        <span className="inline-flex items-center gap-0.5">
          {label}
          <Tip text={tooltip} />
          <SortIcon active={active} dir={sortDir} />
        </span>
      </th>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h3 className="text-sm font-medium text-gray-700">Potencial de agregação por ASN</h3>
        <div className="flex gap-2 flex-wrap">
          <div className="flex gap-1">
            {(['all', 'v6', 'v4'] as const).map((a) => (
              <button
                key={a}
                onClick={() => { setAfiFilter(a); setPage(0) }}
                className={`text-xs px-2 py-0.5 rounded ${
                  afiFilter === a ? 'bg-primario-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {a === 'all' ? 'Todos' : a.toUpperCase()}
              </button>
            ))}
          </div>
          <button
            onClick={download}
            className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600 hover:bg-gray-200"
          >
            CSV
          </button>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px]">
          <thead>
            <tr className="border-b border-gray-200">
              <SortTh k="asn" label="ASN" tooltip="Número do sistema autônomo." />
              <th className="text-xs font-medium text-gray-500 text-left pb-1.5 px-2">Organização</th>
              <th className="text-xs font-medium text-gray-500 text-left pb-1.5 px-2">Família</th>
              <SortTh k="current"          label="Rotas atuais"  right tooltip="Número de prefixos que o ASN anuncia atualmente na tabela global." />
              <SortTh k="savings_origin"   label="Redução"       right tooltip="Quantas rotas seriam eliminadas se o ASN agregasse seus blocos contíguos. Calculado com ipaddress.collapse_addresses." />
              <SortTh k="savings_path_pct" label="Redução %"     right tooltip="Percentual de redução em relação ao total atual. Quanto maior, maior o potencial de compactação." />
            </tr>
          </thead>
          <tbody>
            {visible.map((r, i) => (
              <tr key={i} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="py-1.5 px-2">
                  <button
                    className="text-xs text-primario-600 hover:underline font-mono"
                    onClick={() => navigate(`/asn/${r.asn}${date ? `?date=${date}` : ''}`)}
                  >
                    {r.asn}
                  </button>
                </td>
                <td className="py-1.5 px-2 text-xs text-gray-700 max-w-[160px] truncate">{r.name || '—'}</td>
                <td className="py-1.5 px-2 text-xs text-gray-500 uppercase">{r.afi}</td>
                <td className="py-1.5 px-2 text-xs text-right font-mono text-gray-800">{fmt(r.current)}</td>
                <td className="py-1.5 px-2 text-xs text-right font-mono text-alerta-600">−{fmt(r.savings_origin)}</td>
                <td className="py-1.5 px-2 text-xs text-right font-mono text-alerta-600">{r.savings_path_pct}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {filtered.length > PAGE && (
        <div className="flex justify-between items-center mt-3">
          <span className="text-xs text-gray-400">{fmt(filtered.length)} ASNs com potencial de agregação</span>
          <div className="flex gap-1">
            <button
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
              className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600 disabled:opacity-40"
            >
              ← anterior
            </button>
            <button
              disabled={(page + 1) * PAGE >= filtered.length}
              onClick={() => setPage((p) => p + 1)}
              className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600 disabled:opacity-40"
            >
              próxima →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
