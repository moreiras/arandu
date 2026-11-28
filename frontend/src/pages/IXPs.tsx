import { useSearchParams } from 'react-router-dom'
import { Link } from '../components/layout/LinkDatado'
import { RankingsSici } from './RankingsPage'
import { useQuery } from '@tanstack/react-query'
import { fetchHealth, fetchIXPs, fetchExternalIXPs, fetchSnapshot, fetchAllIXPEstimatedUsers } from '../services/api'
import { useActiveDate } from '../hooks/useSnapshot'
import { IXPTable } from '../components/tables/IXPTable'
import { ExternalIXPTable } from '../components/tables/ExternalIXPTable'
import { SummaryTable } from '../components/tables/SummaryTable'
import { AreaInfluenciaAbas } from '../features/ptt/AreaInfluenciaAbas'
import type { IXPIndexEntry, ExternalIXPIndexEntry, SnapshotSummary } from '../types/api'
import { CoberturaIxbr } from '../features/panorama/CoberturaIxbr'
import { rotuloDe } from '../lib/universos'
import { ApresentacaoRecolhida, GrupoFontes } from '../components/ui/FontesEDatas'
import { Kpi } from '../components/ui/Kpi'
import { ResumoEmTexto } from '../components/ui/ResumoEmTexto'
import { compacto } from '../lib/sintese'
import { CitarDado } from '../components/entidade/CitarDado'
import { useFontes } from '../hooks/entidades'
import { REGRAS_SINTESE_LISTA_PTTS, sinteseListaPtts } from '../features/ptt/sinteseListaPtts'

// ─── number formatting helpers ───────────────────────────────────────────────

function fmtN(n: number | undefined | null): string {
  if (n == null) return '—'
  return n.toLocaleString('pt-BR')
}

function vN(n: number | undefined | null): string | null {
  return n == null ? null : fmtN(n)
}

const UNIVERSO_USUARIOS_PAIS = 'usuários estimados em ASNs brasileiros'

function IXPsKpis({
  ixps,
  externalIXPs,
  summary,
  loading,
  snapshot,
}: {
  ixps: IXPIndexEntry[]
  externalIXPs: ExternalIXPIndexEntry[]
  summary: SnapshotSummary | null | undefined
  loading: boolean
  snapshot?: string | null
}) {
  const ixbrWithBr = ixps.filter(
    (i) => (i.br_asns_origin_union_count ?? 0) > 0 || (i.br_asns_direct_union_count ?? 0) > 0
  ).length
  const externalWithBr = externalIXPs.filter((i) => (i.br_member_count ?? 0) > 0).length
  const totalWithBr = ixbrWithBr + externalWithBr

  const sub = (a: number, b: number, na: string, nb: string) => `${fmtN(a)} ${na} · ${fmtN(b)} ${nb}`
  if (loading) return <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6" aria-hidden="true">{[0, 1, 2, 3, 4, 5].map((i) => <div key={i} className="h-20 animate-pulse rounded-lg bg-gray-100" />)}</div>
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
      <Kpi tom="primario" selo="fato" fonte="IX.br e PeeringDB" dataRef={snapshot}
        rotulo="PTTs do IX.br" valor={fmtN(ixps.length)} referencia={`${fmtN(externalIXPs.length)} IXPs de fora, no PeeringDB, listados à parte e não somados`} />
      <Kpi selo="fato" fonte="looking glasses do IX.br e PeeringDB" dataRef={snapshot}
        rotulo="IXPs com AS BR presente" valor={fmtN(totalWithBr)} referencia={sub(ixbrWithBr, externalWithBr, 'IX.br', 'outros')} />
      <Kpi selo="estimado" fonte="APNIC Labs e looking glasses do IX.br" dataRef={snapshot}
        rotulo={rotuloDe('usuariosIx')} valor={summary?.ixp_estimated_users_v4 != null ? compacto(summary.ixp_estimated_users_v4) : null}
        referencia={summary?.br_apnic_users_total != null ? `de ${compacto(summary.br_apnic_users_total)} ${UNIVERSO_USUARIOS_PAIS} (APNIC); a soma por PTT, na tabela, não é este total` : 'a soma por PTT, na tabela, não é este total'} />
      <Kpi selo="fato" fonte="looking glasses do IX.br" dataRef={snapshot}
        rotulo={rotuloDe('sessaoRs')} valor={vN(summary?.ixp_aggregate?.asn_direct_union_count)} referencia="união, todo o IX.br; não é peering bilateral" />
      <Kpi selo="fato" fonte="looking glasses do IX.br" dataRef={snapshot}
        rotulo={rotuloDe('originadores')} valor={vN(summary?.ixp_aggregate?.asn_origin_union_count)} referencia="união, todo o IX.br; inclui o que chega por trânsito" />
      <Kpi selo="fato" fonte="PeeringDB (autodeclarado)" dataRef={snapshot}
        rotulo={rotuloDe('externosBr')} valor={vN(summary?.external_ixps_br_asn_union_count)} referencia="união por ASN (PeeringDB)" />
    </div>
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
  // IXPs do PeeringDB divididos pelo país do cadastro (PT-22 / ixps 5.5): os do Brasil e os de fora são universos diferentes para quem lê a tabela
  const externosNoBrasil = externalIXPs.filter((i) => i.country === 'BR')
  const externosNoExterior = externalIXPs.filter((i) => i.country !== 'BR')
  const { fontes } = useFontes()

  const snap = summary?.snapshot_date ?? resolvedDate
  return (
    <ApresentacaoRecolhida>
    <div className="space-y-8">
      <h1 className="text-titulo-1 text-gray-900">IXPs</h1>


      <GrupoFontes snapshot={snap}>
        <IXPsKpis
          ixps={ixps}
          externalIXPs={externalIXPs}
          summary={summary}
          loading={loadingIXPs || loadingExternal}
          snapshot={snap}
        />
        <ResumoEmTexto frases={sinteseListaPtts(ixps, externalIXPs, summary, snap)} snapshot={snap} regras={REGRAS_SINTESE_LISTA_PTTS}
          notaComoLer="O IX.br e os IXPs de fora são listas diferentes e não se somam." />
      </GrupoFontes>

      <details className="text-sm text-gray-700" data-testid="como-citar-ixps">
        <summary className="cursor-pointer select-none text-xs font-medium text-primario-700 hover:text-primario-900">Como citar esta página</summary>
        <div className="mt-1 max-w-xl rounded border border-gray-200 bg-white p-2 shadow-sm">
          <p>Os números desta página são do snapshot de {snap || 'data não carregada'}; a lista dos PTTs do IX.br está em <code>/api/v1/ixps?date={snap}</code> e a dos IXPs de fora em <code>/api/v1/external-ixps?date={snap}</code>.</p>
          <CitarDado pedido={{ entidade: 'Lista de PTTs do IX.br e de IXPs do PeeringDB', bloco: 'IXPs' }} fontes={['lg_ixbr', 'ixbr_api', 'peeringdb_ixps']} fontesEntradas={fontes} snapshot={snap} />
        </div>
      </details>

      <div className="space-y-2">
        <h2 className="text-base font-semibold text-gray-800">
          Áreas de influência dos PTTs
        </h2>
        {loadingIXPs ? (
          <div className="h-[460px] bg-gray-100 rounded-lg animate-pulse" />
        ) : (
          <AreaInfluenciaAbas ixps={ixps} date={date ?? undefined} />
        )}
      </div>

      {summary?.global_table && summary?.ixp_aggregate && (
        <SummaryTable
          globalTable={summary.global_table}
          ixpAggregate={summary.ixp_aggregate}
          totalBrASNs={summary.total_asns_br}
          totalIxps={summary.ixps_ok + summary.ixps_partial + summary.ixps_missing}
        />
      )}

      <div className="space-y-2">
        <h2 className="text-base font-semibold text-gray-800">
          IXPs do IX.br ({ixps.length})
        </h2>
        {loadingIXPs ? (
          <div className="h-32 bg-gray-100 rounded-lg animate-pulse" />
        ) : ixps.length === 0 ? (
          <p className="text-gray-600 text-sm">Nenhum IXP disponível no snapshot atual.</p>
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

      <div className="space-y-4">
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
          <p className="text-gray-600 text-sm">Dados de outros IXPs não disponíveis neste snapshot.</p>
        ) : (
          <>
            {externosNoBrasil.length > 0 && (
              <div className="space-y-2" data-testid="externos-no-brasil">
                <h3 className="text-sm font-semibold text-gray-700">No Brasil ({externosNoBrasil.length})</h3>
                <ExternalIXPTable ixps={externosNoBrasil} />
              </div>
            )}
            {externosNoExterior.length > 0 && (
              <div className="space-y-2" data-testid="externos-no-exterior">
                <h3 className="text-sm font-semibold text-gray-700">No exterior ({externosNoExterior.length})</h3>
                <ExternalIXPTable ixps={externosNoExterior} />
              </div>
            )}
          </>
        )}
      </div>

      {/* O detalhe por PTT mora aqui; o Panorama traz o agregado (e os mesmos gráficos por família). */}
      <section className="space-y-2" aria-label="Cobertura por PTT">
        <h2 className="text-base font-semibold text-gray-800">Cobertura por PTT do IX.br</h2>
        <p className="text-sm text-gray-600">Quanto do espaço de endereços (IPv6 e IPv4) e quantos ASes cada PTT enxerga.</p>
        <CoberturaIxbr grupos={['ipv6', 'ipv4', 'asns']} />
      </section>
    </div>
    </ApresentacaoRecolhida>
  )
}
