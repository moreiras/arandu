// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Itens, grupos, saúde do snapshot e painel de estatísticas da Visão geral. */
import { useState } from 'react'
import type { SnapshotSummary } from '../../types/api'
import { fmtN, fmtLarge, fmtPct } from './formato'
import { corLegivel } from '../../lib/contraste'

// ─── StatItem ────────────────────────────────────────────────────────────────

export function StatItem({
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
          style={accent ? { color: corLegivel(accent) } : undefined}
        >
          {value}
        </div>
      )}
      <div className="text-xs text-gray-500 mt-0.5 leading-tight">{label}</div>
      {sub && <div className="text-xs text-gray-400 leading-tight">{sub}</div>}
    </div>
  )
}

// ─── StatGroup ───────────────────────────────────────────────────────────────

export function StatGroup({
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

// ─── SnapshotHealth ──────────────────────────────────────────────────────────

export function SnapshotHealth({
  summary,
  loading,
}: {
  summary: SnapshotSummary | null | undefined
  loading: boolean
}) {
  const [expanded, setExpanded] = useState(false)

  if (loading || !summary) return null

  // ixps_failed é a lista dos códigos 'sem dados' + 'parciais': sobrepõe ixps_missing/ixps_partial,
  // então serve só para listar os códigos, nunca para somar (senão o IXP é contado duas vezes).
  const ixpProblem = summary.ixps_failed?.length ?? 0
  const ixpMissing = summary.ixps_missing ?? 0
  const hasWarning = ixpProblem > 0 || ixpMissing > 0
  const totalIxps = (summary.ixps_ok ?? 0) + (summary.ixps_partial ?? 0) + ixpMissing

  return (
    <div className="text-sm">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-1.5 text-gray-500 hover:text-gray-700 transition-colors"
      >
        {hasWarning ? (
          <span className="inline-flex items-center gap-1 text-aviso-600 font-medium">
            <span className="text-base leading-none">⚠</span>
            Dados incompletos
          </span>
        ) : (
          <span className="text-gray-400 text-xs">Snapshot completo</span>
        )}
        <span
          className="text-gray-400 text-xs transition-transform duration-150"
          style={{ display: 'inline-block', transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
        >
          ▾
        </span>
      </button>

      {expanded && (
        <div className="mt-2 pl-1 space-y-1 text-xs text-gray-500 border-l-2 border-gray-200 pl-3">
          <div>
            <span className="font-medium text-gray-700">IXPs coletados:</span>{' '}
            <span className="text-ok-600">{summary.ixps_ok ?? '—'} ok</span>
            {(summary.ixps_partial ?? 0) > 0 && (
              <>, <span className="text-aviso-500">{summary.ixps_partial} parcial</span></>
            )}
            {ixpMissing > 0 && (
              <>, <span className="text-perigo-500">{ixpMissing} sem dados</span></>
            )}
            {totalIxps > 0 && <span className="text-gray-400"> / {totalIxps} total</span>}
          </div>
          {ixpProblem > 0 && (
            <div className="text-perigo-500">
              IXPs sem dados ou parciais: {summary.ixps_failed?.join(', ')}
            </div>
          )}
          <div>
            <span className="font-medium text-gray-700">Registro.br:</span>{' '}
            {summary.registro_br_asns
              ? `${fmtN(summary.registro_br_asns)} ASNs · ${fmtN(summary.registro_br_prefixes_v6)} prefixos IPv6 · ${fmtN(summary.registro_br_prefixes_v4)} prefixos IPv4`
              : 'sem dados'}
          </div>
          <div>
            <span className="font-medium text-gray-700">Tabela global:</span>{' '}
            {summary.global_table
              ? `${fmtN(summary.total_asns_global)} ASNs · ${fmtN(summary.global_table.v4_prefixes)} prefixos IPv4`
              : <span className="text-perigo-500">sem dados</span>}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── StatsPanel ──────────────────────────────────────────────────────────────

export function StatsPanel({
  summary,
  loading,
}: {
  summary: SnapshotSummary | null | undefined
  loading: boolean
}) {
  const s = summary
  const gt = s?.global_table
  const ixp = s?.ixp_aggregate

  const brAsnsPctOfFt =
    gt?.br_asns_in_ft != null && s?.total_asns_global
      ? (gt.br_asns_in_ft / s.total_asns_global) * 100
      : null

  const pctFtV4 = gt?.v4_br_pct_of_ft ?? null
  const pctFtV6 = gt?.v6_br_pct_of_ft ?? null

  const brV4SpaceInFt =
    gt?.v4_space_24 != null && gt?.v4_br_pct_of_ft != null
      ? Math.round((gt.v4_space_24 * gt.v4_br_pct_of_ft) / 100)
      : null
  // v6_br_space_48 = rir_vis_cells × 65536 — denominador consistente com os demais valores.
  // NÃO usar v6_space_48 × v6_br_pct_of_ft: o espaço bruto e as células Hilbert têm
  // denominadores incompatíveis (prefixos >/32 ocupam 1 célula mas <65536 /48s).
  const brV6SpaceInFt = gt?.v6_br_space_48 ?? null

  const pctAsnV4 =
    s?.br_asns_ft_v4 != null && gt?.br_asns_in_ft
      ? (s.br_asns_ft_v4 / gt.br_asns_in_ft) * 100
      : null
  const pctAsnV6 =
    s?.br_asns_ft_v6 != null && gt?.br_asns_in_ft
      ? (s.br_asns_ft_v6 / gt.br_asns_in_ft) * 100
      : null

  const brV4SpaceInIxp =
    s?.registro_br_declared_space_v4_24 != null && ixp?.v4_br_coverage_pct != null
      ? Math.round((s.registro_br_declared_space_v4_24 * ixp.v4_br_coverage_pct) / 100)
      : null
  const brV6SpaceInIxp =
    s?.registro_br_declared_space_v6_48 != null && ixp?.v6_br_coverage_pct != null
      ? Math.round((s.registro_br_declared_space_v6_48 * ixp.v6_br_coverage_pct) / 100)
      : null

  const ixpCount = s
    ? (s.ixps_ok ?? 0) + (s.ixps_partial ?? 0) + (s.ixps_missing ?? 0)
    : null

  const pctBrInIxp =
    ixp?.br_asns_origin_union_count != null && gt?.br_asns_in_ft
      ? (ixp.br_asns_origin_union_count / gt.br_asns_in_ft) * 100
      : null

  return (
    <div className="space-y-2">

      {/* ASNs */}
      <StatGroup title="ASNs Brasileiros" color="#3b82f6">
        <StatItem
          loading={loading}
          value={fmtN(s?.total_asns_br)}
          label="alocados Registro.br"
          accent="#2563eb"
        />
        <StatItem
          loading={loading}
          value={fmtN(gt?.br_asns_in_ft)}
          label="visíveis na tabela global"
          sub={brAsnsPctOfFt != null ? `${fmtPct(brAsnsPctOfFt)} da FT` : undefined}
        />
        <StatItem
          loading={loading}
          value={fmtN(s?.br_asns_ft_v6)}
          label="visíveis na FT com IPv6"
          sub={pctAsnV6 != null ? `${fmtPct(pctAsnV6)} dos visíveis` : undefined}
        />
        <StatItem
          loading={loading}
          value={fmtN(s?.br_asns_ft_v4)}
          label="visíveis na FT com IPv4"
          sub={pctAsnV4 != null ? `${fmtPct(pctAsnV4)} dos visíveis` : undefined}
        />
      </StatGroup>

      {/* IPv6 */}
      <StatGroup title="Espaço IPv6 Brasileiro" color="#8b5cf6">
        <StatItem
          loading={loading}
          value={fmtN(s?.registro_br_prefixes_v6)}
          label="prefixos alocados"
        />
        <StatItem
          loading={loading}
          value={fmtLarge(s?.registro_br_declared_space_v6_48)}
          label="/48s alocados"
          sub="espaço Registro.br"
        />
        <StatItem
          loading={loading}
          value={fmtPct(gt?.v6_br_coverage_pct)}
          label="cobertura alocado → FT"
          sub="% do espaço BR visível na FT"
        />
        <StatItem
          loading={loading}
          value={fmtLarge(brV6SpaceInFt)}
          label="/48s alocado BR visível na FT"
          sub={pctFtV6 != null ? `${fmtPct(pctFtV6)} da tabela global` : undefined}
          accent="#8b5cf6"
        />
        <StatItem
          loading={loading}
          value={fmtLarge(brV6SpaceInIxp)}
          label="/48s visíveis no IX.br BR"
          sub={ixp?.v6_br_coverage_pct != null ? `${fmtPct(ixp.v6_br_coverage_pct)} do alocado BR` : undefined}
        />
      </StatGroup>

      {/* IPv4 */}
      <StatGroup title="Espaço IPv4 Brasileiro" color="#10b981">
        <StatItem
          loading={loading}
          value={fmtN(s?.registro_br_prefixes_v4)}
          label="prefixos alocados"
        />
        <StatItem
          loading={loading}
          value={fmtLarge(s?.registro_br_declared_space_v4_24)}
          label="/24s alocados"
          sub="espaço Registro.br"
        />
        <StatItem
          loading={loading}
          value={fmtPct(gt?.v4_br_coverage_pct)}
          label="cobertura alocado → FT"
          sub="% do espaço BR visível na FT"
        />
        <StatItem
          loading={loading}
          value={fmtLarge(brV4SpaceInFt)}
          label="/24s na tabela global BR"
          sub={pctFtV4 != null ? `${fmtPct(pctFtV4)} do espaço IPv4 global` : undefined}
          accent="#10b981"
        />
        <StatItem
          loading={loading}
          value={fmtLarge(brV4SpaceInIxp)}
          label="/24s visíveis no IX.br BR"
          sub={ixp?.v4_br_coverage_pct != null ? `${fmtPct(ixp.v4_br_coverage_pct)} do alocado BR` : undefined}
        />
      </StatGroup>

      {/* IX.br */}
      <StatGroup title="IX.br" color="#f59e0b">
        <StatItem
          loading={loading}
          value={fmtN(ixpCount)}
          label="IXPs monitorados"
        />
        <StatItem
          loading={loading}
          value={fmtN(ixp?.asn_direct_union_count)}
          label="ASNs em peering direto"
        />
        <StatItem
          loading={loading}
          value={fmtN(ixp?.br_asns_origin_union_count)}
          label="ASNs BR originando prefixos"
          sub={pctBrInIxp != null ? `${fmtPct(pctBrInIxp)} dos ASNs BR ativos` : undefined}
          accent="#d97706"
        />
        <StatItem
          loading={loading}
          value={fmtN(s?.br_ixp_origin_v6)}
          label="ASNs BR com IPv6 no IX.br"
        />
        <StatItem
          loading={loading}
          value={fmtN(s?.br_ixp_origin_v4)}
          label="ASNs BR com IPv4 no IX.br"
        />
      </StatGroup>

    </div>
  )
}
