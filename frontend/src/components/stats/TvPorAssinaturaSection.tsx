import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, Legend,
} from 'recharts'
import { fetchOutorgasStats } from '../../services/api'
import type { SEACStats } from '../../types/api'
import { VerDados } from '../ui/VerDados'

const SECTION_COLOR = '#9333ea'
const COLOR_WITH_ASN = '#60a5fa'
const COLOR_WITHOUT_ASN = '#d8b4fe'

const fmt = (n: number | null | undefined) => (n == null ? '—' : n.toLocaleString('pt-BR'))
const fmtPct = (n: number | null | undefined, dec = 1) =>
  n == null ? '—' : `${n.toLocaleString('pt-BR', { minimumFractionDigits: dec, maximumFractionDigits: dec })}%`

function StatCard({ value, label, sub, accent }: { value: string; label: string; sub?: string; accent?: string }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 px-4 py-3">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-bold tabular-nums" style={accent ? { color: accent } : undefined}>{value}</div>
      {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}

function OutorgasPorUf({ stats }: { stats: SEACStats }) {
  const ufData = (stats.uf_breakdown ?? []).slice(0, 16)
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="text-xs text-gray-500 mb-2 font-medium">Outorgas SeAC por UF (com/sem ASN)</div>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={ufData} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
          <XAxis dataKey="uf" tick={{ fontSize: 11 }} interval={0} />
          <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
          <Tooltip formatter={(v: number, name: string) => [fmt(v), name === 'with_asn' ? 'Com ASN' : 'Sem ASN']}
                   labelFormatter={(l) => `UF: ${l}`} />
          <Legend formatter={(v) => (v === 'with_asn' ? 'Com ASN' : 'Sem ASN')} wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="with_asn" stackId="a" fill={COLOR_WITH_ASN} />
          <Bar dataKey="without_asn" stackId="a" fill={COLOR_WITHOUT_ASN} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <VerDados dados={ufData as unknown as Record<string, unknown>[]} />
    </div>
  )
}

/**
 * SeAC não tem declaração de acessos ao SICI equivalente (ao contrário de SCM/SMP) —
 * a seção é só licenciamento × ASN no mesmo CNPJ × geografia da outorga.
 */
export function TvPorAssinaturaSection({ date }: { date?: string }) {
  const { data: stats, isError } = useQuery({
    queryKey: ['seac-stats-full', date],
    queryFn: () => fetchOutorgasStats('SeAC', date),
    staleTime: 10 * 60 * 1000,
  })

  if (isError || !stats) return null

  const licensed = stats.unique_cnpjs ?? 0
  const withAsn = stats.cnpjs_with_asn ?? 0
  const withoutAsn = Math.max(licensed - withAsn, 0)
  const pctComAsn = licensed > 0 ? (withAsn / licensed) * 100 : null

  const donut = [
    { name: 'Com ASN no mesmo CNPJ', value: withAsn, color: COLOR_WITH_ASN },
    { name: 'Sem ASN no mesmo CNPJ', value: withoutAsn, color: COLOR_WITHOUT_ASN },
  ]

  return (
    <section className="space-y-6">
      <h2 className="text-sm font-semibold uppercase tracking-widest border-t border-gray-100 pt-8"
          style={{ color: SECTION_COLOR }}>
        TV por assinatura — SeAC (Anatel)
      </h2>

      <div>
        <h3 className="text-base font-semibold text-gray-800 mb-1">Licença e ASN</h3>
        <p className="text-xs text-gray-500 mb-4">
          Prestadoras com outorga de SeAC (Serviço de Acesso Condicionado — TV por assinatura,
          Lei 12.485/2011), cruzadas por CNPJ com os ASNs do Registro.br. {fmt(licensed)} CNPJs
          outorgados neste snapshot. Esta página não traz assinantes de SeAC: não há declaração equivalente ao SICI para este serviço. O cruzamento é por CNPJ: uma operadora sem ASN pode usar a rede de outra empresa do grupo ou de um fornecedor, e ter ASN não garante anúncio na tabela BGP.
        </p>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 grid grid-cols-2 md:grid-cols-3 gap-3">
            <StatCard value={fmt(licensed)} label="Operadores licenciados" sub="CNPJs únicos com outorga SeAC" accent={SECTION_COLOR} />
            <StatCard value={fmt(withAsn)} label="…com ASN" sub="ASN no Registro.br com o mesmo CNPJ" accent={COLOR_WITH_ASN} />
            <StatCard value={fmt(withoutAsn)} label="…sem ASN" sub="nenhum ASN no Registro.br com o mesmo CNPJ" accent={COLOR_WITHOUT_ASN} />
            <StatCard value={fmtPct(pctComAsn)} label="Parcela com ASN" sub="licenciados com ASN no mesmo CNPJ" />
            <StatCard value={fmt(stats.total)} label="Outorgas totais" sub="pode haver várias por CNPJ" />
            <StatCard value={fmt(stats.geolocated)} label="Geolocalizadas" sub={fmtPct(stats.total ? (100 * stats.geolocated) / stats.total : null)} />
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-3 flex flex-col">
            <div className="text-xs text-gray-500 mb-1">Operadores licenciados</div>
            <div className="relative flex-1 flex items-center justify-center">
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie data={donut} dataKey="value" innerRadius={48} outerRadius={68} paddingAngle={2} startAngle={90} endAngle={-270}>
                    {donut.map(e => <Cell key={e.name} fill={e.color} aria-label={e.name} />)}
                  </Pie>
                  <Tooltip formatter={(v: number, name: string) => [fmt(v), name]} />
                </PieChart>
              </ResponsiveContainer>
              <VerDados dados={donut as unknown as Record<string, unknown>[]} />
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <div className="text-lg font-bold tabular-nums text-gray-800">{fmtPct(pctComAsn, 0)}</div>
                <div className="text-xs text-gray-400">com ASN</div>
              </div>
            </div>
            <div className="flex justify-center gap-3 text-xs text-gray-600">
              {donut.map(e => (
                <span key={e.name} className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: e.color }} />
                  {e.name.split(' ')[0]}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-base font-semibold text-gray-800 mb-1">Geografia da outorga</h3>
        <p className="text-xs text-gray-500 mb-4">Distribuição das outorgas SeAC por UF.</p>
        <OutorgasPorUf stats={stats} />
      </div>
    </section>
  )
}
