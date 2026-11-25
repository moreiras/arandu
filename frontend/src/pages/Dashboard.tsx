import { useState, useRef, useLayoutEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from '../components/layout/LinkDatado'
import { fetchHealth, fetchIXPs, fetchHilbertV4, fetchHilbertV6, fetchSnapshot, fetchOutorgasStats } from '../services/api'
import { useActiveDate } from '../hooks/useSnapshot'
import { HomeMap } from '../components/maps/HomeMap'
import { HilbertMap16, LAYER_META } from '../components/hilbert/HilbertMap16'
import type { LayerKey } from '../components/hilbert/HilbertMap16'
import { corLegivel } from '../lib/contraste'
import { HilbertMapV6 } from '../components/hilbert/HilbertMapV6'
import { SummaryTable } from '../components/tables/SummaryTable'
import { HeroKpis } from '../features/dashboard/Hero'
import { SnapshotHealth, StatsPanel } from '../features/dashboard/Estatisticas'

/** Visão geral (/visao-geral): mapa com KPIs, curvas de Hilbert e painel de estatísticas; os componentes ficam em `features/dashboard/`. */
// ─── Dashboard ───────────────────────────────────────────────────────────────

export function Dashboard() {
  const date = useActiveDate()
  const [activeLayer, setActiveLayer] = useState<LayerKey>('rir_br')
  const hilbert4Ref = useRef<HTMLDivElement>(null)
  const [hilbert4Width, setHilbert4Width] = useState(380)

  useLayoutEffect(() => {
    const el = hilbert4Ref.current
    if (!el) return
    const ro = new ResizeObserver(entries => {
      setHilbert4Width(Math.min(Math.floor(entries[0].contentRect.width), 380))
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const { data: health, isLoading: loadingHealth } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
  })

  const { data: ixpData } = useQuery({
    queryKey: ['ixps', date],
    queryFn: () => fetchIXPs(date ?? undefined),
    staleTime: Infinity, gcTime: Infinity,
  })

  const { data: hilbertData, isLoading: loadingHilbert } = useQuery({
    queryKey: ['hilbert-v4', date],
    queryFn: () => fetchHilbertV4(date ?? undefined),
    staleTime: Infinity, gcTime: Infinity,
  })

  const { data: hilbertV6Data, isLoading: loadingHilbertV6 } = useQuery({
    queryKey: ['hilbert-v6', date],
    queryFn: () => fetchHilbertV6(date ?? undefined),
    staleTime: Infinity, gcTime: Infinity,
  })

  const resolvedDate = date ?? health?.latest_snapshot ?? ixpData?.snapshot_date ?? ''
  const { data: snapshotDetails, isLoading: loadingSnapshot } = useQuery({
    queryKey: ['snapshot-details', resolvedDate],
    queryFn: () => fetchSnapshot(resolvedDate),
    enabled: !!resolvedDate,
    staleTime: Infinity, gcTime: Infinity,
  })

  const { data: scmStats } = useQuery({
    queryKey: ['scm-stats', resolvedDate],
    queryFn: () => fetchOutorgasStats('SCM', resolvedDate),
    enabled: !!resolvedDate,
    staleTime: Infinity, gcTime: Infinity,
  })

  const noData = !loadingHealth && health?.snapshots_available === 0

  if (noData) {
    return (
      <div className="max-w-xl mx-auto mt-16 text-center">
        <h1 className="text-xl font-semibold text-gray-800 mb-2">Nenhum snapshot disponível</h1>
        <p className="text-gray-500 text-sm mb-6">
          Ainda não há snapshot publicado neste site.
        </p>
        <Link to="/sobre" className="mt-4 inline-block text-sm text-primario-600 hover:underline">
          Ver documentação →
        </Link>
      </div>
    )
  }

  const snapshotDate = ixpData?.snapshot_date ?? date ?? health?.latest_snapshot ?? ''
  const summary = snapshotDetails?.summary ?? null

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-1.5">
        <div className="flex items-baseline gap-3 flex-wrap">
          <h1 className="text-titulo-1 text-gray-900">Visão geral</h1>
          {snapshotDate && (
            <span className="text-sm text-gray-500">
              Snapshot:{' '}
              <span className="font-mono">{snapshotDate}</span>
              {health && (
                <span className="ml-2 text-gray-400">
                  ({health.snapshots_available} snapshot
                  {health.snapshots_available !== 1 ? 's' : ''} disponíve
                  {health.snapshots_available !== 1 ? 'is' : 'l'})
                </span>
              )}
            </span>
          )}
        </div>
        <SnapshotHealth summary={summary} loading={loadingSnapshot} />
      </div>

      {/* KPIs: indicadores principais acima do mapa */}
      <HeroKpis summary={summary} scmTotal={scmStats?.total} />

      {/* Mapa de ASNs BR */}
      <HomeMap
        date={date ?? undefined}
        title="ASNs Brasileiros — Visibilidade na Tabela Global"
        ixpIndex={ixpData?.ixps}
        brAsnsInFt={summary?.global_table?.br_asns_in_ft}
      />

      {/* Stats panel detalhado */}
      <StatsPanel summary={summary} loading={loadingSnapshot} />

      {/* Espaço IPv6 — 6 blocos RIR */}
      <div>
        <h2 className="text-base font-semibold text-gray-800 mb-2">
          Espaço IPv6 — Curva de Hilbert (resolução /32)
        </h2>
        {loadingHilbertV6 ? (
          <div className="h-48 bg-gray-100 rounded-lg animate-pulse" />
        ) : (
          <HilbertMapV6 data={hilbertV6Data ?? null} blockWidth={220} />
        )}
      </div>

      {/* Espaço IPv4 — Curva de Hilbert */}
      <div>
        <h2 className="text-base font-semibold text-gray-800 mb-2">
          Espaço IPv4 — Curva de Hilbert (resolução /16)
        </h2>

        {/* Layer selector */}
        <div className="flex flex-wrap gap-1.5 mb-2">
          {(Object.keys(LAYER_META) as LayerKey[]).map((key) => {
            const meta = LAYER_META[key]
            const active = activeLayer === key
            return (
              <button
                key={key}
                type="button"
                aria-pressed={active}
                onClick={() => setActiveLayer(key)}
                className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                  active
                    ? 'text-white border-transparent'
                    : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400'
                }`}
                style={active ? { backgroundColor: corLegivel(meta.color), borderColor: corLegivel(meta.color) } : undefined}
                title={meta.description}
              >
                {meta.label}
              </button>
            )
          })}
        </div>

        {/* Legenda dinâmica */}
        <p
          className="text-xs text-gray-500 mb-3 leading-relaxed border-l-2 pl-2"
          style={{ borderColor: LAYER_META[activeLayer].color }}
        >
          {LAYER_META[activeLayer].legend}
        </p>

        <div ref={hilbert4Ref}>
          {loadingHilbert ? (
            <div className="bg-gray-100 rounded-lg animate-pulse" style={{ height: hilbert4Width }} />
          ) : (
            <HilbertMap16
              data={hilbertData ?? null}
              activeLayer={activeLayer}
              width={hilbert4Width}
              date={date ?? undefined}
            />
          )}
        </div>

        <p className="text-xs text-gray-400 mt-1.5">
          Cada célula = bloco /16. Intensidade proporcional ao número de /24s presentes.
          Clique em um bloco /8 destacado para ampliar.
        </p>
      </div>

      {/* Tabela de referência: agregado IX.br */}
      {summary?.global_table && summary?.ixp_aggregate && (
        <SummaryTable
          globalTable={summary.global_table}
          ixpAggregate={summary.ixp_aggregate}
          totalBrASNs={summary.total_asns_br}
          totalIxps={summary.ixps_ok + summary.ixps_partial + summary.ixps_missing}
        />
      )}

    </div>
  )
}
