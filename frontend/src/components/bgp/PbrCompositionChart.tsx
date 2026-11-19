import { useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import type { RoutingAnalysis } from '../../types/routingAnalysis'
import { VerDados } from '../ui/VerDados'

interface Props { data: RoutingAnalysis }

type Measure = 'routes' | 'asns'

const LABELS: Record<string, string> = {
  strict_br:      'Completo (ASN + prefixo BR)',
  origin_only_br: 'Apenas origem BR',
  prefix_only_br: 'Apenas prefixo BR',
}

const COLORS: Record<string, string> = {
  strict_br:      '#22c55e',
  origin_only_br: '#eab308',
  prefix_only_br: '#f97316',
}

export function PbrCompositionChart({ data }: Props) {
  const [measure, setMeasure] = useState<Measure>('routes')

  const keys = ['strict_br', 'origin_only_br', 'prefix_only_br']

  // IPv6 primeiro
  const chartData = (['v6', 'v4'] as const).map((afi) => {
    const comp = data.pbr_composition[afi]
    const entry: Record<string, string | number> = { afi: afi.toUpperCase() }
    for (const k of keys) {
      entry[k] = comp[k]?.[measure] ?? 0
    }
    return entry
  })

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-700">Composição por categoria</h3>
        <div className="flex gap-1">
          {(['routes', 'asns'] as Measure[]).map((m) => (
            <button
              key={m}
              onClick={() => setMeasure(m)}
              className={`text-xs px-2 py-0.5 rounded ${
                measure === m
                  ? 'bg-primario-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {m === 'routes' ? 'Rotas' : 'ASNs'}
            </button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="afi" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 11 }} width={55} tickFormatter={(v) => v.toLocaleString('pt-BR')} />
          <Tooltip
            contentStyle={{ fontSize: 11, padding: '5px 9px' }}
            itemStyle={{ padding: '1px 0' }}
            formatter={(value: number, name: string) => [
              value.toLocaleString('pt-BR'),
              LABELS[name] ?? name,
            ]}
          />
          <Legend
            formatter={(value) => (
              <span className="text-xs text-gray-600">{LABELS[value] ?? value}</span>
            )}
          />
          {keys.map((k) => (
            <Bar key={k} dataKey={k} stackId="a" fill={COLORS[k]} name={k} />
          ))}
        </BarChart>
      </ResponsiveContainer>
      <VerDados dados={chartData as unknown as Record<string, unknown>[]} />
      <p className="text-xs text-gray-400 mt-2">
        <strong>Completo</strong>: ASN e prefixo ambos brasileiros (Registro.br).{' '}
        <strong>Apenas origem BR</strong>: ASN brasileiro anuncia prefixo não alocado ao Brasil.{' '}
        <strong>Apenas prefixo BR</strong>: prefixo brasileiro anunciado por ASN estrangeiro.
      </p>
    </div>
  )
}
