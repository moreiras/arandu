import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import type { RoutingAnalysis } from '../../types/routingAnalysis'
import { Tip } from './BgpShared'
import { VerDados } from '../ui/VerDados'

interface Props {
  data: RoutingAnalysis
  date?: string
}

function fmt(n: number) { return n.toLocaleString('pt-BR') }

function StatRow({ label, v6, v4, tooltip }: {
  label: string; v6: string | number; v4: string | number; tooltip?: string
}) {
  return (
    <tr className="border-t border-gray-100">
      <td className="py-1.5 text-xs text-gray-600 pr-4">
        <span className="flex items-center gap-0.5">
          {label}
          {tooltip && <Tip text={tooltip} />}
        </span>
      </td>
      <td className="py-1.5 text-xs text-right font-mono text-gray-800">{typeof v6 === 'number' ? fmt(v6) : v6}</td>
      <td className="py-1.5 text-xs text-right font-mono text-gray-800">{typeof v4 === 'number' ? fmt(v4) : v4}</td>
    </tr>
  )
}

export function MoreSpecificsSection({ data, date }: Props) {
  const navigate = useNavigate()
  const ms4 = data.more_specifics.v4
  const ms6 = data.more_specifics.v6

  // Família do ranking (IPv6 primeiro). O dado traz as duas.
  const [afi, setAfi] = useState<'v6' | 'v4'>('v6')
  const top = [...data.top_asns_more_specifics]
    .filter((a) => (afi === 'v6' ? a.v6_more_spec : a.v4_more_spec) > 0)
    .sort((a, b) => (afi === 'v6' ? b.v6_more_spec - a.v6_more_spec : b.v4_more_spec - a.v4_more_spec))
    .slice(0, 15)

  const chartData = top.map((a) => ({
    name: a.name ? `${a.asn} · ${a.name.slice(0, 18)}` : String(a.asn),
    asn:  a.asn,
    root:     afi === 'v6' ? a.v6_root : a.v4_root,
    more_spec: afi === 'v6' ? a.v6_more_spec : a.v4_more_spec,
  }))

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-medium text-gray-700 mb-3">Estatísticas de mais específicos: Rotas brasileiras</h3>
        <table className="w-full">
          <thead>
            <tr>
              <th className="text-xs font-medium text-gray-500 text-left pb-1"></th>
              <th className="text-xs font-medium text-gray-500 text-right pb-1">IPv6</th>
              <th className="text-xs font-medium text-gray-500 text-right pb-1">IPv4</th>
            </tr>
          </thead>
          <tbody>
            <StatRow
              label="Prefixos raiz"
              v6={ms6.pbr_root} v4={ms4.pbr_root}
              tooltip="Prefixos que não são sub-blocos de nenhum outro prefixo brasileiro anunciado. São os 'agregados' a partir dos quais os mais específicos derivam."
            />
            <StatRow
              label="Mais específicos"
              v6={ms6.pbr_more_specific} v4={ms4.pbr_more_specific}
              tooltip="Prefixos que são sub-blocos de outro prefixo brasileiro já anunciado. Podem ser usados para engenharia de tráfego, multihoming ou anycast."
            />
            <StatRow
              label="Mesma origem que o raiz"
              v6={ms6.same_origin} v4={ms4.same_origin}
              tooltip="Mais específicos anunciados pelo mesmo ASN que anuncia o prefixo raiz. Tipicamente indica engenharia de tráfego ou blackhole routing."
            />
            <StatRow
              label="Origem diferente do raiz"
              v6={ms6.diff_origin} v4={ms4.diff_origin}
              tooltip="Mais específicos anunciados por um ASN diferente do que anuncia o prefixo raiz. Pode ser legítimo (multihoming, CDN) ou indicar MOAS."
            />
            <StatRow
              label="Profundidade máxima"
              v6={ms6.max_depth} v4={ms4.max_depth}
              tooltip="Nível máximo de aninhamento de mais específicos observado. Profundidade 1 = sub-bloco do raiz; profundidade 2 = sub-bloco de um mais específico, e assim por diante."
            />
            <StatRow
              label="Profundidade média"
              v6={ms6.avg_depth} v4={ms4.avg_depth}
              tooltip="Média do nível de aninhamento de todos os mais específicos detectados."
            />
          </tbody>
        </table>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-medium text-gray-700">
            Top ASNs por mais específicos ({afi === 'v6' ? 'IPv6' : 'IPv4'})
          </h3>
          <div className="flex text-xs rounded border border-gray-200 overflow-hidden" role="group" aria-label="Família de endereços">
            {(['v6', 'v4'] as const).map((a) => (
              <button key={a} type="button" aria-pressed={afi === a} onClick={() => setAfi(a)}
                className={`min-h-6 px-2.5 py-1 ${afi === a ? 'bg-primario-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}>
                {a === 'v6' ? 'IPv6' : 'IPv4'}
              </button>
            ))}
          </div>
        </div>
        {top.length === 0 && <p className="text-sm text-gray-500">Nenhum AS com mais específicos nesta família.</p>}
        <ResponsiveContainer width="100%" height={Math.max(220, top.length * 28)}>
          <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 16, left: 4, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={fmt} />
            <YAxis
              dataKey="name"
              type="category"
              width={160}
              tick={{ fontSize: 9 }}
              onClick={(e) => {
                const d = chartData.find((x) => x.name === e.value)
                if (d) navigate(`/asn/${d.asn}${date ? `?date=${date}` : ''}`)
              }}
              style={{ cursor: 'pointer' }}
            />
            <Tooltip
              contentStyle={{ fontSize: 11, padding: '5px 9px' }}
              itemStyle={{ padding: '1px 0' }}
              formatter={(v: number, name: string) => [fmt(v), name === 'root' ? 'Prefixo raiz' : 'Mais específicos']}
            />
            <Legend formatter={(v) => <span className="text-xs">{v === 'root' ? 'Prefixo raiz' : 'Mais específicos'}</span>} />
            <Bar dataKey="root"      stackId="a" fill="#3b82f6" name="root" />
            <Bar dataKey="more_spec" stackId="a" fill="#f97316" name="more_spec" />
          </BarChart>
        </ResponsiveContainer>
        <VerDados dados={chartData as unknown as Record<string, unknown>[]} />
      </div>
    </div>
  )
}
