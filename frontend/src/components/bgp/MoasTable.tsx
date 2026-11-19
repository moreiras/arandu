import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import type { MoasEntry } from '../../types/routingAnalysis'
import { Tip, SortIcon, type SortDir } from './BgpShared'

interface Props {
  data: MoasEntry[]
  date?: string
}

type SortKey = 'prefix' | 'origins_count' | 'br_origins_count'

function fmt(n: number) { return n.toLocaleString('pt-BR') }

export function MoasTable({ data, date }: Props) {
  const navigate = useNavigate()
  const [afi, setAfi]         = useState<'all' | 'v6' | 'v4'>('all')
  const [page, setPage]       = useState(0)
  const [sortKey, setSortKey] = useState<SortKey>('origins_count')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
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
    const rows = data.filter((r) => afi === 'all' || r.afi === afi)
    rows.sort((a, b) => {
      let aVal: string | number
      let bVal: string | number
      switch (sortKey) {
        case 'prefix':          aVal = a.prefix;           bVal = b.prefix;           break
        case 'origins_count':   aVal = a.origins.length;   bVal = b.origins.length;   break
        case 'br_origins_count':aVal = a.br_origins.length;bVal = b.br_origins.length;break
        default:                aVal = 0;                  bVal = 0
      }
      if (typeof aVal === 'string') {
        return sortDir === 'asc' ? aVal.localeCompare(bVal as string) : (bVal as string).localeCompare(aVal)
      }
      return sortDir === 'asc' ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number)
    })
    return rows
  }, [data, afi, sortKey, sortDir])

  const visible = filtered.slice(page * PAGE, (page + 1) * PAGE)

  function SortTh({ k, label, right, tooltip }: {
    k: SortKey; label: string; right?: boolean; tooltip: string
  }) {
    const active = sortKey === k
    return (
      <th
        onClick={() => handleSort(k)}
        className={[
          'text-xs font-medium pb-1.5 px-1 cursor-pointer select-none whitespace-nowrap',
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
        <h3 className="text-sm font-medium text-gray-700">
          Prefixos com múltiplas origens{' '}
          <span className="text-xs font-normal text-gray-400">({fmt(data.length)} detectados)</span>
        </h3>
        <div className="flex gap-1">
          {(['all', 'v6', 'v4'] as const).map((a) => (
            <button
              key={a}
              onClick={() => { setAfi(a); setPage(0) }}
              className={`text-xs px-2 py-0.5 rounded ${afi === a ? 'bg-primario-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
            >
              {a === 'all' ? 'Todos' : a.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[480px]">
          <thead>
            <tr className="border-b border-gray-200">
              <SortTh k="prefix" label="Prefixo" tooltip="Prefixo IP anunciado por mais de um ASN de origem diferente." />
              <th className="text-xs font-medium text-gray-500 text-left pb-1.5 px-1">Família</th>
              <SortTh k="origins_count" label="Origens" right tooltip="Total de ASNs distintos que anunciam este prefixo como origem. Quanto mais origens, maior a chance de uso legítimo (anycast) ou de sequestro." />
              <SortTh k="br_origins_count" label="Origens BR" right tooltip="Quantas das origens detectadas são ASNs brasileiros conforme Registro.br." />
              <th className="text-xs font-medium text-gray-500 text-left pb-1.5 px-1">
                <span className="inline-flex items-center gap-0.5">
                  Prefixo BR?
                  <Tip text="Indica se o prefixo está alocado ao Brasil pelo Registro.br. Um prefixo BR com origens não-BR merece atenção especial." />
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            {visible.map((r, i) => (
              <tr key={i} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="py-1.5 px-1 text-xs font-mono text-gray-800">{r.prefix}</td>
                <td className="py-1.5 px-1 text-xs text-gray-500 uppercase">{r.afi}</td>
                <td className="py-1.5 px-1">
                  <div className="flex gap-1 flex-wrap justify-end">
                    {r.origins.slice(0, 6).map((asn) => (
                      <button
                        key={asn}
                        onClick={() => navigate(`/asn/${asn}${date ? `?date=${date}` : ''}`)}
                        className="text-xs text-primario-600 hover:underline font-mono"
                      >
                        {asn}
                      </button>
                    ))}
                    {r.origins.length > 6 && (
                      <span className="text-xs text-gray-400">+{r.origins.length - 6}</span>
                    )}
                  </div>
                </td>
                <td className="py-1.5 px-1">
                  <div className="flex gap-1 flex-wrap justify-end">
                    {r.br_origins.map((asn) => (
                      <button
                        key={asn}
                        onClick={() => navigate(`/asn/${asn}${date ? `?date=${date}` : ''}`)}
                        className="text-xs text-primario-600 hover:underline font-mono"
                      >
                        {asn}
                      </button>
                    ))}
                    {r.br_origins.length === 0 && <span className="text-xs text-gray-400">—</span>}
                  </div>
                </td>
                <td className="py-1.5 px-1 text-xs text-gray-500">
                  {r.is_prefix_br ? (
                    <span className="text-ok-600 font-medium">Sim</span>
                  ) : (
                    <span className="text-gray-400">Não</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filtered.length > PAGE && (
        <div className="flex justify-between items-center mt-3">
          <span className="text-xs text-gray-400">{fmt(filtered.length)} prefixos</span>
          <div className="flex gap-1">
            <button disabled={page === 0} onClick={() => setPage((p) => p - 1)}
              className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600 disabled:opacity-40">
              ← anterior
            </button>
            <button disabled={(page + 1) * PAGE >= filtered.length} onClick={() => setPage((p) => p + 1)}
              className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600 disabled:opacity-40">
              próxima →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
