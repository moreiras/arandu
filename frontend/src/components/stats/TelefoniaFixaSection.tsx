import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, Legend,
} from 'recharts'
import { fetchOutorgasStats } from '../../services/api'
import type { STFCStats } from '../../types/api'
import { corLegivel } from '../../lib/contraste'
import { VerDados } from '../ui/VerDados'

const SECTION_COLOR = '#334155'
const COLOR_WITH_ASN = '#60a5fa'
const COLOR_WITHOUT_ASN = '#94a3b8'

const fmt = (n: number | null | undefined) => (n == null ? '—' : n.toLocaleString('pt-BR'))
const fmtPct = (n: number | null | undefined, dec = 1) =>
  n == null ? '—' : `${n.toLocaleString('pt-BR', { minimumFractionDigits: dec, maximumFractionDigits: dec })}%`

function StatCard({ value, label, sub, accent }: { value: string; label: string; sub?: string; accent?: string }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 px-4 py-3">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-bold tabular-nums" style={accent ? { color: corLegivel(accent) } : undefined}>{value}</div>
      {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}

function OutorgasPorUf({ stats }: { stats: STFCStats }) {
  const ufData = (stats.uf_breakdown ?? []).slice(0, 16)
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="text-xs text-gray-500 mb-2 font-medium">Outorgas STFC por UF (com/sem ASN)</div>
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
 * STFC não tem declaração de acessos ao SICI equivalente (ao contrário de SCM/SMP) —
 * a seção é só licenciamento × autonomia (ASN) × geografia da outorga.
 */
export function TelefoniaFixaSection({ date }: { date?: string }) {
  const { data: stats, isError } = useQuery({
    queryKey: ['stfc-stats-full', date],
    queryFn: () => fetchOutorgasStats('STFC', date),
    staleTime: 10 * 60 * 1000,
  })

  if (isError || !stats) return null

  const licensed = stats.unique_cnpjs ?? 0
  const withAsn = stats.cnpjs_with_asn ?? 0
  const withoutAsn = Math.max(licensed - withAsn, 0)
  const autonomizacao = licensed > 0 ? (withAsn / licensed) * 100 : null

  const donut = [
    { name: 'Com ASN (autônomos)', value: withAsn, color: COLOR_WITH_ASN },
    { name: 'Sem ASN (só licença)', value: withoutAsn, color: COLOR_WITHOUT_ASN },
  ]

  return (
    <section className="space-y-6">
      <h2 className="text-sm font-semibold uppercase tracking-widest border-t border-gray-100 pt-8"
          style={{ color: SECTION_COLOR }}>
        Telefonia fixa comutada — STFC (Anatel)
      </h2>

      <div>
        <h3 className="text-base font-semibold text-gray-800 mb-1">Licença e autonomia</h3>
        <p className="text-xs text-gray-500 mb-4">
          Prestadoras com outorga de STFC, cruzadas por CNPJ com os ASNs do Registro.br.
          Universo maior que SMP (~1.700 CNPJs): inclui pequenos provedores de VoIP e
          telefonia fixa. Sem declaração de acessos equivalente ao SICI para este serviço.
        </p>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 grid grid-cols-2 md:grid-cols-3 gap-3">
            <StatCard value={fmt(licensed)} label="Operadores licenciados" sub="CNPJs únicos com outorga STFC" accent={SECTION_COLOR} />
            <StatCard value={fmt(withAsn)} label="…com ASN" sub="autônomos no BGP" accent={COLOR_WITH_ASN} />
            <StatCard value={fmt(withoutAsn)} label="…sem ASN" sub="licenciados, ausentes do BGP" accent={COLOR_WITHOUT_ASN} />
            <StatCard value={fmtPct(autonomizacao)} label="Taxa de autonomização" sub="licenciados que viraram AS" />
            <StatCard value={fmt(stats.total)} label="Outorgas totais" sub="pode haver várias por CNPJ" />
            <StatCard value={fmt(stats.geolocated)} label="Geolocalizadas" sub={fmtPct(stats.total ? (100 * stats.geolocated) / stats.total : null)} />
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-3 flex flex-col">
            <div className="text-xs text-gray-500 mb-1">Operadores licenciados</div>
            <div className="relative flex-1 flex items-center justify-center">
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie data={donut} dataKey="value" innerRadius={48} outerRadius={68} paddingAngle={2} startAngle={90} endAngle={-270}>
                    {donut.map(e => <Cell key={e.name} fill={e.color} />)}
                  </Pie>
                  <Tooltip formatter={(v: number, name: string) => [fmt(v), name]} />
                </PieChart>
              </ResponsiveContainer>
              <VerDados dados={donut as unknown as Record<string, unknown>[]} />
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <div className="text-lg font-bold tabular-nums text-gray-800">{fmtPct(autonomizacao, 0)}</div>
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
        <p className="text-xs text-gray-500 mb-4">Distribuição das outorgas STFC por UF.</p>
        <OutorgasPorUf stats={stats} />
      </div>
    </section>
  )
}
