// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Legenda do mapa "Explorar": junta as camadas ligadas. */
import { colorByItems } from './estilo'
import { COLOR_SCM, COLOR_SCM_WITH_ASN, LAYERS } from './tipos'
import type { MapState } from './tipos'

export function Swatch({ color, shape, opacity = 0.85 }: { color: string; shape: 'dot' | 'line'; opacity?: number }) {
  return shape === 'line'
    ? <span className="w-3 h-0.5 rounded flex-shrink-0" style={{ background: color, opacity }} />
    : <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: color, opacity }} />
}

export function Legend({ state }: { state: MapState }) {
  const rows: Array<{ key: string; color: string; label: string; shape: 'dot' | 'line'; opacity?: number; indent?: boolean }> = []
  for (const l of LAYERS) {
    if (!state.on[l.id]) continue
    if (l.id === 'asns_geo' && state.colorBy !== 'solid') {
      rows.push({ key: l.id, color: 'transparent', label: `${l.label}:`, shape: 'dot' })
      for (const it of colorByItems(state.colorBy)) rows.push({ key: `${l.id}-${it.label}`, ...it, shape: 'dot', indent: true })
      continue
    }
    if (l.id === 'outorgas_scm') {
      if (state.scmMode !== 'sem_asn') rows.push({ key: 'scm-com', color: COLOR_SCM_WITH_ASN, label: 'SCM com ASN', shape: 'dot' })
      if (state.scmMode !== 'com_asn') rows.push({ key: 'scm-sem', color: COLOR_SCM, label: 'SCM sem ASN', shape: 'dot' })
      continue
    }
    rows.push({ key: l.id, color: l.color, label: l.label, shape: l.shape })
  }
  if (rows.length === 0) return null
  return (
    <div className="bg-white/90 backdrop-blur-sm rounded-lg shadow-md px-3 py-2 space-y-1 max-w-[200px]">
      {rows.map(r => (
        <div key={r.key} className={`flex items-center gap-2 ${r.indent ? 'pl-2' : ''}`}>
          {r.color !== 'transparent' && <Swatch color={r.color} shape={r.shape} opacity={r.opacity} />}
          <span className="text-xs text-gray-600 leading-tight">{r.label}</span>
        </div>
      ))}
    </div>
  )
}
