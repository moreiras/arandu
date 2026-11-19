// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
export const fmt = (n: number | null | undefined) => (n == null ? '—' : n.toLocaleString('pt-BR'))

export function fmtCnpj(c: string): string {
  const d = (c ?? '').replace(/\D/g, '')
  if (d.length !== 14) return c
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`
}

/** Interpretação do HHI, na convenção usada por autoridades de concorrência. */
export function hhiLabel(hhi: number): { texto: string; cor: string } {
  if (hhi >= 2500) return { texto: 'altamente concentrado', cor: 'text-perigo-700 bg-perigo-50 border-perigo-100' }
  if (hhi >= 1500) return { texto: 'moderadamente concentrado', cor: 'text-aviso-700 bg-aviso-50 border-aviso-100' }
  return { texto: 'competitivo', cor: 'text-mercado-700 bg-mercado-50 border-mercado-100' }
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
