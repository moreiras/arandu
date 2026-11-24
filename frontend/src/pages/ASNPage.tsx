// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useParams, Link, useSearchParams } from 'react-router-dom'
import { useMemo } from 'react'
import type { ASNDocument } from '../types/api'
import { useActiveDate } from '../hooks/useSnapshot'
import { useAsnPerfil, useFontes } from '../hooks/entidades'
import type { WeekSeries } from '../components/bgp/HourlyActivityChart'
import { EntityPage } from '../features/entidade/EntityPage'
import { EstadoDados, ehErroDeAcessoOuFalha } from '../components/ui/EstadoDados'
import { CabecalhoAsn } from '../features/asn/CabecalhoAsn'
import { FichaAsn } from '../features/asn/FichaAsn'
import type { AsnCtx } from '../features/asn/contexto'
import '../features/asn'

/**
 * Página de ASN: busca o perfil (documento, estabilidade BGP, caminhos e pares nos PTTs, numa chamada) e entrega ao registro de blocos
 * (`features/asn`). O conteúdo de cada seção mora no seu bloco; aqui só ficam os dados e o esqueleto.
 */
export function ASNPage() {
  const { asn } = useParams<{ asn: string }>()
  const [params] = useSearchParams()
  const versaoAntiga = params.get('versao') === '1'      // a página sem ficha e sem abas (`?versao=1`)
  const date = useActiveDate()
  const { fontes } = useFontes()

  // Perfil consolidado: documento, caminhos, pares nos PTTs diretos e estabilidade BGP do AS numa chamada (eram 4).
  const { data: perfil, isLoading, isError, error, refetch } = useAsnPerfil(asn)
  const { doc, referencias, pathsData, ixpPeerStats, estab, historico, seguranca, prontidao, routeServers, politicaRs, organizacao, abuso, bloqueios, radar, exposicao, transito, facilities, peering } = useMemo(() => {
    if (!perfil) return { doc: undefined, referencias: undefined, pathsData: undefined, ixpPeerStats: undefined, estab: undefined, historico: undefined, seguranca: undefined, prontidao: undefined, routeServers: undefined, politicaRs: undefined, organizacao: undefined, abuso: undefined, bloqueios: undefined, radar: undefined, exposicao: undefined, transito: undefined, facilities: undefined, peering: undefined }
    const { referencias, paths, ixp_peers, estabilidade, historico, seguranca, prontidao, route_servers, politica_rs, organizacao, abuso, bloqueios, radar, exposicao, transito, facilities, peering, ...resto } = perfil
    return { doc: resto as ASNDocument, referencias, pathsData: paths, ixpPeerStats: ixp_peers, estab: estabilidade ?? undefined, historico, seguranca, prontidao, routeServers: route_servers, politicaRs: politica_rs, organizacao, abuso, bloqueios, radar, exposicao, transito, facilities, peering }
  }, [perfil])
  const loadingPaths = false
  const asnStability = estab?.stability ?? undefined
  const stabilityData = useMemo(
    () => (estab ? { epppd_stats: estab.epppd_stats, hourly_global: { timestamps: estab.timestamps } } : undefined),
    [estab],
  )
  const asnWeeks = useMemo<WeekSeries[] | undefined>(
    () => estab?.weeks.map((w) => ({ date: w.date, timestamps: w.timestamps, series: w.series })),
    [estab],
  )
  const asnDiagnosis = estab?.diagnosis ?? undefined

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 bg-gray-100 rounded w-1/3" />
        <div className="grid grid-cols-2 gap-4">
          <div className="h-48 bg-gray-100 rounded" />
          <div className="h-48 bg-gray-100 rounded" />
        </div>
      </div>
    )
  }

  // Erro de acesso, de taxa ou de rede não é 404: a página não pode afirmar que o AS não existe.
  if (isError && ehErroDeAcessoOuFalha(error)) {
    return <EstadoDados variante="pagina" erro={error} oQue={`o perfil do AS${asn}`} aoTentarDeNovo={() => void refetch()} className="mt-8 max-w-2xl mx-auto" />
  }

  if (isError || !doc) {
    return (
      <div className="text-center mt-16">
        <div className="text-3xl mb-3">404</div>
        <p className="text-gray-500 text-sm">
          ASN <code className="font-mono">AS{asn}</code> não encontrado no snapshot {date ?? 'atual'}.
        </p>
        <Link to="/" className="mt-4 inline-block text-sm text-primario-600 hover:underline">
          ← Voltar ao início
        </Link>
      </div>
    )
  }

  const ctx: AsnCtx = {
    doc, date, historico, seguranca, prontidao, routeServers, politicaRs, organizacao, abuso, bloqueios, radar, exposicao, transito, facilities, peering, stabilityData, asnStability, asnWeeks, asnDiagnosis,
    ixpPaths: pathsData?.ixp_paths ?? {},
    // relação do documento principal + metadados dos nós vindos da rota de caminhos
    pathNodeMeta: { ...(doc.path_node_meta ?? {}), ...(pathsData?.path_node_meta ?? {}) },
    ixpMemberCodes: doc.ixp_member_codes ?? [],
    ixpPeerStats,
    carregandoCaminhos: loadingPaths,
  }

  return (
    <div className="space-y-8">
      <CabecalhoAsn doc={doc} />
      {!versaoAntiga && <FichaAsn doc={doc} referencias={referencias} />}
      <EntityPage entidade="asn" rotulo={`AS${doc.asn}${doc.name ? ` · ${doc.name}` : ''}`} dados={ctx} snapshot={doc.snapshot_date} fontes={fontes} espacamento="space-y-8" />
    </div>
  )
}
