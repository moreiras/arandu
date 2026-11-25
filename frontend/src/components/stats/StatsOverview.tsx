import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie,
} from 'recharts'
import type { RpkiSummary, SnapshotSummary } from '../../types/api'
import { fetchRpkiSummary, fetchMapAsns, fetchMapPrefixes } from '../../services/api'
import { UF_REGION, REGION_ORDER, REGION_COLOR } from '../../utils/regioes'
import { corLegivel } from '../../lib/contraste'
import { VerDados } from '../ui/VerDados'
import { AtribuicaoDbIp } from '../ui/AtribuicaoDbIp'
import { LinhaProveniencia } from '../ui/Kpi'
import type { Selo } from '../entidade/proveniencia'

// ── helpers ───────────────────────────────────────────────────────────────────

function fmtN(n: number | null | undefined): string {
  return n == null ? '—' : n.toLocaleString('pt-BR')
}
function fmtLarge(n: number | null | undefined): string {
  if (n == null) return '—'
  if (n >= 1e9) return `${(n / 1e9).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}B`
  if (n >= 1e6) return `${(n / 1e6).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}M`
  if (n >= 1e3) return `${(n / 1e3).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}k`
  return n.toLocaleString('pt-BR')
}
function fmtPct(n: number | null | undefined, dec = 1): string {
  return n == null ? '—' : `${n.toLocaleString('pt-BR', { minimumFractionDigits: dec, maximumFractionDigits: dec })}%`
}

function useCountUp(target: number | null | undefined, duration = 900): number {
  const [val, setVal] = useState(0)
  useEffect(() => {
    if (target == null) { setVal(0); return }
    // Movimento reduzido (WCAG 2.2, 2.3.3): o número final, sem animar.
    if (typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { setVal(target); return }
    let raf = 0
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      setVal(target * (1 - Math.pow(1 - t, 3)))
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, duration])
  return val
}

/** Número grande da faixa de abertura. Natureza, fonte e data de referência em texto sob o rótulo (PT-14), a mesma linha do `Kpi` comum. */
function Kpi({ target, label, sub, color, kind = 'large', selo, fonte, dataRef }: {
  target: number | null | undefined
  label: string
  sub?: string
  color: string
  kind?: 'large' | 'pct' | 'plain'
  selo: Selo
  fonte: string
  dataRef?: string | null
}) {
  const v = useCountUp(target)
  const display = target == null ? '—'
    : kind === 'pct' ? fmtPct(v)
    : kind === 'plain' ? Math.round(v).toLocaleString('pt-BR')
    : fmtLarge(Math.round(v))
  return (
    <div className="px-3 py-1">
      <div className="text-2xl sm:text-3xl font-extrabold tabular-nums leading-none" style={{ color: corLegivel(color) }}>{display}</div>
      <div className="text-xs sm:text-xs text-gray-700 mt-1 leading-tight font-medium">{label}</div>
      {sub && <div className="text-xs text-gray-400 leading-tight">{sub}</div>}
      <LinhaProveniencia selo={selo} fonte={fonte} dataRef={dataRef} className="mt-0.5 text-xs leading-tight text-gray-600" />
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

function Section({ title, color, children }: { title: string; color: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="text-sm font-semibold uppercase tracking-widest mb-3" style={{ color: corLegivel(color, 4.7) }}>{title}</h2>
      {children}
    </section>
  )
}

function CoverageBar({ label, pct, color }: { label: string; pct: number | null | undefined; color: string }) {
  const v = pct ?? 0
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>{label}</span>
        <span className="font-semibold tabular-nums" style={{ color: corLegivel(color) }}>{fmtPct(pct)}</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${Math.min(v, 100)}%`, background: color }} />
      </div>
    </div>
  )
}

// ── regiões ───────────────────────────────────────────────────────────────────

interface GeoFC { features: Array<{ properties: { uf?: string; ip_version?: number; prefix_count?: number } }> }

// ── RPKI ─────────────────────────────────────────────────────────────────────

function RpkiBar({ label, pct, color, sub }: { label: string; pct: number | null | undefined; color: string; sub?: string }) {
  const v = pct ?? 0
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>{label}</span>
        <span className="font-semibold tabular-nums" style={{ color: corLegivel(color) }}>{fmtPct(pct)}</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${Math.min(v, 100)}%`, background: color }} />
      </div>
      {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}

function RpkiSection({ rpki }: { rpki: RpkiSummary | null }) {
  const total = rpki?.br_asns_total ?? 0
  const withRoa = rpki?.br_asns_with_roa ?? 0
  const withAspa = rpki?.br_asns_with_aspa ?? 0
  const withAspaOfRoa = rpki?.br_asns_with_aspa_of_roa ?? 0
  const aspaOnlyCount = Math.max(withAspa - withAspaOfRoa, 0)
  const roaOnlyCount = Math.max(withRoa - withAspaOfRoa, 0)
  const noRoaCount = Math.max(total - withRoa, 0)
  const neitherCount = Math.max(total - withRoa - aspaOnlyCount, 0)

  const roaPct = total > 0 ? (withRoa / total) * 100 : null
  const aspaPct = total > 0 ? (withAspa / total) * 100 : null
  const v4Pct = rpki && rpki.br_space_v4_total_24 > 0
    ? (rpki.br_space_v4_roa_24 / rpki.br_space_v4_total_24) * 100 : null
  const v6Pct = rpki && rpki.br_space_v6_total_48 > 0
    ? (rpki.br_space_v6_roa_48 / rpki.br_space_v6_total_48) * 100 : null

  const donutData = [
    { name: 'ROA + ASPA', value: withAspaOfRoa, color: '#059669' },
    { name: 'Só ROA', value: roaOnlyCount, color: '#34d399' },
    { name: 'Só ASPA', value: aspaOnlyCount, color: '#0891b2' },
    { name: 'Nenhum', value: neitherCount, color: '#e5e7eb' },
  ]

  return (
    <Section title="RPKI — Segurança de Roteamento BGP" color="#b45309">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cards + barras */}
        <div className="lg:col-span-2 space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard
              value={fmtN(withRoa)}
              label="ASNs BR com ROA"
              sub={roaPct != null ? `${fmtPct(roaPct)} dos ASNs BR` : undefined}
              accent="#b45309"
            />
            <StatCard
              value={fmtPct(roaPct)}
              label="adoção de ROA"
              sub={`${fmtN(noRoaCount)} ainda sem ROA`}
            />
            <StatCard
              value={fmtN(withAspa)}
              label="ASNs BR com ASPA"
              sub={aspaPct != null ? `${fmtPct(aspaPct)} dos ASNs BR` : undefined}
            />
            <StatCard
              value={fmtPct(aspaPct)}
              label="adoção de ASPA"
              sub="entre todos os ASNs BR"
            />
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
            <RpkiBar
              label="Adoção de ROA — ASNs BR"
              pct={roaPct}
              color="#b45309"
              sub={`${fmtN(withRoa)} de ${fmtN(total)} ASNs publicaram ao menos 1 ROA`}
            />
            <RpkiBar
              label="Espaço IPv6 BR anunciado por ASes com ROA"
              pct={v6Pct}
              color="#f59e0b"
              sub={`${fmtLarge(rpki?.br_space_v6_roa_48)} de ${fmtLarge(rpki?.br_space_v6_total_48)} /48 equivalentes`}
            />
            <RpkiBar
              label="Espaço IPv4 BR anunciado por ASes com ROA"
              pct={v4Pct}
              color="#d97706"
              sub={`${fmtLarge(rpki?.br_space_v4_roa_24)} de ${fmtLarge(rpki?.br_space_v4_total_24)} /24 equivalentes`}
            />
            <RpkiBar
              label="Adoção de ASPA — ASNs BR"
              pct={aspaPct}
              color="#0891b2"
              sub={`${fmtN(withAspa)} de ${fmtN(total)} ASNs publicaram ao menos 1 ASPA`}
            />
          </div>
        </div>

        {/* Donut */}
        <div className="bg-white rounded-lg border border-gray-200 p-3 flex flex-col">
          <div className="text-xs text-gray-500 mb-1">Perfil RPKI dos ASNs BR</div>
          <div className="relative flex-1 flex items-center justify-center">
            <ResponsiveContainer width="100%" height={150}>
              <PieChart>
                <Pie
                  data={donutData}
                  dataKey="value"
                  innerRadius={46}
                  outerRadius={66}
                  paddingAngle={2}
                  startAngle={90}
                  endAngle={-270}
                >
                  {donutData.map((e) => <Cell key={e.name} fill={e.color} />)}
                </Pie>
                <Tooltip formatter={(v: number, name: string) => [fmtN(v), name]} />
              </PieChart>
            </ResponsiveContainer>
            <VerDados dados={donutData as unknown as Record<string, unknown>[]} />
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="text-center">
                <div className="text-xl font-bold tabular-nums" style={{ color: '#b45309' }}>{fmtPct(roaPct)}</div>
                <div className="text-xs text-gray-400 leading-tight">com ROA</div>
              </div>
            </div>
          </div>
          <div className="flex flex-col gap-1 mt-2">
            {donutData.map((e) => (
              <div key={e.name} className="flex items-center gap-2 text-xs text-gray-600">
                <span className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: e.color }} />
                <span className="flex-1">{e.name}</span>
                <span className="tabular-nums font-medium">{fmtN(e.value)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Section>
  )
}

// ── componente ────────────────────────────────────────────────────────────────

export function StatsOverview({ summary, date }: { summary: SnapshotSummary | null; date?: string }) {
  const { data: rpki } = useQuery({
    queryKey: ['rpki-summary', date],
    queryFn: () => fetchRpkiSummary(date),
    staleTime: Infinity,
    gcTime: Infinity,
  })

  const { data: asnGeo } = useQuery<GeoFC>({
    queryKey: ['map-asns', date],
    queryFn: () => fetchMapAsns(date) as Promise<GeoFC>,
    staleTime: Infinity, gcTime: Infinity,
  })
  const { data: prefixGeo } = useQuery<GeoFC>({
    queryKey: ['map-prefixes', date],
    queryFn: () => fetchMapPrefixes(date) as Promise<GeoFC>,
    staleTime: Infinity, gcTime: Infinity,
  })

  const s = summary
  const gt = s?.global_table
  const ref = date ?? s?.snapshot_date

  // Agregações por UF / região
  const { ufRows, regionRows } = useMemo(() => {
    const asByUf: Record<string, number> = {}
    for (const f of asnGeo?.features ?? []) {
      const uf = (f.properties.uf || '').toUpperCase()
      if (uf) asByUf[uf] = (asByUf[uf] || 0) + 1
    }
    const pfxByUf: Record<string, { v4: number; v6: number }> = {}
    for (const f of prefixGeo?.features ?? []) {
      const uf = (f.properties.uf || '').toUpperCase()
      if (!uf) continue
      const slot = pfxByUf[uf] ?? { v4: 0, v6: 0 }
      const n = f.properties.prefix_count ?? 1      // feição agregada por AS e município
      if (f.properties.ip_version === 6) slot.v6 += n; else slot.v4 += n
      pfxByUf[uf] = slot
    }
    const ufRows = Object.keys(asByUf)
      .map((uf) => ({
        uf, region: UF_REGION[uf] ?? '—',
        ases: asByUf[uf] ?? 0,
        v6: pfxByUf[uf]?.v6 ?? 0,   // D6: v6 antes de v4 (as colunas do "Ver dados" seguem a ordem das chaves)
        v4: pfxByUf[uf]?.v4 ?? 0,
      }))
      .sort((a, b) => b.ases - a.ases)

    const regAgg: Record<string, { ases: number; v6: number; v4: number }> = {}
    for (const r of ufRows) {
      const a = regAgg[r.region] ?? { ases: 0, v6: 0, v4: 0 }
      a.ases += r.ases; a.v4 += r.v4; a.v6 += r.v6
      regAgg[r.region] = a
    }
    const regionRows = REGION_ORDER
      .filter((r) => regAgg[r])
      .map((r) => ({ region: r, ...regAgg[r] }))
    return { ufRows, regionRows }
  }, [asnGeo, prefixGeo])

  const totalGeoAses = ufRows.reduce((acc, r) => acc + r.ases, 0)

  const ipv6Donut = useMemo(() => {
    const withV6 = s?.br_asns_with_ipv6 ?? 0
    const total = s?.total_asns_br ?? 0
    return [
      { name: 'Com IPv6', value: withV6, color: '#8b5cf6' },
      { name: 'Sem IPv6', value: Math.max(total - withV6, 0), color: '#e5e7eb' },
    ]
  }, [s])

  return (
    <div className="space-y-10">
      {/* Hero */}
      <div className="rounded-xl border border-gray-200 bg-gradient-to-br from-gray-50 to-white px-4 py-3">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-x-3 gap-y-2 divide-x divide-gray-200">
          <Kpi target={s?.total_asns_br} label="ASNs brasileiros" sub="alocados Registro.br" color="#2563eb" kind="plain" selo="fato" fonte="LACNIC (delegated)" dataRef={ref} />
          <Kpi target={s?.br_apnic_users_total} label="usuários BR estimados" sub="por medições do APNIC" color="#0891b2" selo="estimado" fonte="APNIC Labs" dataRef={ref} />
          <Kpi target={s?.br_ipv6_pct} kind="pct" label="ASNs BR com IPv6" sub={`${fmtN(s?.br_asns_with_ipv6)} ASNs`} color="#8b5cf6" selo="fato" fonte="Registro.br, tabela global e PTTs" dataRef={ref} />
          <Kpi target={s?.registro_br_prefixes_v6} kind="plain" label="prefixos IPv6 alocados" sub="Registro.br" color="#a78bfa" selo="fato" fonte="Registro.br" dataRef={ref} />
          <Kpi target={s?.registro_br_prefixes_v4} kind="plain" label="prefixos IPv4 alocados" sub="Registro.br" color="#0ea5e9" selo="fato" fonte="Registro.br" dataRef={ref} />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-x-3 gap-y-2 divide-x divide-gray-200 mt-2 pt-2 border-t border-gray-100">
          <Kpi target={s?.provedores_fixos_ativos} kind="plain" label="provedores fixos ativos" sub="SCM com ASN ou no SICI" color="#0ea5e9" selo="inferido" fonte="Anatel (SICI) e Registro.br" dataRef={ref} />
          <Kpi target={s?.assinantes_b2b_fixos} label="assinantes B2B fixos" sub="pessoa jurídica" color="#0369a1" selo="fato" fonte="Anatel (SICI)" dataRef={ref} />
          <Kpi target={s?.assinantes_b2c_fixos} label="assinantes B2C fixos" sub="pessoa física" color="#0891b2" selo="fato" fonte="Anatel (SICI)" dataRef={ref} />
          <Kpi target={s?.provedores_moveis_ativos} kind="plain" label="provedores móveis ativos" sub="SMP com ASN ou no SICI" color="#a78bfa" selo="inferido" fonte="Anatel (SICI) e Registro.br" dataRef={ref} />
          <Kpi target={s?.assinantes_b2b_moveis} label="assinantes B2B móveis" sub="pessoa jurídica" color="#7c3aed" selo="fato" fonte="Anatel (SICI)" dataRef={ref} />
          <Kpi target={s?.assinantes_b2c_moveis} label="assinantes B2C móveis" sub="pessoa física" color="#8b5cf6" selo="fato" fonte="Anatel (SICI)" dataRef={ref} />
        </div>
      </div>

      {/* ── AS ── */}
      <Section title="Sistemas Autônomos (AS)" color="#2563eb">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard value={fmtN(s?.total_asns_br)} label="ASNs BR alocados" accent="#2563eb" />
            <StatCard value={fmtN(gt?.br_asns_in_ft)} label="visíveis na tabela global"
              sub={gt?.br_asns_in_ft && s?.total_asns_br ? `${fmtPct((gt.br_asns_in_ft / s.total_asns_br) * 100)} dos alocados` : undefined} />
            <StatCard value={fmtN(s?.ixp_aggregate?.br_asns_origin_union_count)} label="originando no IX.br"
              sub={s?.ixp_aggregate?.br_asns_origin_union_count && gt?.br_asns_in_ft ? `${fmtPct((s.ixp_aggregate.br_asns_origin_union_count / gt.br_asns_in_ft) * 100)} dos visíveis` : undefined} />
            <StatCard value={fmtN(gt?.total_asns)} label="ASNs na tabela global" sub="todos os países" />
          </div>
          {/* Donut adoção IPv6 */}
          <div className="bg-white rounded-lg border border-gray-200 p-3 flex flex-col">
            <div className="text-xs text-gray-500 mb-1">Adoção de IPv6 (ASNs BR)</div>
            <div className="relative flex-1 flex items-center justify-center">
              <ResponsiveContainer width="100%" height={150}>
                <PieChart>
                  <Pie data={ipv6Donut} dataKey="value" innerRadius={46} outerRadius={66} paddingAngle={2} startAngle={90} endAngle={-270}>
                    {ipv6Donut.map((e) => <Cell key={e.name} fill={e.color} />)}
                  </Pie>
                  <Tooltip formatter={(v: number) => fmtN(v)} />
                </PieChart>
              </ResponsiveContainer>
              <VerDados dados={ipv6Donut as unknown as Record<string, unknown>[]} />
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <span className="text-2xl font-bold text-estimado-600 tabular-nums">{fmtPct(s?.br_ipv6_pct)}</span>
              </div>
            </div>
          </div>
        </div>
      </Section>

      {/* ── RPKI ── */}
      <RpkiSection rpki={rpki ?? null} />

      {/* ── IPv6 ── */}
      <Section title="Espaço IPv6 brasileiro" color="#8b5cf6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <StatCard value={fmtN(s?.registro_br_prefixes_v6)} label="prefixos alocados" sub="Registro.br" />
          <StatCard value={fmtLarge(s?.registro_br_declared_space_v6_48)} label="/48s alocados" accent="#8b5cf6" />
          <StatCard value={fmtPct(gt?.v6_br_coverage_pct)} label="cobertura alocado → FT" sub="% do espaço BR visível" />
          <StatCard value={fmtN(s?.br_ixp_origin_v6)} label="ASNs BR com IPv6 no IX.br" />
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4 max-w-md">
          <CoverageBar label="Espaço IPv6 BR alocado visível na tabela global" pct={gt?.v6_br_coverage_pct} color="#8b5cf6" />
        </div>
      </Section>

      {/* ── IPv4 ── */}
      <Section title="Espaço IPv4 brasileiro" color="#0ea5e9">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <StatCard value={fmtN(s?.registro_br_prefixes_v4)} label="prefixos alocados" sub="Registro.br" />
          <StatCard value={fmtLarge(s?.registro_br_declared_space_v4_24)} label="/24s alocados" accent="#0ea5e9" />
          <StatCard value={fmtPct(gt?.v4_br_coverage_pct)} label="cobertura alocado → FT" sub="% do espaço BR visível" />
          <StatCard value={fmtN(s?.br_ixp_origin_v4)} label="ASNs BR com IPv4 no IX.br" />
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4 max-w-md">
          <CoverageBar label="Espaço IPv4 BR alocado visível na tabela global" pct={gt?.v4_br_coverage_pct} color="#0ea5e9" />
        </div>
      </Section>

      {/* ── Registro.br ── */}
      <Section title="Alocação do Registro.br" color="#16a34a">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-4">
          <StatCard value={fmtN(s?.total_asns_br)} label="ASNs alocados" accent="#16a34a" />
          <StatCard value={fmtN(gt?.br_asns_in_ft)} label="ASNs visíveis na FT"
            sub={gt?.br_asns_in_ft && s?.total_asns_br ? fmtPct((gt.br_asns_in_ft / s.total_asns_br) * 100) : undefined} />
          <StatCard value={fmtN(s?.registro_br_prefixes_v6)} label="prefixos IPv6" />
          <StatCard value={fmtN(s?.registro_br_prefixes_v4)} label="prefixos IPv4" />
          <StatCard value={fmtLarge(s?.registro_br_declared_space_v6_48)} label="/48s IPv6 alocados" />
          <StatCard value={fmtLarge(s?.registro_br_declared_space_v4_24)} label="/24s IPv4 alocados" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-white rounded-lg border border-gray-200 p-4">
          <CoverageBar label="ASNs alocados visíveis na FT"
            pct={gt?.br_asns_in_ft && s?.total_asns_br ? (gt.br_asns_in_ft / s.total_asns_br) * 100 : null} color="#16a34a" />
          <CoverageBar label="Espaço IPv6 alocado visível na FT" pct={gt?.v6_br_coverage_pct} color="#8b5cf6" />
          <CoverageBar label="Espaço IPv4 alocado visível na FT" pct={gt?.v4_br_coverage_pct} color="#0ea5e9" />
        </div>
      </Section>

      {/* ── UF / macrorregião ── */}
      <Section title="Distribuição geográfica (UF e macrorregião)" color="#0d9488">
        <p className="text-xs text-gray-400 mb-3">
          Por localização da organização (CNPJ) e geolocalização dos prefixos. Cobre {fmtN(totalGeoAses)} ASNs BR geolocalizados.
        </p>
        <AtribuicaoDbIp className="-mt-2 mb-3" />

        {/* legenda de regiões */}
        <div className="flex flex-wrap gap-3 text-xs text-gray-500 mb-2">
          {REGION_ORDER.map((r) => (
            <span key={r} className="flex items-center gap-1">
              <span className="inline-block w-3 h-3 rounded-full" style={{ background: REGION_COLOR[r] }} />{r}
            </span>
          ))}
        </div>

        {/* ASNs por UF */}
        <div className="bg-white rounded-lg border border-gray-200 p-3 mb-4">
          <div className="text-xs text-gray-500 mb-2 font-medium">ASNs por Unidade Federativa</div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={ufRows} margin={{ top: 5, right: 12, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="uf" tick={{ fontSize: 11 }} interval={0} angle={-45} textAnchor="end" height={40} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number) => [fmtN(v), 'ASNs']} labelFormatter={(l) => `UF ${l}`} />
              <Bar dataKey="ases" radius={[3, 3, 0, 0]}>
                {ufRows.map((r) => <Cell key={r.uf} fill={REGION_COLOR[r.region] ?? '#94a3b8'} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <VerDados dados={ufRows as unknown as Record<string, unknown>[]} />
        </div>

        {/* Por macrorregião: cards + prefixos */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-3">
            <div className="text-xs text-gray-500 mb-2 font-medium">ASNs por macrorregião</div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={regionRows} layout="vertical" margin={{ top: 4, right: 16, left: 12, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="region" tick={{ fontSize: 11 }} width={86} />
                <Tooltip formatter={(v: number) => [fmtN(v), 'ASNs']} />
                <Bar dataKey="ases" radius={[0, 3, 3, 0]}>
                  {regionRows.map((r) => <Cell key={r.region} fill={REGION_COLOR[r.region]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <VerDados dados={regionRows as unknown as Record<string, unknown>[]} />
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-3">
            <div className="text-xs text-gray-500 mb-2 font-medium">Prefixos geolocalizados por macrorregião (IPv6 + IPv4)</div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={regionRows} layout="vertical" margin={{ top: 4, right: 16, left: 12, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="region" tick={{ fontSize: 11 }} width={86} />
                <Tooltip formatter={(v: number, k: string) => [fmtN(v), k === 'v4' ? 'IPv4' : 'IPv6']} />
                <Bar dataKey="v6" stackId="p" fill="#8b5cf6" radius={[0, 0, 0, 0]} />
                <Bar dataKey="v4" stackId="p" fill="#0ea5e9" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <VerDados dados={regionRows as unknown as Record<string, unknown>[]} />
            <div className="flex gap-3 text-xs text-gray-500 mt-1 justify-center">
              <span className="flex items-center gap-1"><span className="inline-block w-3 h-3 rounded-sm" style={{ background: '#8b5cf6' }} />IPv6</span>
              <span className="flex items-center gap-1"><span className="inline-block w-3 h-3 rounded-sm" style={{ background: '#0ea5e9' }} />IPv4</span>
            </div>
          </div>
        </div>
      </Section>
    </div>
  )
}
