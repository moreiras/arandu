import { useQuery } from '@tanstack/react-query'
import { fetchIXPs, fetchHealth, fetchSnapshot } from '../services/api'
import { useActiveDate } from '../hooks/useSnapshot'
import { CoberturaIxbr } from '../features/panorama/CoberturaIxbr'
import { StatsOverview } from '../components/stats/StatsOverview'
import { SegurancaSection } from '../components/stats/SegurancaSection'
import { BandaLargaFixaSection } from '../components/stats/BandaLargaFixaSection'
import { BandaLargaMovelSection } from '../components/stats/BandaLargaMovelSection'
import { TelefoniaFixaSection } from '../components/stats/TelefoniaFixaSection'
import { TvPorAssinaturaSection } from '../components/stats/TvPorAssinaturaSection'
import { EconomicGroupsTable } from '../components/stats/EconomicGroupsTable'

export function Estatisticas() {
  const date = useActiveDate()

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
  })

  const { data: ixpData } = useQuery({
    queryKey: ['ixps', date],
    queryFn: () => fetchIXPs(date ?? undefined),
    staleTime: Infinity, gcTime: Infinity,
  })

  const resolvedDate = date ?? health?.latest_snapshot ?? ixpData?.snapshot_date ?? ''
  const { data: snapshotDetails } = useQuery({
    queryKey: ['snapshot-details', resolvedDate],
    queryFn: () => fetchSnapshot(resolvedDate),
    enabled: !!resolvedDate,
    staleTime: Infinity, gcTime: Infinity,
  })



  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Estatísticas</h1>
        {ixpData?.snapshot_date && (
          <p className="text-sm text-gray-500 mt-1">
            Snapshot: <span className="font-mono">{ixpData.snapshot_date}</span>
          </p>
        )}
      </div>

      {/* Visão geral: AS, IPv6, IPv4, Registro.br, UF/macrorregião */}
      <StatsOverview summary={snapshotDetails?.summary ?? null} date={date ?? undefined} />

      {/* Grupos econômicos — CNPJs com múltiplos ASNs */}
      <EconomicGroupsTable date={date ?? undefined} />

      <h2 className="text-sm font-semibold uppercase tracking-widest text-aviso-600 border-t border-gray-100 pt-8">
        Cobertura no IX.br (por IXP)
      </h2>
      <CoberturaIxbr grupos={['ipv6', 'ipv4', 'asns']} />
      <SegurancaSection date={date ?? undefined} />

      {/* Últimas 4 seções da página: outorgas Anatel, na ordem SCM, SMP, STFC, SeAC */}
      <BandaLargaFixaSection date={date ?? undefined} />
      <BandaLargaMovelSection date={date ?? undefined} />
      <TelefoniaFixaSection date={date ?? undefined} />
      <TvPorAssinaturaSection date={date ?? undefined} />
    </div>
  )
}
