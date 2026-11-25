import { useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { composicaoPorPrefixo, type RoutingAnalysis } from '../../types/routingAnalysis'
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

const fmt = (n: number | undefined) => (n ?? 0).toLocaleString('pt-BR')

export function PbrCompositionChart({ data }: Props) {
  const [measure, setMeasure] = useState<Measure>('routes')
  // Regra de D4: só as categorias com prefixo em bloco do Registro.br somam o total; "apenas origem BR" vira apoio, fora do total.
  // Documento anterior à regra: as três categorias, como foram publicadas.
  const porPrefixo = composicaoPorPrefixo(data)
  const keys = porPrefixo ? ['strict_br', 'prefix_only_br'] : ['strict_br', 'origin_only_br', 'prefix_only_br']

  // IPv6 primeiro
  const chartData = (['v6', 'v4'] as const).map((afi) => {
    const comp = data.pbr_composition[afi]
    const entry: Record<string, string | number> = { afi: afi.toUpperCase() }
    for (const k of keys) {
      entry[k] = comp[k]?.[measure] ?? 0
    }
    return entry
  })
  const apoio = (['v6', 'v4'] as const).map((afi) => ({ afi: afi === 'v6' ? 'IPv6' : 'IPv4', ...(data.pbr_composition[afi]?.asn_br_fora_de_bloco ?? { routes: 0, asns: 0 }) }))

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
      {porPrefixo ? (
        <>
          <p className="text-xs text-gray-600 mt-2">
            Rota brasileira é a de prefixo contido em bloco alocado pelo Registro.br; a origem do anúncio não define.{' '}
            <strong>Completo</strong>: prefixo brasileiro anunciado por ASN da lista do Registro.br.{' '}
            <strong>Apenas prefixo BR</strong>: prefixo brasileiro anunciado por outro ASN. As duas somam o total.
          </p>
          <p className="text-xs text-gray-600 mt-1">
            Fora do total, como apoio: rotas de ASN da lista do Registro.br em espaço de outro RIR (bloco legado ou transferido, ou rede
            estrangeira com CNPJ no Brasil):{' '}
            {apoio.map((a, i) => <span key={a.afi}>{i > 0 && '; '}{a.afi}: {fmt(a.routes)} rotas de {fmt(a.asns)} ASNs</span>)}.
          </p>
        </>
      ) : (
        <p className="text-xs text-gray-600 mt-2">
          Snapshot gerado antes da regra atual: o total inclui <strong>apenas origem BR</strong> (ASN da lista do Registro.br anunciando
          prefixo fora dos blocos do Registro.br).{' '}
          <strong>Completo</strong>: ASN e prefixo ambos brasileiros (Registro.br).{' '}
          <strong>Apenas prefixo BR</strong>: prefixo brasileiro anunciado por outro ASN.
        </p>
      )}
    </div>
  )
}
