// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useParams, Link, useLocation, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { fetchIXPPeers } from '../services/api'
import { useActiveDate } from '../hooks/useSnapshot'
import { useFontes, useIxpPerfil } from '../hooks/entidades'
import { coletaDaFamilia, isIXPAfiFull, type IXPAfiFull, type IXPDocument } from '../types/api'
import { EntityPage } from '../features/entidade/EntityPage'
import { CabecalhoPtt } from '../features/ptt/CabecalhoPtt'
import { getIndexAfi } from '../features/ptt/ui'
import type { PttCtx } from '../features/ptt/contexto'
import '../features/ptt'

/** Página de PTT: busca o documento e os extras e entrega ao registro de blocos (`features/ptt`); o conteúdo de cada seção mora no seu bloco. */
export function IXPPage() {
  const { code } = useParams<{ code: string }>()
  const date = useActiveDate()
  const [params] = useSearchParams()
  const { hash } = useLocation()
  // as listas de pares (por família de IP) só são buscadas quando a aba Participantes abre; `?versao=1` mostra tudo, sem abas
  const precisaPares = params.get('versao') === '1' || params.get('aba') === 'participantes' || /^#bloco-(peers|membros)/.test(hash)
  const { fontes } = useFontes()
  const [selectedPeerV4, setSelectedPeerV4] = useState<number | null>(null)
  const [selectedPeerV6, setSelectedPeerV6] = useState<number | null>(null)

  // Perfil consolidado: documento, membros (com nomes), usuários estimados, potencial, assinantes, linha do índice e totais do
  // snapshot numa chamada (eram 7). Só os pares v6 e v4 ficam à parte (listas longas).
  const { data: perfil, isLoading, isError } = useIxpPerfil(code)
  const { ixp, ixpEntry, estUsers, potential, assinantes, membersData, totais, historico, routeServers, rejeicoes, facilities, portas } = useMemo(() => {
    if (!perfil) return { ixp: undefined, ixpEntry: undefined, estUsers: undefined, potential: undefined, assinantes: undefined, membersData: undefined, totais: undefined, historico: undefined, routeServers: undefined, rejeicoes: undefined, facilities: undefined, portas: undefined }
    const { membros, usuarios_estimados, potencial, assinantes, indice, totais, historico, route_servers, rejeicoes, facilities, portas, ...doc } = perfil
    return { ixp: doc as IXPDocument, ixpEntry: indice ?? undefined, estUsers: usuarios_estimados, potential: potencial ?? undefined,
      assinantes: assinantes ?? undefined, membersData: membros, totais, historico, routeServers: route_servers, rejeicoes, facilities, portas }
  }, [perfil])
  const loadingMembers = false

  const v4 = ixp && isIXPAfiFull(ixp.v4) ? ixp.v4 : null
  const v6 = ixp && isIXPAfiFull(ixp.v6) ? ixp.v6 : null

  const v4idx = ixpEntry ? getIndexAfi(ixpEntry.v4) : null
  const v6idx = ixpEntry ? getIndexAfi(ixpEntry.v6) : null

  const totalBrASNs = totais?.total_asns_br ?? null
  const totalGlobalASNs = totais?.total_asns_global ?? null


  const { data: peersV4, isLoading: loadingPeersV4 } = useQuery({
    queryKey: ['ixp-peers-v4', code, date],
    queryFn: () => fetchIXPPeers(code!, 'v4', date ?? undefined),
    enabled: !!code && !!v4 && precisaPares,
    staleTime: Infinity, gcTime: Infinity,
  })

  const { data: peersV6, isLoading: loadingPeersV6 } = useQuery({
    queryKey: ['ixp-peers-v6', code, date],
    queryFn: () => fetchIXPPeers(code!, 'v6', date ?? undefined),
    enabled: !!code && !!v6 && precisaPares,
    staleTime: Infinity, gcTime: Infinity,
  })

  // Merge: doc slim (estatísticas) + listas de membros quando chegarem
  const mergedV4 = useMemo((): IXPAfiFull | null => {
    if (!v4) return null
    return { ...v4, ...(membersData?.v4 ?? {}) }
  }, [v4, membersData])

  const mergedV6 = useMemo((): IXPAfiFull | null => {
    if (!v6) return null
    return { ...v6, ...(membersData?.v6 ?? {}) }
  }, [v6, membersData])

  // Membros registrados sem peering direto (v4 ou v6) — usa dados merged
  const membersWithoutDirect = useMemo(() => {
    const members = ixp?.asn_members ?? []
    if (members.length === 0) return []
    const direct = new Set([
      ...(mergedV4?.asn_direct ?? []),
      ...(mergedV6?.asn_direct ?? []),
    ])
    return members.filter(asn => !direct.has(asn))
  }, [ixp?.asn_members, mergedV4, mergedV6])

  // Nomes vêm no perfil (membros.nomes, inclusive dos membros cadastrados sem par direto)
  const nameMap = useMemo<Record<string, string>>(
    () => Object.fromEntries(Object.entries(membersData?.nomes ?? {}).map(([asn, n]) => [asn, n.name])),
    [membersData],
  )

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 bg-gray-100 rounded w-1/3" />
        <div className="grid grid-cols-6 gap-2">
          {[1, 2, 3, 4, 5, 6].map((i) => <div key={i} className="h-16 bg-gray-100 rounded" />)}
        </div>
        <div className="h-64 bg-gray-100 rounded" />
      </div>
    )
  }

  if (isError || !ixp) {
    return (
      <div className="text-center mt-16">
        <div className="text-3xl mb-3">404</div>
        <p className="text-gray-500 text-sm">
          IXP <code className="font-mono">{code}</code> não encontrado no snapshot atual.
        </p>
        <Link to="/" className="mt-4 inline-block text-sm text-primario-600 hover:underline">
          ← Voltar ao início
        </Link>
      </div>
    )
  }
  // Cálculos de indicadores AS
  const par = ixpEntry?.ixbr_members_count ?? null
  const dir = ixpEntry?.asn_direct_union_count ?? null
  const dif = par != null && dir != null && dir > 0 ? ((par - dir) / dir) * 100 : null
  const org = ixpEntry?.asn_origin_union_count ?? null
  const brOriginUnion = ixpEntry?.br_asns_origin_union_count ?? null
  const cbrAsns = brOriginUnion != null && totalBrASNs ? (brOriginUnion / totalBrASNs) * 100 : null
  const cftAsns = org != null && totalGlobalASNs ? (org / totalGlobalASNs) * 100 : null
  const ctx: PttCtx = {
    code: code!, date, historico, routeServers, rejeicoes, facilities, portas, ixp, v4, v6, v4idx, v6idx, par, dir, dif, org, brOriginUnion, cbrAsns, cftAsns, totalBrASNs, totalGlobalASNs,
    estUsers, potential, usuariosBrTotal: totais?.br_apnic_users_total ?? null, mergedV4, mergedV6, membersWithoutDirect, nameMap, peersV4, peersV6,
    loadingPeersV4, loadingPeersV6, loadingMembers, membersData, assinantes,
    selectedPeerV4, selectedPeerV6, setSelectedPeerV4, setSelectedPeerV6,
  }

  return (
    <div className="space-y-6">
      <CabecalhoPtt code={code!} nome={ixp.name} uf={ixp.uf} snapshot={ixp.snapshot_date}
        coletaV4={coletaDaFamilia(ixp.v4)} coletaV6={coletaDaFamilia(ixp.v6)} rotasV4={v4?.total_routes ?? null} rotasV6={v6?.total_routes ?? null} />
      <EntityPage entidade="ixp" rotulo={`PTT ${ixp.name} (${ixp.uf})`} dados={ctx} snapshot={ixp.snapshot_date} fontes={fontes} espacamento="space-y-6" />
    </div>
  )
}
