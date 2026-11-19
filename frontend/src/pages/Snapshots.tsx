import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchSnapshots, fetchSnapshot, fetchRpkiSummary, fetchOutorgasStats } from '../services/api'
import { useActiveDate } from '../hooks/useSnapshot'
import { useState } from 'react'

function fmtN(n: number | null | undefined): string {
  if (n == null) return '—'
  return n.toLocaleString('pt-BR')
}
function fmtLarge(n: number | null | undefined): string {
  if (n == null) return '—'
  if (n >= 1e6) return `${(n / 1e6).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}M`
  return n.toLocaleString('pt-BR')
}

export function Snapshots() {
  const date = useActiveDate()
  const [selected, setSelected] = useState<string | null>(null)

  const { data: list, isLoading, isError } = useQuery({
    queryKey: ['snapshots'],
    queryFn: fetchSnapshots,
    staleTime: Infinity, gcTime: Infinity,
  })

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
          Histórico de snapshots publicados. Cada snapshot é imutável após publicação.
        </p>
      </div>

      {isError ? (
        <div className="text-center py-16 text-perigo-500 text-sm">
          Erro ao carregar lista de snapshots. Verifique a conexão com a API.
        </div>
      ) : !list || list.count === 0 ? (
        <div className="text-center py-16">
          <div className="text-3xl mb-3">📭</div>
          <p className="text-gray-500 text-sm">
            Nenhum snapshot publicado. Execute o pipeline para gerar o primeiro snapshot.
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
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    {[
                      { label: 'ASN alocados pelo Registro.br', value: fmtN(detail.summary.total_asns_br) },
                      { label: 'ASN BR na full table', value: fmtN(detail.summary.global_table?.br_asns_in_ft) },
                      { label: 'ASN BR no IX.br', value: fmtN(detail.summary.ixp_aggregate?.br_asns_origin_union_count) },
                      { label: 'ASN BR com cadastro no PeeringDB', value: fmtN(detail.summary.br_asns_peeringdb) },
                      { label: 'Usuários BR estimados (APNIC)', value: fmtLarge(detail.summary.br_apnic_users_total) },
                      { label: 'ASN com objetos RPKI', value: fmtN(rpkiSummary?.br_asns_with_roa) },
                      { label: 'ASN BR geolocalizados', value: fmtN(detail.summary.br_asns_geolocalized) },
                      { label: 'Outorgas SCM', value: fmtN(scmStats?.total) },
                    ].map((row) => (
                      <div key={row.label} className="bg-gray-50 rounded p-2">
                        <div className="text-xs text-gray-500">{row.label}</div>
                        <div className="font-semibold text-gray-800">{row.value}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-400">
                    summary.json não disponível neste snapshot (pipeline incompleto).
                  </p>
                )}

                {detail.manifest && (
                  <div className="text-xs text-gray-400 font-mono border-t border-gray-100 pt-3">
                    Gerado em: {String(detail.manifest.generated_at ?? '—')}
                  </div>
                )}
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
