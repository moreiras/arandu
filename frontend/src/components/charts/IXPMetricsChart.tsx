import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import type { IXPIndexEntry } from '../../types/api'
import { VerDados } from '../ui/VerDados'

type DataPoint = { name: string; value: number; ixp: IXPIndexEntry }

interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{ value: number; payload: DataPoint }>
  renderContent: (ixp: IXPIndexEntry, value: number) => React.ReactNode
}

function CustomTooltip({ active, payload, renderContent }: CustomTooltipProps) {
  if (!active || !payload?.[0]) return null
  const { value, payload: dp } = payload[0]
  return (
    <div className="bg-white border border-gray-200 rounded shadow-lg p-3 text-xs max-w-xs leading-relaxed text-gray-700">
      {renderContent(dp.ixp, value)}
    </div>
  )
}

interface IXPMetricsChartProps {
  ixps: IXPIndexEntry[]
  getValue: (ixp: IXPIndexEntry) => number | null
  label: string
  color?: string
  isPct?: boolean
  height?: number
  renderTooltipContent?: (ixp: IXPIndexEntry, value: number) => React.ReactNode
}

export function IXPMetricsChart({
  ixps,
  getValue,
  label,
  color = '#3b82f6',
  isPct = false,
  height = 280,
  renderTooltipContent,
}: IXPMetricsChartProps) {
  const data: DataPoint[] = ixps
    .map((ixp) => ({ name: ixp.code.toUpperCase(), value: getValue(ixp) as number, ixp }))
    .filter((d) => d.value != null)
    .sort((a, b) => b.value - a.value)

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
        Dados não disponíveis no snapshot atual.
      </div>
    )
  }

  const tooltipEl = renderTooltipContent
    ? (props: object) => (
        <CustomTooltip
          {...(props as CustomTooltipProps)}
          renderContent={renderTooltipContent}
        />
      )
    : undefined

  return (
    <>
<ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-45} textAnchor="end" interval={0} />
        <YAxis tick={{ fontSize: 11 }} unit={isPct ? '%' : undefined} />
        {tooltipEl ? (
          <Tooltip content={tooltipEl} />
        ) : (
          <Tooltip
            formatter={(v: number) => [
              isPct ? `${v.toFixed(2)}%` : v.toLocaleString('pt-BR'),
              label,
            ]}
          />
        )}
        <Bar dataKey="value" name={label} fill={color} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
    <VerDados dados={data as unknown as Record<string, unknown>[]} />
</>
  )
}
