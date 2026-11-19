// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Tabela de métricas por família (IPv6/IPv4) da página Comparar. */
import type { IXPAfiFull } from '../../types/api'

// ── AFI metrics table (só quando exatamente 2 IX.br são comparados) ─────────

export function fmtNum(n: number | undefined): string {
  if (n == null) return '—'
  return n.toLocaleString('pt-BR')
}

export function fmtPct(n: number | undefined | null): string {
  if (n == null) return '—'
  return n.toFixed(1) + '%'
}

export function brPrefixCoverageVsFT(
  afi: IXPAfiFull | null,
  brCovInFT: number | null | undefined,
): string {
  if (!afi || brCovInFT == null || brCovInFT <= 0) return '—'
  const ftBrSpace = afi.br_prefix_declared_space * (brCovInFT / 100)
  if (ftBrSpace === 0) return '—'
  return (afi.br_prefix_covered_space / ftBrSpace * 100).toFixed(1) + '%'
}

export function AfiMetricsTable({
  title,
  afiA,
  afiB,
  labelA,
  labelB,
  brCovInFT,
}: {
  title: string
  afiA: IXPAfiFull | null
  afiB: IXPAfiFull | null
  labelA: string
  labelB: string
  brCovInFT: number | null | undefined
}) {
  if (!afiA && !afiB) return null

  const rows: { label: string; tooltip?: string; a: string; b: string }[] = [
    { label: `ASNs diretos ${title}`, a: fmtNum(afiA?.asn_direct_count), b: fmtNum(afiB?.asn_direct_count) },
    { label: `ASNs originadores ${title}`, a: fmtNum(afiA?.asn_origin_count), b: fmtNum(afiB?.asn_origin_count) },
    {
      label: `Cobertura BR ASNs ${title}`,
      tooltip: `ASNs BR originadores neste IXP / ASNs BR originando prefixos ${title} na tabela global`,
      a: fmtPct(afiA?.br_asns_origin_pct),
      b: fmtPct(afiB?.br_asns_origin_pct),
    },
    { label: `Prefixos ${title}`, a: fmtNum(afiA?.unique_prefixes), b: fmtNum(afiB?.unique_prefixes) },
    {
      label: `Cobertura BR Prefixos ${title}`,
      tooltip: `Espaço de prefixos BR visível neste IXP / espaço BR visível na tabela global`,
      a: brPrefixCoverageVsFT(afiA, brCovInFT),
      b: brPrefixCoverageVsFT(afiB, brCovInFT),
    },
  ]

  return (
    <div className="overflow-x-auto rounded border border-gray-200">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
          <tr>
            <th className="px-3 py-2 text-left font-medium">Métrica BGP — {title}</th>
            <th className="px-3 py-2 text-right font-medium w-36 truncate" title={labelA}>A</th>
            <th className="px-3 py-2 text-right font-medium w-36 truncate" title={labelB}>B</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map(row => (
            <tr key={row.label} className="hover:bg-gray-50">
              <td className="px-3 py-2 text-gray-600" title={row.tooltip}>
                {row.label}
                {row.tooltip && <span className="ml-1 text-gray-400 text-xs cursor-help">ⓘ</span>}
              </td>
              <td className="px-3 py-2 text-right tabular-nums font-mono text-gray-800">{row.a}</td>
              <td className="px-3 py-2 text-right tabular-nums font-mono text-gray-800">{row.b}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Combinações (regiões de interseção) ─────────────────────────────────────

export const SET_COLORS = ['#2563eb', '#16a34a', '#ea580c', '#9333ea'] // blue, green, orange, purple
