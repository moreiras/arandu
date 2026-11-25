// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Geografia do Localizador: distância, IX mais próximo e círculo do raio (puro; testado em localizador.test.ts). */
import { IXP_COORDS } from '../../components/maps/ixpCoords'

export function distKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371
  const r = Math.PI / 180
  const dLat = (lat2 - lat1) * r
  const dLon = (lon2 - lon1) * r
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin(dLon / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

/** IX do IX.br mais próximo de um ponto (por código com coordenada conhecida). */
export function nearestIxCode(lat: number, lon: number): string | null {
  let best: string | null = null
  let bestD = Infinity
  for (const [code, [ilat, ilon]] of Object.entries(IXP_COORDS)) {
    const d = distKm(lat, lon, ilat, ilon)
    if (d < bestD) { bestD = d; best = code }
  }
  return best
}

/** Distância em linha reta (km) do ponto à cidade de cada PTT, do menor para o maior valor. Só os PTTs com coordenada conhecida. */
export function distanciasPtt(lat: number, lon: number): Array<{ code: string; km: number }> {
  return Object.entries(IXP_COORDS)
    .map(([code, [ilat, ilon]]) => ({ code, km: distKm(lat, lon, ilat, ilon) }))
    .sort((a, b) => a.km - b.km || a.code.localeCompare(b.code))
}

/** Polígono geodésico aproximando um círculo de raio em km — substitui L.circle. */
export function circlePolygon(lat: number, lon: number, radiusKm: number, points = 72): GeoJSON.Feature<GeoJSON.Polygon> {
  const R = 6371
  const latR = (lat * Math.PI) / 180
  const lonR = (lon * Math.PI) / 180
  const dR = radiusKm / R
  const ring: [number, number][] = []
  for (let i = 0; i <= points; i++) {
    const brng = (i / points) * 2 * Math.PI
    const lat2 = Math.asin(Math.sin(latR) * Math.cos(dR) + Math.cos(latR) * Math.sin(dR) * Math.cos(brng))
    const lon2 = lonR + Math.atan2(
      Math.sin(brng) * Math.sin(dR) * Math.cos(latR),
      Math.cos(dR) - Math.sin(latR) * Math.sin(lat2),
    )
    ring.push([(lon2 * 180) / Math.PI, (lat2 * 180) / Math.PI])
  }
  return { type: 'Feature', geometry: { type: 'Polygon', coordinates: [ring] }, properties: {} }
}
