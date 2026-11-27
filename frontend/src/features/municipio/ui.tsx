// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { faixaHhi, rotuloFaixaHhi } from '../../lib/referencias'

export const fmt = (n: number | null | undefined) => (n == null ? '—' : n.toLocaleString('pt-BR'))

export function fmtCnpj(c: string): string {
  const d = (c ?? '').replace(/\D/g, '')
  if (d.length !== 14) return c
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`
}

/** Faixa do HHI pelo método do projeto (D11): rótulo numérico e cor neutra, sem cor de juízo. A nota de método fica em `NOTA_FAIXAS_HHI`. */
export function hhiLabel(hhi: number): { texto: string; cor: string } {
  return { texto: rotuloFaixaHhi(faixaHhi(hhi)), cor: 'text-gray-700 bg-gray-50 border-gray-200' }
}

export function KPI({ label, value, hint, referencia }: { label: string; value: string; hint?: string; referencia?: string }) {
  return (
    <div className="px-3 py-2 rounded-lg bg-gray-50 border border-gray-100">
      <div className="text-xs text-gray-400 uppercase tracking-wide">{label}</div>
      <div className="text-lg font-semibold text-gray-900 tabular-nums leading-tight">{value}</div>
      {hint && <div className="text-xs text-gray-400">{hint}</div>}
      {referencia && <div className="text-xs text-gray-600" data-kpi-referencia>{referencia}</div>}
    </div>
  )
}
