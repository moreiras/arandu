import { useQuery } from '@tanstack/react-query'
import { Link } from '../components/layout/LinkDatado'
import { fetchSnapshot, fetchRpkiSummary, fetchOutorgasStats } from '../services/api'
import { useActiveDate, useSnapshots } from '../hooks/useSnapshot'
import { useState } from 'react'
import { NotaRevisao } from '../components/ui/NotaRevisao'
import { CorrecoesNoChangelog } from '../components/ui/CorrecoesNoChangelog'
import { rotuloDe } from '../lib/universos'
import { ColetaSnapshot, IndicadoresSnapshot, type LinhaIndicador, type ManifestoSnapshot } from '../features/snapshots/ManifestoSnapshot'

function fmtN(n: number | null | undefined): string {
  if (n == null) return '—'
  return n.toLocaleString('pt-BR')
}
function fmtLarge(n: number | null | undefined): string {
  if (n == null) return '—'
  if (n >= 1e6) return `${(n / 1e6).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}M`
  return n.toLocaleString('pt-BR')
}

/** Cada indicador com a(s) fonte(s) do catálogo de que vem e a natureza do dado (IPv6 antes de IPv4). Os ids de fonte dão a data de `manifest.sources`. */
function linhasDoSnapshot(sm: Record<string, any>, rpki: number | undefined, scm: number | undefined): LinhaIndicador[] {
  return [
    { label: rotuloDe('asnsLacnic'), valor: fmtN(sm.total_asns_br), fontes: ['lacnic_delegated'], selo: 'fato' },
    { label: rotuloDe('asnsRegistroBr'), valor: fmtN(sm.registro_br_asns), fontes: ['registro_br'], selo: 'fato' },
    { label: rotuloDe('asnsVisiveis'), valor: fmtN(sm.global_table?.br_asns_in_ft), fontes: ['fulltable_routeviews'], selo: 'fato' },
    { label: 'ASN BR com prefixos IPv6 na full table', valor: fmtN(sm.br_asns_ft_v6), fontes: ['fulltable_routeviews'], selo: 'fato' },
    { label: 'ASN BR com prefixos IPv4 na full table', valor: fmtN(sm.br_asns_ft_v4), fontes: ['fulltable_routeviews'], selo: 'fato' },
    { label: rotuloDe('originadoresBr'), valor: fmtN(sm.ixp_aggregate?.br_asns_origin_union_count), fontes: ['lg_ixbr'], selo: 'fato' },
    { label: 'ASN BR com cadastro no PeeringDB', valor: fmtN(sm.br_asns_peeringdb), fontes: ['peeringdb_networks'], selo: 'fato' },
    { label: rotuloDe('usuariosPais'), valor: fmtLarge(sm.br_apnic_users_total), fontes: ['apnic_pop'], selo: 'estimado' },
    { label: 'ASN com objetos RPKI', valor: fmtN(rpki), fontes: ['rpki_collector'], selo: 'fato' },
    { label: 'ASNs brasileiros com coordenada da sede', valor: fmtN(sm.br_asns_geolocalized), fontes: ['cnpj_geo'], selo: 'inferido' },
    { label: 'Outorgas SCM', valor: fmtN(scm), fontes: ['anatel_outorgas'], selo: 'fato' },
  ]
}

export function Snapshots() {
  const date = useActiveDate()
  const [selected, setSelected] = useState<string | null>(null)

  const { data: list, isLoading, isError } = useSnapshots()

  const { data: detail } = useQuery({
    queryKey: ['snapshot-detail', selected],
    queryFn: () => fetchSnapshot(selected!),
    enabled: !!selected,
    staleTime: Infinity, gcTime: Infinity,
  })

  const { data: rpkiSummary } = useQuery({
    queryKey: ['rpki-summary', selected],
    queryFn: () => fetchRpkiSummary(selected!),
    enabled: !!selected,
    staleTime: Infinity, gcTime: Infinity,
  })

  const { data: scmStats } = useQuery({
    queryKey: ['scm-stats', selected],
    queryFn: () => fetchOutorgasStats('SCM', selected!),
    enabled: !!selected,
    staleTime: Infinity, gcTime: Infinity,
  })

  if (isLoading) {
    return (
      <div className="space-y-3 animate-pulse">
        <div className="h-8 bg-gray-100 rounded w-1/4" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-14 bg-gray-100 rounded" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Snapshots</h1>
        <p className="text-sm text-gray-500 mt-1">
          Histórico de snapshots publicados. <CorrecoesNoChangelog />
        </p>
      </div>

      <NotaRevisao />

      {isError ? (
        <div className="text-center py-16 text-perigo-500 text-sm">
          Erro ao carregar lista de snapshots. Verifique a conexão com a API.
        </div>
      ) : !list || list.count === 0 ? (
        <div className="text-center py-16">
          <p className="text-gray-500 text-sm">
            Nenhum snapshot publicado até agora.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Lista de snapshots */}
          <div className="md:col-span-1">
            <h2 className="text-sm font-medium text-gray-600 mb-2 uppercase tracking-wide">
              {list.count} snapshot{list.count !== 1 ? 's' : ''} disponíve{list.count !== 1 ? 'is' : 'l'}
            </h2>
            <div className="space-y-1">
              {[...list.snapshots].reverse().map((d) => (
                <button
                  key={d}
                  onClick={() => setSelected(d === selected ? null : d)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm font-mono transition-colors flex items-center justify-between ${
                    selected === d
                      ? 'bg-primario-100 text-primario-700 font-semibold'
                      : 'hover:bg-gray-100 text-gray-700'
                  }`}
                >
                  <span>{d}</span>
                  {d === list.latest && (
                    <span className="text-xs bg-ok-100 text-ok-600 rounded px-1.5 py-0.5 font-sans font-normal">
                      atual
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Detalhe do snapshot selecionado */}
          <div className="md:col-span-2">
            {!selected ? (
              <div className="flex items-center justify-center h-48 text-gray-400 text-sm border border-dashed border-gray-200 rounded-lg">
                Selecione um snapshot para ver os detalhes
              </div>
            ) : detail ? (
              <div className="bg-white border border-gray-200 rounded-lg p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-gray-900 font-mono">{selected}</h2>
                  <Link
                    to={`/?date=${selected}`}
                    className="text-sm text-primario-600 hover:underline"
                  >
                    Ver dashboard →
                  </Link>
                </div>

                {detail.summary ? (
                  <IndicadoresSnapshot sources={(detail.manifest as ManifestoSnapshot | null)?.sources} linhas={linhasDoSnapshot(detail.summary, rpkiSummary?.br_asns_with_roa, scmStats?.total)} />
                ) : (
                  <p className="text-sm text-gray-400">
                    Os totais deste snapshot não estão disponíveis.
                  </p>
                )}

                {detail.manifest && <ColetaSnapshot m={detail.manifest as ManifestoSnapshot} />}
              </div>
            ) : (
              <div className="h-48 bg-gray-50 rounded-lg animate-pulse" />
            )}
          </div>
        </div>
      )}
    </div>
  )
}
