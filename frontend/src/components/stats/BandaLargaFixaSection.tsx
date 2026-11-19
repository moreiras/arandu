import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, Legend,
} from 'recharts'
import { fetchOutorgasStats, fetchAcessosStats, fetchDivergenciasSCM } from '../../services/api'
import { AccessHistoryChart } from '../acessos/AccessHistoryChart'
import { SpeedDistributionChart } from './SpeedDistributionChart'
import { UF_REGION, REGION_ORDER, REGION_COLOR } from '../../utils/regioes'
import type { SiciSeriePoint, SCMStats, SiciStats } from '../../types/api'
import { useAuth } from '../../auth/AuthContext'
import { corLegivel } from '../../lib/contraste'
import { VerDados } from '../ui/VerDados'

const SECTION_COLOR = '#7c3aed'
const COLOR_WITH_ASN = '#60a5fa'
const COLOR_WITHOUT_ASN = '#a855f7'
const COLOR_PF = '#0ea5e9'
const COLOR_PJ = '#f59e0b'

const fmt = (n: number | null | undefined) => (n == null ? '—' : n.toLocaleString('pt-BR'))
const fmtPct = (n: number | null | undefined, dec = 1) =>
  n == null ? '—' : `${n.toLocaleString('pt-BR', { minimumFractionDigits: dec, maximumFractionDigits: dec })}%`

const DIVERGENCIAS_INICIAL = 20
const DIVERGENCIAS_EXPANDIDO = 1000

function DivergenciasSCM({ date }: { date?: string }) {
  const [expanded, setExpanded] = useState(false)
  const { requireLogin } = useAuth()
  const limit = expanded ? DIVERGENCIAS_EXPANDIDO : DIVERGENCIAS_INICIAL
  const { data: divs, isFetching } = useQuery({
    queryKey: ['acessos-divergencias-scm', date, limit],
    queryFn: () => fetchDivergenciasSCM({ date, limit }),
    placeholderData: prev => prev,
    retry: false,
    staleTime: 10 * 60 * 1000,
  })

  if (!divs || divs.items.length === 0) return null

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="px-4 py-2 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-700">Maiores divergências entre APNIC e Anatel</h3>
        <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">
          Operadoras com outorga SCM e um único ASN cujos usuários estimados pelo APNIC chegam a
          {' '}{fmt(divs.min_razao)}× o esperado pelos acessos de banda larga fixa declarados ao SICI ({divs.mes_referencia}):
          {' '}<b>esperado = {fmt(divs.k_pf)} × B2C + {fmt(divs.k_pj)} × B2B</b> — pessoas por
          domicílio e uma estimativa folgada de usuários por empresa. Ordenado por usuários APNIC.
          Acessos móveis não entram na conta, embora o APNIC os observe. É ponto de partida para
          investigar, não erro comprovado de nenhuma das fontes.
          {' '}{fmt(divs.total)} ASNs nessa situação, {fmt(divs.sem_acessos)} deles sem nenhum acesso declarado.
        </p>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-400 bg-gray-50 border-b border-gray-100">
            <th className="px-4 py-1.5 w-10 text-right">#</th>
            <th className="px-4 py-1.5 w-24">AS</th>
            <th className="px-4 py-1.5">Nome</th>
            <th className="px-4 py-1.5 w-24 text-right">B2C</th>
            <th className="px-4 py-1.5 w-24 text-right">B2B</th>
            <th className="px-4 py-1.5 w-28 text-right">Esperado</th>
            <th className="px-4 py-1.5 w-28 text-right">APNIC</th>
            <th className="px-4 py-1.5 w-20 text-right">Razão</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {divs.items.map((d, i) => (
            <tr key={d.asn} className="hover:bg-gray-50">
              <td className="px-4 py-1 text-right tabular-nums text-gray-400">{i + 1}</td>
              <td className="px-4 py-1">
                <Link to={`/asn/${d.asn}`} className="text-primario-600 hover:underline">AS{d.asn}</Link>
              </td>
              <td className="px-4 py-1 text-gray-700 truncate" title={d.empresa || undefined}>{d.name}</td>
              <td className="px-4 py-1 text-right tabular-nums text-gray-500">{fmt(d.acessos_pf)}</td>
              <td className="px-4 py-1 text-right tabular-nums text-gray-500">{fmt(d.acessos_pj)}</td>
              <td className={`px-4 py-1 text-right tabular-nums ${d.esperado === 0 ? 'text-perigo-600 font-medium' : ''}`}>
                {fmt(d.esperado)}
              </td>
              <td className="px-4 py-1 text-right tabular-nums font-medium">{fmt(d.apnic_users)}</td>
              <td className="px-4 py-1 text-right tabular-nums">
                {d.razao == null ? '—' : `${d.razao.toLocaleString('pt-BR')}×`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {divs.total > DIVERGENCIAS_INICIAL && (
        <div className="px-4 py-2 border-t border-gray-100 text-center">
          <button
            type="button"
            onClick={() => { if (!expanded && !requireLogin('lista-expandida')) return; setExpanded(e => !e) }}
            disabled={isFetching}
            className="text-xs text-primario-600 hover:underline disabled:text-gray-400"
          >
            {isFetching
              ? 'Carregando…'
              : expanded
                ? `Mostrar apenas os ${DIVERGENCIAS_INICIAL} maiores`
                : `Mostrar os ${fmt(Math.min(DIVERGENCIAS_EXPANDIDO, divs.total))} maiores`}
          </button>
        </div>
      )}
    </div>
  )
}

function StatCard({ value, label, sub, accent }: { value: string; label: string; sub?: string; accent?: string }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 px-4 py-3">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-bold tabular-nums" style={accent ? { color: corLegivel(accent) } : undefined}>{value}</div>
      {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}

function Barras({ dados, total, limite = 6 }: { dados: Record<string, number>; total: number; limite?: number }) {
  const rows = Object.entries(dados).sort((a, b) => b[1] - a[1]).slice(0, limite)
  return (
    <div className="space-y-1">
      {rows.map(([k, v]) => (
        <div key={k} className="flex items-center gap-2 text-xs">
          <span className="w-28 truncate text-gray-600" title={k}>{k}</span>
          <span className="flex-1 h-2.5 bg-gray-100 rounded-sm overflow-hidden">
            <span className="block h-full bg-primario-500/70" style={{ width: `${total ? (100 * v) / total : 0}%` }} />
          </span>
          <span className="w-24 text-right tabular-nums text-gray-500">{fmt(v)}</span>
        </div>
      ))}
    </div>
  )
}

// ── outorgas × acessos por UF/região ────────────────────────────────────────────

function OutorgasPorUf({ scm }: { scm: SCMStats }) {
  const ufData = (scm.uf_breakdown ?? []).slice(0, 16)
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="text-xs text-gray-500 mb-2 font-medium">Outorgas SCM por UF (com/sem ASN)</div>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={ufData} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
          <XAxis dataKey="uf" tick={{ fontSize: 11 }} interval={0} />
          <YAxis tick={{ fontSize: 11 }} />
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

function AcessosPorUf({ acessos }: { acessos: SiciStats }) {
  const ufData = Object.entries(acessos.por_uf ?? {})
    .map(([uf, v]) => ({ uf, ...v }))
    .sort((a, b) => b.acessos - a.acessos)
    .slice(0, 16)
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="text-xs text-gray-500 mb-2 font-medium">Acessos declarados (SICI) por UF (B2C/B2B)</div>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={ufData} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
          <XAxis dataKey="uf" tick={{ fontSize: 11 }} interval={0} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip formatter={(v: number, name: string) => [fmt(v), name === 'pf' ? 'B2C' : 'B2B']}
                   labelFormatter={(l) => `UF: ${l}`} />
          <Legend formatter={(v) => (v === 'pf' ? 'B2C' : 'B2B')} wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="pf" stackId="a" fill={COLOR_PF} />
          <Bar dataKey="pj" stackId="a" fill={COLOR_PJ} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <VerDados dados={ufData as unknown as Record<string, unknown>[]} />
    </div>
  )
}

function OutorgasPorRegiao({ scm }: { scm: SCMStats }) {
  const agg: Record<string, { with_asn: number; without_asn: number }> = {}
  for (const row of scm.uf_breakdown ?? []) {
    const r = UF_REGION[row.uf] ?? '—'
    const a = agg[r] ?? { with_asn: 0, without_asn: 0 }
    a.with_asn += row.with_asn
    a.without_asn += row.without_asn
    agg[r] = a
  }
  const data = REGION_ORDER.filter(r => agg[r]).map(r => ({ region: r, ...agg[r] }))
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="text-xs text-gray-500 mb-2 font-medium">Outorgas SCM por macrorregião</div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 12, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="region" tick={{ fontSize: 11 }} width={86} />
          <Tooltip formatter={(v: number, name: string) => [fmt(v), name === 'with_asn' ? 'Com ASN' : 'Sem ASN']} />
          <Bar dataKey="with_asn" stackId="a" fill={COLOR_WITH_ASN} />
          <Bar dataKey="without_asn" stackId="a" fill={COLOR_WITHOUT_ASN} radius={[0, 3, 3, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <VerDados dados={data as unknown as Record<string, unknown>[]} />
    </div>
  )
}

function AcessosPorRegiao({ acessos }: { acessos: SiciStats }) {
  const agg: Record<string, { pf: number; pj: number }> = {}
  for (const [uf, v] of Object.entries(acessos.por_uf ?? {})) {
    const r = UF_REGION[uf] ?? '—'
    const a = agg[r] ?? { pf: 0, pj: 0 }
    a.pf += v.pf
    a.pj += v.pj
    agg[r] = a
  }
  const data = REGION_ORDER.filter(r => agg[r]).map(r => ({ region: r, ...agg[r] }))
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="text-xs text-gray-500 mb-2 font-medium">Acessos declarados (SICI) por macrorregião</div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 12, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="region" tick={{ fontSize: 11 }} width={86} />
          <Tooltip formatter={(v: number, name: string) => [fmt(v), name === 'pf' ? 'B2C' : 'B2B']} />
          <Bar dataKey="pf" stackId="a" fill={COLOR_PF} />
          <Bar dataKey="pj" stackId="a" fill={COLOR_PJ} radius={[0, 3, 3, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <VerDados dados={data as unknown as Record<string, unknown>[]} />
    </div>
  )
}

// ── maiores operadoras: abas SICI × AS/APNIC ────────────────────────────────────

function MaioresOperadoras({ acessos }: { acessos: SiciStats }) {
  const [aba, setAba] = useState<'sici' | 'asn'>('sici')
  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="px-4 py-2 border-b border-gray-100 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">Maiores operadoras</h3>
        <div className="flex rounded-md border border-gray-200 overflow-hidden text-xs">
          <button onClick={() => setAba('sici')}
                  className={`px-2.5 py-1 ${aba === 'sici' ? 'bg-primario-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}>
            Por acessos declarados (SICI)
          </button>
          <button onClick={() => setAba('asn')}
                  className={`px-2.5 py-1 ${aba === 'asn' ? 'bg-primario-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}>
            Por usuários estimados (AS/APNIC)
          </button>
        </div>
      </div>
      {aba === 'sici' ? (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-400 bg-gray-50 border-b border-gray-100">
              <th className="px-4 py-1.5 w-8 text-right">#</th>
              <th className="px-4 py-1.5">Operadora</th>
              <th className="px-4 py-1.5 w-28 text-right">Acessos</th>
              <th className="px-4 py-1.5 w-24 text-right">B2B</th>
              <th className="px-4 py-1.5 w-24 text-right">Munic.</th>
              <th className="px-4 py-1.5 w-36">ASN</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {acessos.top_operadoras.map((o, i) => (
              <tr key={o.cnpj} className="hover:bg-gray-50">
                <td className="px-4 py-1 text-right text-gray-400 tabular-nums">{i + 1}</td>
                <td className="px-4 py-1">
                  <Link to={`/operadora/${o.cnpj}`} className="text-primario-600 hover:underline">
                    {o.empresa || o.razao_social}
                  </Link>
                </td>
                <td className="px-4 py-1 text-right tabular-nums">{fmt(o.acessos)}</td>
                <td className="px-4 py-1 text-right tabular-nums text-gray-500">{fmt(o.acessos_pj)}</td>
                <td className="px-4 py-1 text-right tabular-nums text-gray-500">{fmt(o.municipios)}</td>
                <td className="px-4 py-1">
                  {o.asns.length ? (
                    <div className="flex flex-wrap gap-1">
                      {o.asns.slice(0, 2).map(a => (
                        <Link key={a} to={`/asn/${a}`}
                              className="text-xs px-1.5 py-0.5 rounded bg-primario-50 text-primario-700 border border-primario-100">
                          AS{a}
                        </Link>
                      ))}
                      {o.asns.length > 2 && <span className="text-xs text-gray-400">+{o.asns.length - 2}</span>}
                    </div>
                  ) : <span className="text-xs text-gray-300">sem ASN</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-400 bg-gray-50 border-b border-gray-100">
              <th className="px-4 py-1.5 w-8 text-right">#</th>
              <th className="px-4 py-1.5 w-24">AS</th>
              <th className="px-4 py-1.5">Operadora</th>
              <th className="px-4 py-1.5 w-32 text-right">Usuários (APNIC)</th>
              <th className="px-4 py-1.5 w-32 text-right">Acessos (SICI)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {acessos.top_operadoras_por_asn.map((o, i) => (
              <tr key={o.cnpj} className="hover:bg-gray-50">
                <td className="px-4 py-1 text-right text-gray-400 tabular-nums">{i + 1}</td>
                <td className="px-4 py-1">
                  <Link to={`/asn/${o.asn}`} className="text-primario-600 hover:underline">AS{o.asn}</Link>
                </td>
                <td className="px-4 py-1">
                  <Link to={`/operadora/${o.cnpj}`} className="text-primario-600 hover:underline">{o.empresa}</Link>
                </td>
                <td className="px-4 py-1 text-right tabular-nums">{fmt(o.apnic_users)}</td>
                <td className="px-4 py-1 text-right tabular-nums text-gray-500">
                  {o.acessos_sici == null ? <span className="text-gray-300">sem declaração</span> : fmt(o.acessos_sici)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

// ── componente principal ─────────────────────────────────────────────────────────

export function BandaLargaFixaSection({ date }: { date?: string }) {
  const { data: scm, isError: scmError } = useQuery({
    queryKey: ['scm-stats', date],
    queryFn: () => fetchOutorgasStats('SCM', date),
    staleTime: 10 * 60 * 1000,
  })
  const { data: acessos } = useQuery({
    queryKey: ['acessos-stats', date],
    queryFn: () => fetchAcessosStats(date, 15),
    retry: false,
    staleTime: 10 * 60 * 1000,
  })

  if (scmError && !acessos) return null

  const licensed = scm?.unique_cnpjs ?? 0
  const withAsn = scm?.cnpjs_with_asn ?? 0
  const withoutAsn = Math.max(licensed - withAsn, 0)
  const autonomizacao = licensed > 0 ? (withAsn / licensed) * 100 : null
  const cobertura = acessos?.cobertura_declaracao

  const donut = [
    { name: 'Com ASN (autônomos)', value: withAsn, color: COLOR_WITH_ASN },
    { name: 'Sem ASN (só licença)', value: withoutAsn, color: COLOR_WITHOUT_ASN },
  ]

  const maxMuni = Math.max(1, ...(scm?.top_municipios ?? []).map(m => m.count))

  const serie: SiciSeriePoint[] = acessos
    ? acessos.serie_total.map(p => [p.mes, p.acessos, p.acessos, 0])
    : []
  const b2cPct = acessos?.total_acessos ? (100 * acessos.acessos_pf) / acessos.total_acessos : 0

  return (
    <section className="space-y-6">
      <h2 className="text-sm font-semibold uppercase tracking-widest border-t border-gray-100 pt-8"
          style={{ color: SECTION_COLOR }}>
        Banda larga fixa — SCM &amp; SICI (Anatel)
        {acessos?.mes_referencia && (
          <span className="text-xs font-normal normal-case tracking-normal text-gray-400 ml-2">
            mês de referência {acessos.mes_referencia}
          </span>
        )}
      </h2>

      {/* Licenciamento × autonomia × declaração */}
      {scm && (
        <div>
          <h3 className="text-base font-semibold text-gray-800 mb-1">Licença, autonomia e declaração</h3>
          <p className="text-xs text-gray-500 mb-4">
            Operadores com outorga de SCM, cruzados por CNPJ com os ASNs do Registro.br e com a
            declaração mensal de acessos ao SICI.
          </p>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 grid grid-cols-2 md:grid-cols-3 gap-3">
              <StatCard value={fmt(licensed)} label="Operadores licenciados" sub="CNPJs únicos com outorga SCM" accent={SECTION_COLOR} />
              <StatCard value={fmt(withAsn)} label="…com ASN" sub="autônomos no BGP" accent={COLOR_WITH_ASN} />
              <StatCard value={fmt(withoutAsn)} label="…sem ASN" sub="licenciados, ausentes do BGP" accent={COLOR_WITHOUT_ASN} />
              <StatCard value={fmtPct(autonomizacao)} label="Taxa de autonomização" sub="licenciados que viraram AS" />
              <StatCard value={fmt(cobertura?.informaram_sici)} label="…informaram no SICI"
                         sub={cobertura ? `${fmtPct(cobertura.pct_informaram_sici)} dos licenciados` : undefined} />
              <StatCard value={fmt(cobertura?.com_asn_informaram_sici)} label="…com ASN e informaram"
                         sub={cobertura ? `${fmtPct(cobertura.pct_com_asn_informaram_sici)} dos com ASN` : undefined} />
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
      )}

      {/* Acessos totais B2C/B2B */}
      {acessos && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard value={fmt(acessos.total_acessos)} label="Acessos declarados" accent={SECTION_COLOR} />
          <StatCard value={fmt(acessos.acessos_pf)} label="B2C" sub={`${b2cPct.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`} accent={COLOR_PF} />
          <StatCard value={fmt(acessos.acessos_pj)} label="B2B" sub={`${(100 - b2cPct).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`} accent={COLOR_PJ} />
          <StatCard value={fmt(acessos.municipios_atendidos)} label="Municípios atendidos" />
        </div>
      )}

      {/* Outorgas × acessos por UF e macrorregião */}
      {scm && acessos && (
        <div>
          <h3 className="text-base font-semibold text-gray-800 mb-1">Geografia: licenciamento × acessos</h3>
          <p className="text-xs text-gray-500 mb-4">
            Outorgas SCM (cadastro) ao lado dos acessos efetivamente declarados (uso), por UF e por macrorregião.
          </p>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <OutorgasPorUf scm={scm} />
            <AcessosPorUf acessos={acessos} />
            <OutorgasPorRegiao scm={scm} />
            <AcessosPorRegiao acessos={acessos} />
          </div>
        </div>
      )}

      {/* Evolução nacional */}
      {acessos && serie.length > 1 && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-1">
            Evolução nacional de acessos
            <span className="font-normal text-gray-400">{' '}· {serie[0][0]} a {serie[serie.length - 1][0]}</span>
          </h3>
          <AccessHistoryChart serie={serie} meses={serie.length} />
        </div>
      )}

      {/* Meio / tecnologia */}
      {acessos && (
        <div className="grid md:grid-cols-2 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Meio de acesso</h3>
            <Barras dados={acessos.por_meio} total={acessos.total_acessos} />
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Tecnologia</h3>
            <Barras dados={acessos.por_tecnologia} total={acessos.total_acessos} limite={8} />
          </div>
        </div>
      )}

      {/* Distribuição de velocidade contratada */}
      <SpeedDistributionChart distrib={acessos?.distrib_velocidade} />

      {/* Maiores operadoras — abas SICI × AS/APNIC */}
      {acessos && <MaioresOperadoras acessos={acessos} />}

      {/* Top municípios por outorga (regulatório) */}
      {scm && (
        <div>
          <h3 className="text-base font-semibold text-gray-800 mb-1">Municípios com mais outorgas SCM</h3>
          <p className="text-xs text-gray-500 mb-4">Top 15 municípios por número de outorgas — uma medida de interiorização.</p>
          <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-1.5">
            {(scm.top_municipios ?? []).map(m => (
              <div key={`${m.municipio}-${m.uf}`} className="flex items-center gap-2 text-xs">
                <span className="w-40 flex-shrink-0 truncate text-gray-700" title={`${m.municipio} / ${m.uf}`}>
                  {m.municipio} <span className="text-gray-400">/{m.uf}</span>
                </span>
                <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${(m.count / maxMuni) * 100}%`, background: SECTION_COLOR }} />
                </div>
                <span className="w-12 text-right tabular-nums text-gray-600">{fmt(m.count)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Divergências APNIC × SICI (SCM) */}
      <DivergenciasSCM date={date} />
    </section>
  )
}
