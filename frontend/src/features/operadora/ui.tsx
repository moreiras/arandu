// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { GrupoCnpjEntry } from '../../types/api'
import { ordenarPorFaixa } from '../../lib/faixas'

export const fmt = (n: number | null | undefined) => (n == null ? '—' : n.toLocaleString('pt-BR'))

export function fmtCnpj(c: string): string {
  const d = (c ?? '').replace(/\D/g, '')
  if (d.length !== 14) return c
  return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8,12)}-${d.slice(12)}`
}

export function mergeGrupoCnpjs(
  a: GrupoCnpjEntry[] | undefined,
  b: GrupoCnpjEntry[] | undefined,
): GrupoCnpjEntry[] {
  const byCnpj = new Map<string, GrupoCnpjEntry>()
  for (const e of [...(a ?? []), ...(b ?? [])]) byCnpj.set(e.cnpj, e)
  return [...byCnpj.values()].sort((x, y) => (x.empresa || x.cnpj).localeCompare(y.empresa || y.cnpj))
}

export function fmtCapacidade(mbps: number | undefined): string {
  if (!mbps) return '—'
  if (mbps >= 1e6) return `${(mbps / 1e6).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} Tbps`
  if (mbps >= 1e3) return `${(mbps / 1e3).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} Gbps`
  return `${mbps.toLocaleString('pt-BR', { maximumFractionDigits: 0 })} Mbps`
}

export function KPI({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="px-3 py-2 rounded-lg bg-gray-50 border border-gray-100">
      <div className="text-xs text-gray-400 uppercase tracking-wide">{label}</div>
      <div className="text-lg font-semibold text-gray-900 tabular-nums leading-tight">{value}</div>
      {hint && <div className="text-xs text-gray-400">{hint}</div>}
    </div>
  )
}

/** `ordem="faixa"`: faixas de velocidade na ordem das faixas (e todas, sem corte); padrão: as 6 maiores por valor. */
export function Barras({ dados, total, ordem = 'valor' }: { dados: Record<string, number>; total: number; ordem?: 'valor' | 'faixa' }) {
  const rows = ordem === 'faixa' ? ordenarPorFaixa(Object.entries(dados)) : Object.entries(dados).sort((a, b) => b[1] - a[1]).slice(0, 6)
  if (!rows.length) return null
  return (
    <div className="space-y-1">
      {rows.map(([k, v]) => (
        <div key={k} className="flex items-center gap-2 text-xs">
          <span className="w-32 truncate text-gray-600" title={k}>{k}</span>
          <span className="flex-1 h-2.5 bg-gray-100 rounded-sm overflow-hidden">
            <span className="block h-full bg-primario-500/70"
                  style={{ width: `${total ? (100 * v) / total : 0}%` }} />
          </span>
          <span className="w-20 text-right tabular-nums text-gray-500">{fmt(v)}</span>
        </div>
      ))}
    </div>
  )
}
