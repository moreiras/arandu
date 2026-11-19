// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Ponto no formato do GeoJSON: [longitude, latitude]. */
export type LonLat = [number, number]

const RAIO_TERRA_KM = 6371.0088

/** Distância em linha reta (great-circle, haversine) entre dois pontos, em km. */
export function haversineKm(a: LonLat, b: LonLat): number {
  const rad = (g: number) => (g * Math.PI) / 180
  const dLat = rad(b[1] - a[1])
  const dLon = rad(b[0] - a[0])
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a[1])) * Math.cos(rad(b[1])) * Math.sin(dLon / 2) ** 2
  return 2 * RAIO_TERRA_KM * Math.asin(Math.min(1, Math.sqrt(h)))
}

export interface PontoNomeado { codigo: string; nome: string; lonlat: LonLat }
export interface PontoProximo extends PontoNomeado { km: number }

/** Os `n` pontos mais próximos da origem, do menor para o maior, com a distância. Vazio se não houver origem. */
export function maisProximos(origem: LonLat | null | undefined, pontos: PontoNomeado[], n = 1): PontoProximo[] {
  if (!origem) return []
  return pontos.map((p) => ({ ...p, km: haversineKm(origem, p.lonlat) })).sort((x, y) => x.km - y.km).slice(0, n)
}

/** Distância arredondada para exibir: "12 km" (menos de 10 km mostra uma casa). */
export function fmtKm(km: number | null | undefined): string {
  if (km == null || !Number.isFinite(km)) return '—'
  return `${km < 10 ? km.toLocaleString('pt-BR', { maximumFractionDigits: 1 }) : Math.round(km).toLocaleString('pt-BR')} km`
}
