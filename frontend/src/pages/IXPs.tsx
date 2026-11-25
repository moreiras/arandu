import { useSearchParams } from 'react-router-dom'
import { Link } from '../components/layout/LinkDatado'
import { RankingsSici } from './RankingsPage'
import { useQuery } from '@tanstack/react-query'
import { fetchHealth, fetchIXPs, fetchExternalIXPs, fetchSnapshot, fetchAllIXPEstimatedUsers } from '../services/api'
import { useActiveDate } from '../hooks/useSnapshot'
import { IXPTable } from '../components/tables/IXPTable'
import { ExternalIXPTable } from '../components/tables/ExternalIXPTable'
import { SummaryTable } from '../components/tables/SummaryTable'
import { IXPVoronoiMap } from '../components/maps/IXPVoronoiMap'
import type { IXPIndexEntry, ExternalIXPIndexEntry, SnapshotSummary } from '../types/api'
import { corLegivel } from '../lib/contraste'
import { CoberturaIxbr } from '../features/panorama/CoberturaIxbr'
import { NotaVariosTotais } from '../components/ui/NotaVariosTotais'
import { rotuloDe } from '../lib/universos'

// ─── number formatting helpers ───────────────────────────────────────────────

function fmtN(n: number | undefined | null): string {
  if (n == null) return '—'
  return n.toLocaleString('pt-BR')
}

function fmtLarge(n: number | undefined | null): string {
  if (n == null) return '—'
  if (n >= 1e9) return `${(n / 1e9).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}B`
  if (n >= 1e6) return `${(n / 1e6).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}M`
  return n.toLocaleString('pt-BR')
}

// ─── StatItem / StatGroup (mesmo padrão visual do Dashboard) ─────────────────

function StatItem({
  value,
  label,
  sub,
  loading,
  accent,
}: {
  value: string
  label: string
  sub?: string
  loading?: boolean
  accent?: string
}) {
  return (
    <div className="px-4 py-3 min-w-0">
      {loading ? (
        <div className="h-6 w-20 bg-gray-100 rounded animate-pulse mb-1" />
      ) : (
        <div
          className="text-xl font-bold text-gray-900 tabular-nums leading-tight"
          style={accent ? { color: accent } : undefined}
        >
          {value}
        </div>
      )}
      <div className="text-xs text-gray-500 mt-0.5 leading-tight">{label}</div>
      {sub && <div className="text-xs text-gray-400 leading-tight">{sub}</div>}
    </div>
  )
}

function StatGroup({
  title,
  color,
  children,
}: {
  title: string
  color: string
  children: React.ReactNode
}) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div
        className="px-4 py-1.5 border-b"
        style={{ backgroundColor: `${color}14`, borderColor: `${color}30` }}
      >
        {/* 5:1 contra o branco: o fundo é a mesma cor a 8%, que tira um pouco do contraste */}
        <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: corLegivel(color, 5) }}>
          {title}
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-none lg:grid-flow-col lg:auto-cols-fr divide-x divide-y lg:divide-y-0 divide-gray-100">
        {children}
      </div>
    </div>
  )
}

// ─── IXPsKpis ──────────────────────────────────────────────────────────────

const UNIVERSO_USUARIOS_PAIS = 'usuários estimados em ASNs brasileiros'

function IXPsKpis({
  ixps,
  externalIXPs,
  summary,
  loading,
}: {
  ixps: IXPIndexEntry[]
  externalIXPs: ExternalIXPIndexEntry[]
  summary: SnapshotSummary | null | undefined
  loading: boolean
}) {
  const totalIXPs = ixps.length + externalIXPs.length

  const ixbrWithBr = ixps.filter(
    (i) => (i.br_asns_origin_union_count ?? 0) > 0 || (i.br_asns_direct_union_count ?? 0) > 0
  ).length
  const externalWithBr = externalIXPs.filter((i) => (i.br_member_count ?? 0) > 0).length
  const totalWithBr = ixbrWithBr + externalWithBr

  return (
    <StatGroup title="IXPs" color="#d97706">
      <StatItem
        loading={loading}
        value={fmtN(totalIXPs)}
        label="PTTs do IX.br e IXPs de fora (PeeringDB)"
        sub={`${fmtN(ixps.length)} IX.br · ${fmtN(externalIXPs.length)} outros`}
        accent="#d97706"
      />
      <StatItem
        loading={loading}
        value={fmtN(totalWithBr)}
        label="IXPs com AS BR presente"
        sub={`${fmtN(ixbrWithBr)} IX.br · ${fmtN(externalWithBr)} outros`}
      />
      <StatItem
        loading={loading}
        value={fmtLarge(summary?.ixp_estimated_users_v4)}
        label={rotuloDe('usuariosIx')}
        sub={summary?.br_apnic_users_total != null ? `de ${fmtLarge(summary.br_apnic_users_total)} ${UNIVERSO_USUARIOS_PAIS} (APNIC); a soma por PTT, na tabela, não é este total` : 'a soma por PTT, na tabela, não é este total'}
        accent="#0891b2"
      />
      <StatItem
        loading={loading}
        value={fmtN(summary?.ixp_aggregate?.asn_direct_union_count)}
        label={rotuloDe('sessaoRs')}
        sub="união, todo o IX.br; não é peering bilateral"
      />
      <StatItem
        loading={loading}
        value={fmtN(summary?.ixp_aggregate?.asn_origin_union_count)}
        label={rotuloDe('originadores')}
        sub="união, todo o IX.br; inclui o que chega por trânsito"
        accent="#16a34a"
      />
      <StatItem
        loading={loading}
        value={fmtN(summary?.external_ixps_br_asn_union_count)}
        label={rotuloDe('externosBr')}
        sub="união por ASN (PeeringDB)"
        accent="#8b5cf6"
      />
    </StatGroup>
  )
}

export function IXPs() {
  const [params] = useSearchParams()
  if (params.get('visao') === 'route-servers') {
    return (
      <div className="space-y-6">
        <nav aria-label="Visão dos PTTs" className="flex gap-1 border-b border-gray-200">
          <Link to="/ixps" className="px-4 py-2 text-sm -mb-px border-b-2 border-transparent text-gray-500 hover:text-gray-800">PTTs</Link>
          <Link to="/ixps?visao=route-servers" aria-current="page" className="px-4 py-2 text-sm -mb-px border-b-2 border-primario-600 text-primario-700 font-medium">Route servers</Link>
        </nav>
        <h1 className="text-titulo-1 text-gray-900">Route servers do IX.br</h1>
        <RankingsSici abaFixa="route-servers" />
      </div>
    )
  }
  return <IXPsLista />
}

function IXPsLista() {
  const date = useActiveDate()

  const { data: health } = useQuery({ queryKey: ['health'], queryFn: fetchHealth })

  const { data: ixpData, isLoading: loadingIXPs } = useQuery({
    queryKey: ['ixps', date],
    queryFn: () => fetchIXPs(date ?? undefined),
    staleTime: Infinity, gcTime: Infinity,
  })

  const { data: externalData, isLoading: loadingExternal } = useQuery({
    queryKey: ['external-ixps', date],
    queryFn: () => fetchExternalIXPs(date ?? undefined),
    staleTime: Infinity, gcTime: Infinity,
  })

  const resolvedDate = date ?? health?.latest_snapshot ?? ixpData?.snapshot_date ?? ''
  const { data: snapshotDetails } = useQuery({
    queryKey: ['snapshot-details', resolvedDate],
    queryFn: () => fetchSnapshot(resolvedDate),
    enabled: !!resolvedDate,
    staleTime: Infinity, gcTime: Infinity,
  })

  const { data: estUsersData } = useQuery({
    queryKey: ['ixps-est-users', date],
    queryFn: () => fetchAllIXPEstimatedUsers(date ?? undefined),
    staleTime: Infinity, gcTime: Infinity,
  })

  const ixps = ixpData?.ixps ?? []
  const externalIXPs = externalData?.ixps ?? []
  const summary = snapshotDetails?.summary ?? null

  return (
    <div className="space-y-8">
      <h1 className="text-titulo-1 text-gray-900">IXPs</h1>

      <NotaVariosTotais>Os PTTs do IX.br e os IXPs de fora são listas diferentes e não se somam num número só. Um ASN pode ter sessão com o route server, constar do cadastro de participantes ou apenas originar prefixo visto no PTT: são três conjuntos de tamanhos muito diferentes. A soma dos usuários estimados por PTT conta o mesmo usuário em cada PTT onde o ASN aparece.</NotaVariosTotais>

      <IXPsKpis
        ixps={ixps}
        externalIXPs={externalIXPs}
        summary={summary}
        loading={loadingIXPs || loadingExternal}
      />

      <div className="space-y-2">
        <div className="flex items-baseline justify-between gap-2">
          <h2 className="text-base font-semibold text-gray-800">
            Áreas de influência dos PTTs
          </h2>
          <span className="text-xs text-gray-400">
            PTT mais próximo (distância geográfica) · grade 0,12°
          </span>
        </div>
        {loadingIXPs ? (
          <div className="h-[460px] bg-gray-100 rounded-lg animate-pulse" />
        ) : (
          <IXPVoronoiMap ixps={ixps} date={date ?? undefined} />
        )}
      </div>

      {summary?.global_table && summary?.ixp_aggregate && (
        <SummaryTable
          globalTable={summary.global_table}
          ixpAggregate={summary.ixp_aggregate}
          totalBrASNs={summary.total_asns_br}
        />
      )}

      <div className="space-y-2">
        <h2 className="text-base font-semibold text-gray-800">
          IXPs do IX.br ({ixps.length})
        </h2>
        {loadingIXPs ? (
          <div className="h-32 bg-gray-100 rounded-lg animate-pulse" />
        ) : ixps.length === 0 ? (
          <p className="text-gray-400 text-sm">Nenhum IXP disponível no snapshot atual.</p>
        ) : (
          <IXPTable
            ixps={ixps}
            totalBrASNs={summary?.total_asns_br}
            totalGlobalASNs={summary?.global_table?.total_asns}
            estUsers={estUsersData?.ixps}
            interligacao={ixpData?.interligacao}
            dataSnapshot={ixpData?.snapshot_date}
          />
        )}
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <h2 className="text-base font-semibold text-gray-800">
            Outros IXPs{externalIXPs.length > 0 ? ` (${externalIXPs.length})` : ''}
          </h2>
          <span className="text-xs px-1.5 py-0.5 rounded bg-aviso-100 text-aviso-700 border border-aviso-200">
            dados: PeeringDB
          </span>
        </div>
        {loadingExternal ? (
          <div className="h-32 bg-gray-100 rounded-lg animate-pulse" />
        ) : externalIXPs.length === 0 ? (
          <p className="text-gray-400 text-sm">Dados de outros IXPs não disponíveis neste snapshot.</p>
        ) : (
          <ExternalIXPTable ixps={externalIXPs} />
        )}
      </div>

      {/* O detalhe por PTT mora aqui; o Panorama traz o agregado (e os mesmos gráficos por família). */}
      <section className="space-y-2" aria-label="Cobertura por PTT">
        <h2 className="text-base font-semibold text-gray-800">Cobertura por PTT do IX.br</h2>
        <p className="text-sm text-gray-600">Quanto do espaço de endereços (IPv6 e IPv4) e quantos ASes cada PTT enxerga.</p>
        <CoberturaIxbr grupos={['ipv6', 'ipv4', 'asns']} />
      </section>
    </div>
  )
}
