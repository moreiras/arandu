import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, Cell, ResponsiveContainer,
} from 'recharts'
import type { PrefixLengthEntry } from '../../types/routingAnalysis'
import { VerDados } from '../ui/VerDados'

interface Props {
  data: PrefixLengthEntry[]
  afi: 'v4' | 'v6'
}

function threshold(afi: 'v4' | 'v6') {
  return afi === 'v4' ? 24 : 48
}

export function PrefixLengthHistogram({ data, afi }: Props) {
  const t = threshold(afi)

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-sm font-medium text-gray-700 mb-3">
        Distribuição por tamanho do prefixo (prefix length), IP{afi}
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="length"
            tick={{ fontSize: 10 }}
            tickFormatter={(v) => `/${v}`}
            interval="preserveStart"
          />
          <YAxis
            tick={{ fontSize: 10 }}
            width={50}
            tickFormatter={(v) => v.toLocaleString('pt-BR')}
          />
          <Tooltip
            contentStyle={{ fontSize: 11, padding: '5px 9px' }}
            itemStyle={{ padding: '1px 0' }}
            formatter={(value: number, _: string, props: { payload?: PrefixLengthEntry }) => {
              const pct = props.payload?.pct_routes ?? 0
              return [`${value.toLocaleString('pt-BR')} rotas (${pct}% do total)`, '']
            }}
            labelFormatter={(label) => `Comprimento de prefixo: /${label}`}
          />
          <ReferenceLine
            x={t}
            stroke="#ef4444"
            strokeDasharray="4 2"
            label={{ value: `/${t}`, position: 'top', fontSize: 10, fill: '#ef4444' }}
          />
          <Bar dataKey="count" name="Rotas">
            {data.map((entry) => (
              <Cell
                key={entry.length}
                fill={entry.length > t ? '#f97316' : '#3b82f6'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <VerDados dados={data as unknown as Record<string, unknown>[]} />
      <p className="text-xs text-gray-400 mt-1">
        Barras laranjas: prefixos acima de /{t} (potencialmente filtráveis por operadores).
      </p>
    </div>
  )
}
