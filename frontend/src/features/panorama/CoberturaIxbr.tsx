// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { fetchIXPs, fetchHealth, fetchSnapshot } from '../../services/api'
import { useActiveDate } from '../../hooks/useSnapshot'
import { IXPMetricsChart } from '../../components/charts/IXPMetricsChart'
import type { IXPIndexAfi, IXPIndexEntry } from '../../types/api'

export type GrupoCobertura = 'ipv4' | 'ipv6' | 'asns'

function getV4(ixp: IXPIndexEntry): IXPIndexAfi | null {
  const v = ixp.v4
  return v && 'total_routes' in v ? (v as IXPIndexAfi) : null
}

function getV6(ixp: IXPIndexEntry): IXPIndexAfi | null {
  const v = ixp.v6
  return v && 'total_routes' in v ? (v as IXPIndexAfi) : null
}

function n(v: number | undefined | null) {
  return v?.toLocaleString('pt-BR') ?? '—'
}

function p(v: number | null | undefined, denom: number | null | undefined, dec = 1) {
  if (v == null || !denom) return '—'
  return `${((v / denom) * 100).toFixed(dec)}%`
}


/**
 * Cobertura no IX.br por PTT: `ipv4` (2 gráficos), `ipv6` (2) e `asns` (3). Cada panorama escolhe os grupos que cabem no seu tema;
 * a página de Estatísticas (`?versao=1`) mostra os três. As consultas (`ixps`, detalhe do snapshot) usam as mesmas chaves das demais páginas, então não repetem chamada.
 */
export function CoberturaIxbr({ grupos }: { grupos: GrupoCobertura[] }) {
  const date = useActiveDate()
  const { data: health } = useQuery({ queryKey: ['health'], queryFn: fetchHealth })
  const { data: ixpData, isLoading } = useQuery({ queryKey: ['ixps', date], queryFn: () => fetchIXPs(date ?? undefined), staleTime: Infinity, gcTime: Infinity })
  const resolvedDate = date ?? health?.latest_snapshot ?? ixpData?.snapshot_date ?? ''
  const { data: snapshotDetails } = useQuery({ queryKey: ['snapshot-details', resolvedDate], queryFn: () => fetchSnapshot(resolvedDate), enabled: !!resolvedDate, staleTime: Infinity, gcTime: Infinity })
  const ixps = ixpData?.ixps ?? []
  const totalBrASNs = snapshotDetails?.summary?.total_asns_br ?? null
  const brAsnsInFt = snapshotDetails?.summary?.global_table?.br_asns_in_ft ?? null
  const totalGlobalASNs = snapshotDetails?.summary?.global_table?.total_asns ?? null

  // ── Tooltips de cobertura ────────────────────────────────────────────────

  function tooltipCovBrV4(ixp: IXPIndexEntry, value: number) {
    return (
      <>
        <strong>{value.toFixed(2)}%</strong> dos prefixos IPv4 alocados pelo Registro.br são
        visíveis no IX.br {ixp.name}, {ixp.uf}
      </>
    )
  }

  function tooltipCovFtV4(ixp: IXPIndexEntry, value: number) {
    return (
      <>
        <strong>{value.toFixed(2)}%</strong> do espaço IPv4 da tabela de roteamento global
        (RouteViews) está visível no IX.br {ixp.name}, {ixp.uf}
      </>
    )
  }

  function tooltipCovBrV6(ixp: IXPIndexEntry, value: number) {
    return (
      <>
        <strong>{value.toFixed(2)}%</strong> dos prefixos IPv6 alocados pelo Registro.br são
        visíveis no IX.br {ixp.name}, {ixp.uf}
      </>
    )
  }

  function tooltipCovFtV6(ixp: IXPIndexEntry, value: number) {
    return (
      <>
        <strong>{value.toFixed(2)}%</strong> do espaço IPv6 da tabela de roteamento global
        (RouteViews) está visível no IX.br {ixp.name}, {ixp.uf}
      </>
    )
  }

  // ── Tooltips de ASNs ─────────────────────────────────────────────────────

  function tooltipAsnDirect(ixp: IXPIndexEntry, value: number) {
    return (
      <>
        <strong>{n(value)}</strong> ASNs participam diretamente do IX.br {ixp.name}, {ixp.uf},
        isso representa <strong>{p(value, totalBrASNs)}</strong> dos {n(totalBrASNs)} ASNs
        alocados pelo Registro.br, <strong>{p(value, brAsnsInFt)}</strong> dos {n(brAsnsInFt)}{' '}
        ASNs do Registro.br visíveis na tabela global e{' '}
        <strong>{p(value, totalGlobalASNs)}</strong> dos {n(totalGlobalASNs)} ASNs presentes na
        tabela global BGP
      </>
    )
  }

  function tooltipAsnOrigin(ixp: IXPIndexEntry, value: number) {
    return (
      <>
        <strong>{n(value)}</strong> ASNs originam prefixos visíveis no IX.br {ixp.name},{' '}
        {ixp.uf}, isso representa <strong>{p(value, totalBrASNs)}</strong> dos {n(totalBrASNs)}{' '}
        ASNs alocados pelo Registro.br, <strong>{p(value, brAsnsInFt)}</strong> dos{' '}
        {n(brAsnsInFt)} ASNs do Registro.br visíveis na tabela global e{' '}
        <strong>{p(value, totalGlobalASNs)}</strong> dos {n(totalGlobalASNs)} ASNs presentes na
        tabela global BGP
      </>
    )
  }

  function tooltipAsnBrOrigin(ixp: IXPIndexEntry, value: number) {
    return (
      <>
        <strong>{n(value)}</strong> ASNs brasileiros (Registro.br) originam prefixos visíveis no
        IX.br {ixp.name}, {ixp.uf}, isso representa{' '}
        <strong>{p(value, totalBrASNs)}</strong> dos {n(totalBrASNs)} ASNs alocados pelo
        Registro.br, <strong>{p(value, brAsnsInFt)}</strong> dos {n(brAsnsInFt)} ASNs do
        Registro.br visíveis na tabela global e{' '}
        <strong>{p(value, totalGlobalASNs)}</strong> dos {n(totalGlobalASNs)} ASNs presentes na
        tabela global BGP
      </>
    )
  }


  if (isLoading) {
    return <div className="space-y-6">{[1, 2, 3].map((i) => <div key={i} className="h-64 bg-gray-100 rounded-lg animate-pulse" />)}</div>
  }
  if (ixps.length === 0) {
    return <div className="text-center py-16 text-gray-400"><p>Nenhum dado disponível. Execute o pipeline completo para gerar estatísticas.</p></div>
  }
  return (
    <div className="space-y-10" data-testid="cobertura-ixbr">
      {grupos.includes('ipv6') && (
        <>
          {/* ── Cobertura IPv6 ── */}
          <section>
            <h2 className="text-base font-semibold text-gray-800 mb-1">
              Cobertura dos prefixos brasileiros IPv6 no IX.br
            </h2>
            <p className="text-xs text-gray-500 mb-4">
              % do espaço IPv6 declarado no Registro.br visível em cada IXP (por espaço).
            </p>
            <IXPMetricsChart
              ixps={ixps}
              getValue={(ixp) => getV6(ixp)?.br_prefix_coverage_pct ?? null}
              label="Cob. prefixos BR IPv6 (%)"
              color="#8b5cf6"
              isPct
              renderTooltipContent={tooltipCovBrV6}
            />
          </section>

          <section>
            <h2 className="text-base font-semibold text-gray-800 mb-1">
              Cobertura dos prefixos totais IPv6 da full table no IX.br
            </h2>
            <p className="text-xs text-gray-500 mb-4">
              % do espaço IPv6 da tabela de roteamento global (RouteViews) visível em cada IXP.
            </p>
            <IXPMetricsChart
              ixps={ixps}
              getValue={(ixp) => getV6(ixp)?.ixp_vs_fulltable_space_pct ?? null}
              label="Cob. full table IPv6 (%)"
              color="#a78bfa"
              isPct
              renderTooltipContent={tooltipCovFtV6}
            />
          </section>
        </>
      )}
      {grupos.includes('ipv4') && (
        <>
          {/* ── Cobertura IPv4 ── */}
          <section>
            <h2 className="text-base font-semibold text-gray-800 mb-1">
              Cobertura dos prefixos brasileiros IPv4 no IX.br
            </h2>
            <p className="text-xs text-gray-500 mb-4">
              % do espaço IPv4 declarado no Registro.br visível em cada IXP (por espaço, não contagem de prefixos).
            </p>
            <IXPMetricsChart
              ixps={ixps}
              getValue={(ixp) => getV4(ixp)?.br_prefix_coverage_pct ?? null}
              label="Cob. prefixos BR IPv4 (%)"
              color="#3b82f6"
              isPct
              renderTooltipContent={tooltipCovBrV4}
            />
          </section>

          <section>
            <h2 className="text-base font-semibold text-gray-800 mb-1">
              Cobertura dos prefixos totais IPv4 da full table no IX.br
            </h2>
            <p className="text-xs text-gray-500 mb-4">
              % do espaço IPv4 da tabela de roteamento global (RouteViews) visível em cada IXP.
            </p>
            <IXPMetricsChart
              ixps={ixps}
              getValue={(ixp) => getV4(ixp)?.ixp_vs_fulltable_space_pct ?? null}
              label="Cob. full table IPv4 (%)"
              color="#6366f1"
              isPct
              renderTooltipContent={tooltipCovFtV4}
            />
          </section>
        </>
      )}
      {grupos.includes('asns') && (
        <>
          {/* ── ASNs ── */}
          <section>
            <h2 className="text-base font-semibold text-gray-800 mb-1">
              ASNs em peering direto por IXP
            </h2>
            <p className="text-xs text-gray-500 mb-4">
              ASNs com sessão BGP direta no Route Server do IXP (não contabiliza originadores via upstream).
            </p>
            <IXPMetricsChart
              ixps={ixps}
              getValue={(ixp) => ixp.asn_direct_union_count ?? null}
              label="ASNs diretos"
              color="#0ea5e9"
              renderTooltipContent={tooltipAsnDirect}
            />
          </section>

          <section>
            <h2 className="text-base font-semibold text-gray-800 mb-1">
              ASNs originadores por IXP
            </h2>
            <p className="text-xs text-gray-500 mb-4">
              ASNs cujos prefixos aparecem na tabela do IXP, incluindo os que chegam via upstream.
            </p>
            <IXPMetricsChart
              ixps={ixps}
              getValue={(ixp) => ixp.asn_origin_union_count ?? null}
              label="ASNs originadores"
              color="#06b6d4"
              renderTooltipContent={tooltipAsnOrigin}
            />
          </section>

          <section>
            <h2 className="text-base font-semibold text-gray-800 mb-1">
              ASNs originadores brasileiros por IXP
            </h2>
            <p className="text-xs text-gray-500 mb-4">
              ASNs alocados pelo Registro.br cujos prefixos são visíveis na tabela do IXP (união IPv6 ∪ IPv4).
            </p>
            <IXPMetricsChart
              ixps={ixps}
              getValue={(ixp) => ixp.br_asns_origin_union_count ?? null}
              label="ASNs BR originadores"
              color="#ef4444"
              renderTooltipContent={tooltipAsnBrOrigin}
            />
          </section>
        </>
      )}
    </div>
  )
}
