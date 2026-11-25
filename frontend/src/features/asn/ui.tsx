// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

export const TA_COLORS: Record<string, string> = {
  lacnic:  'bg-ok-100 text-ok-800',
  ripe:    'bg-primario-100 text-primario-800',
  arin:    'bg-alerta-100 text-alerta-800',
  apnic:   'bg-v6-100 text-v6-800',
  afrinic: 'bg-aviso-100 text-aviso-800',
}

export const ACCENT = {
  orange: { dot: 'bg-alerta-400', text: 'text-alerta-700' },
  red:    { dot: 'bg-perigo-400',    text: 'text-perigo-700'    },
  amber:  { dot: 'bg-aviso-400',  text: 'text-aviso-700'  },
  blue:   { dot: 'bg-primario-400',   text: 'text-primario-700'   },
  cyan:   { dot: 'bg-tecnico-400',   text: 'text-tecnico-700'   },
  teal:   { dot: 'bg-mercado-400',   text: 'text-mercado-700'   },
  violet: { dot: 'bg-estimado-400', text: 'text-estimado-700' },
}
export type Accent = keyof typeof ACCENT

export function MetricCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string
  value: string | number
  sub?: string
  accent?: Accent
}) {
  // PT-30: o número é sempre neutro. Cor sem significado (vermelho, azul, roxo) parece juízo; `accent` fica só por compatibilidade de chamada.
  void accent
  const valClass = 'text-gray-900'
  return (
    <div className="bg-white rounded-lg border border-gray-200 px-4 py-3">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className={`text-2xl font-bold ${valClass}`}>{value}</div>
      {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// SCM / PeeringDB contacts sections
// ---------------------------------------------------------------------------

