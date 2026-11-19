import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import type { TooSpecificEntry } from '../../types/routingAnalysis'
import { Tip, SortIcon, type SortDir } from './BgpShared'

interface Props {
  v4: TooSpecificEntry[]
  v6: TooSpecificEntry[]
  date?: string
}

type SortKey = 'prefix' | 'origin_as' | 'name' | 'has_covering' | 'is_prefix_br'

function fmt(n: number) { return n.toLocaleString('pt-BR') }

export function TooSpecificTable({ v4, v6, date }: Props) {
  const navigate  = useNavigate()
  // IPv6 primeiro como padrão
  const [afi, setAfi]               = useState<'v6' | 'v4'>('v6')
  const [page, setPage]             = useState(0)
  const [sortKey, setSortKey]       = useState<SortKey>('prefix')
  const [sortDir, setSortDir]       = useState<SortDir>('asc')
  const [showBlackhole, setShowBlackhole] = useState(false)
  const PAGE = 25

  const threshold = afi === 'v4' ? '/24' : '/48'

  function isBlackholeLength(prefix: string, a: 'v4' | 'v6') {
    return a === 'v4' ? prefix.endsWith('/32') : prefix.endsWith('/64')
  }

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
    setPage(0)
  }

  const blackholeCount = useMemo(() => {
    const rows = afi === 'v4' ? v4 : v6
    return rows.filter((r) => isBlackholeLength(r.prefix, afi)).length
  }, [afi, v4, v6])

  const sorted = useMemo(() => {
    const rows = (afi === 'v4' ? v4 : v6).filter(
      (r) => showBlackhole || !isBlackholeLength(r.prefix, afi)
    )
    rows.sort((a, b) => {
      let aVal: string | number | boolean
      let bVal: string | number | boolean
      switch (sortKey) {
        case 'prefix':       aVal = a.prefix;       bVal = b.prefix;       break
        case 'origin_as':    aVal = a.origin_as;    bVal = b.origin_as;    break
        case 'name':         aVal = a.name ?? '';   bVal = b.name ?? '';   break
        case 'has_covering': aVal = a.has_covering ? 1 : 0; bVal = b.has_covering ? 1 : 0; break
        case 'is_prefix_br': aVal = a.is_prefix_br ? 1 : 0; bVal = b.is_prefix_br ? 1 : 0; break
        default:             aVal = 0;              bVal = 0
      }
      if (typeof aVal === 'string') {
        return sortDir === 'asc' ? aVal.localeCompare(bVal as string) : (bVal as string).localeCompare(aVal)
      }
      return sortDir === 'asc' ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number)
    })
    return rows
  }, [afi, v4, v6, sortKey, sortDir, showBlackhole])

  const visible = sorted.slice(page * PAGE, (page + 1) * PAGE)

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
      <div className="flex items-start justify-between mb-3 flex-wrap gap-2">
        <div>
          <h3 className="text-sm font-medium text-gray-700">
            Prefixos potencialmente filtráveis (mais específicos que {threshold})
          </h3>
          {!showBlackhole && blackholeCount > 0 && (
            <p className="text-xs text-gray-400 mt-0.5">
              {fmt(blackholeCount)} prefixos {afi === 'v4' ? '/32' : '/64'} ocultados (comuns em blackhole/RTBH)
            </p>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          {/* IPv6 primeiro */}
          <div className="flex gap-1">
            {(['v6', 'v4'] as const).map((a) => (
              <button
                key={a}
                onClick={() => { setAfi(a); setPage(0); setSortKey('prefix'); setSortDir('asc') }}
                className={`text-xs px-2 py-0.5 rounded ${afi === a ? 'bg-primario-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
              >
                {a.toUpperCase()} ({fmt(a === 'v4' ? v4.length : v6.length)})
              </button>
            ))}
          </div>
          <button
            onClick={() => { setShowBlackhole((s) => !s); setPage(0) }}
            className="text-xs px-2 py-0.5 rounded border border-gray-200 text-gray-500 hover:bg-gray-50"
          >
            {showBlackhole ? 'Ocultar IPv6 /64 e IPv4 /32' : 'Mostrar também IPv6 /64 e IPv4 /32'}
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px]">
          <thead>
            <tr className="border-b border-gray-200">
              <SortTh k="prefix"
                label="Prefixo"
                tooltip={`Prefixo mais específico que ${threshold}. Operadores de backbone costumam filtrar esses prefixos por excederem o limite de granularidade aceito.`}
              />
              <SortTh k="origin_as"
                label="ASN"
                tooltip="Sistema autônomo que origina este prefixo na tabela global."
              />
              <SortTh k="name"
                label="Organização"
                tooltip="Nome da organização titular do ASN de origem."
              />
              <SortTh k="has_covering"
                label="Tem agregado?"
                tooltip="Indica se há um prefixo menos específico (agregado) do mesmo ASN na tabela. Se sim, o tráfego seria absorvido pelo agregado mesmo se este prefixo fosse filtrado. Se não, filtrar causaria blackhole."
              />
              <SortTh k="is_prefix_br"
                label="Prefixo BR?"
                tooltip="Indica se o prefixo está alocado ao Brasil pelo Registro.br."
              />
            </tr>
          </thead>
          <tbody>
            {visible.map((r, i) => (
              <tr key={i} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="py-1.5 px-1 text-xs font-mono text-gray-800">{r.prefix}</td>
                <td className="py-1.5 px-1">
                  <button
                    className="text-xs text-primario-600 hover:underline font-mono"
                    onClick={() => navigate(`/asn/${r.origin_as}${date ? `?date=${date}` : ''}`)}
                  >
                    {r.origin_as}
                  </button>
                </td>
                <td className="py-1.5 px-1 text-xs text-gray-700 max-w-[160px] truncate" title={r.name}>
                  {r.name || '—'}
                </td>
                <td className="py-1.5 px-1 text-xs">
                  {r.has_covering ? (
                    <span className="text-ok-600">Sim</span>
                  ) : (
                    <span className="text-alerta-500">Não</span>
                  )}
                </td>
                <td className="py-1.5 px-1 text-xs">
                  {r.is_prefix_br ? (
                    <span className="text-primario-600">Sim</span>
                  ) : (
                    <span className="text-gray-400">Não</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {sorted.length > PAGE && (
        <div className="flex justify-between items-center mt-3">
          <span className="text-xs text-gray-400">{fmt(sorted.length)} prefixos</span>
          <div className="flex gap-1">
            <button disabled={page === 0} onClick={() => setPage((p) => p - 1)}
              className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600 disabled:opacity-40">
              ← anterior
            </button>
            <button disabled={(page + 1) * PAGE >= sorted.length} onClick={() => setPage((p) => p + 1)}
              className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600 disabled:opacity-40">
              próxima →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
