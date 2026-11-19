// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ReactNode } from 'react'
import type { LonLat } from '../../lib/geo'

/** Caixa [oeste, sul, leste, norte] que enquadra os pontos, com folga em graus; sem pontos, null (o mapa usa o enquadramento do país). */
export function enquadramento(pontos: LonLat[], folga = 0.5): [number, number, number, number] | null {
  const v = pontos.filter((p) => Number.isFinite(p[0]) && Number.isFinite(p[1]))
  if (v.length === 0) return null
  const lons = v.map((p) => p[0]), lats = v.map((p) => p[1])
  return [Math.min(...lons) - folga, Math.min(...lats) - folga, Math.max(...lons) + folga, Math.max(...lats) + folga]
}

export interface ItemLegenda { rotulo: string; cor: string }

/**
 * Moldura padrão dos mapas: título, legenda com rótulos (nunca só cor, por causa do daltonismo) e altura limitada no celular.
 * O mapa em si (MapLibre) é passado como `children`; a orientação inicial vem de `bearingInicial()` (padrão sul para cima, escolha lembrada).
 */
export function MapaMoldura({ titulo, legenda, altura = 'h-80', nota, children }: { titulo: string; legenda?: ItemLegenda[]; altura?: string; nota?: string; children: ReactNode }) {
  return (
    <figure className="min-w-0" aria-label={titulo}>
      <figcaption className="mb-1 text-titulo-4 text-gray-800">{titulo}</figcaption>
      <div className={`${altura} max-h-[60vh] w-full overflow-hidden rounded-lg border border-gray-200`}>{children}</div>
      {legenda && legenda.length > 0 && (
        <ul className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-600" aria-label="Legenda">
          {legenda.map((l) => <li key={l.rotulo} className="flex items-center gap-1"><span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: l.cor }} aria-hidden="true" />{l.rotulo}</li>)}
        </ul>
      )}
      {nota && <p className="mt-1 text-xs text-gray-500">{nota}</p>}
    </figure>
  )
}
