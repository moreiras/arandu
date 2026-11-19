// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { haversineKm, type LonLat } from '../../lib/geo'

/** Teto de municípios agregados: limita as chamadas ao perfil e o tempo de carga. É interno, não aparece na interface. */
export const MAX_MUNICIPIOS_RAIO = 50
export const RAIO_MAX_KM = 500
export const RAIO_PASSO_KM = 5

export interface Vizinho { ibge: string; km: number }

export interface ConjuntoRaio {
  central: string
  /** Raio pedido pelo usuário (0 = só o município). */
  raioKm: number
  /** Município central primeiro e depois os mais próximos, no máximo `MAX_MUNICIPIOS_RAIO` no total. */
  selecionados: Vizinho[]
  /** Dentro do raio, mas cortados pelo teto (ficam no mapa em cinza; não entram nas somas). */
  foraDoLimite: Vizinho[]
  /** Quantos municípios há dentro do raio pedido (selecionados + cortados). */
  dentroDoRaio: number
  cortado: boolean
  /** Até onde as somas realmente chegam: o raio pedido, ou a distância do último selecionado quando o teto corta. */
  raioEfetivoKm: number
}

/**
 * Municípios cujo centróide está a até `raioKm` do centróide do município central, do mais próximo ao mais distante (empate: código IBGE),
 * limitados a `max`. Devolve `null` se o município central não tem centróide. Distância em linha reta entre centróides, não a área do município.
 */
export function conjuntoNoRaio(central: string, centroides: Record<string, LonLat>, raioKm: number, max = MAX_MUNICIPIOS_RAIO): ConjuntoRaio | null {
  const origem = centroides[central]
  if (!origem) return null
  const raio = Math.max(0, Math.min(RAIO_MAX_KM, Number.isFinite(raioKm) ? raioKm : 0))
  const dentro: Vizinho[] = []
  if (raio > 0) {
    for (const [ibge, c] of Object.entries(centroides)) {
      if (ibge === central) continue
      const km = haversineKm(origem, c)
      if (km <= raio) dentro.push({ ibge, km })
    }
    dentro.sort((a, b) => a.km - b.km || a.ibge.localeCompare(b.ibge))
  }
  const cabem = Math.max(0, max - 1)
  const selecionados = [{ ibge: central, km: 0 }, ...dentro.slice(0, cabem)]
  const cortado = dentro.length > cabem
  return {
    central, raioKm: raio, selecionados, foraDoLimite: dentro.slice(cabem), dentroDoRaio: dentro.length + 1, cortado,
    raioEfetivoKm: cortado ? selecionados[selecionados.length - 1].km : raio,
  }
}

/** Polígono aproximado (GeoJSON) de um círculo de `km` ao redor de `centro`, para desenhar o raio no mapa. */
export function circuloGeoJSON(centro: LonLat, km: number, passos = 96): GeoJSON.Feature<GeoJSON.Polygon> {
  const R = 6371.0088
  const lat = (centro[1] * Math.PI) / 180
  const lon = (centro[0] * Math.PI) / 180
  const d = km / R
  const anel: [number, number][] = []
  for (let i = 0; i <= passos; i++) {
    const b = (2 * Math.PI * i) / passos
    const la = Math.asin(Math.sin(lat) * Math.cos(d) + Math.cos(lat) * Math.sin(d) * Math.cos(b))
    const lo = lon + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(lat), Math.cos(d) - Math.sin(lat) * Math.sin(la))
    anel.push([(lo * 180) / Math.PI, (la * 180) / Math.PI])
  }
  return { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [anel] } }
}
