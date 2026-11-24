// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import {
  fetchAcessosMunicipiosMapa, fetchIXPresence, fetchIXPs, fetchMapAsns, fetchMapPix, fetchMapPrefixes, fetchResolvePlace, fetchOutorgasMapa,
} from '../../services/api'
import type { IXPresenceResponse } from '../../services/api'
import type { SiciMunicipiosMapaResponse } from '../../types/api'
import type { AsnFeature, PixFeature, PrefixFeature, ScmGeoFeature } from './tipos'
import { ehErroDeAcessoOuFalha, ehNaoEncontrado } from '../../components/ui/EstadoDados'

const PARA_SEMPRE = { staleTime: Infinity, gcTime: Infinity } as const

/** Todas as consultas do Localizador. Os prefixos só são buscados com a camada ligada (pesam). */
export function useLocalizadorDados(date: string | undefined, showPrefixes: boolean) {
  const asnGeo = useQuery<{ features: AsnFeature[] }>({
    queryKey: ['map-asns', date],
    queryFn: () => fetchMapAsns(date) as unknown as Promise<{ features: AsnFeature[] }>,
    ...PARA_SEMPRE,
  })
  const prefixGeo = useQuery<{ features: PrefixFeature[] }>({
    queryKey: ['map-prefixes', date],
    queryFn: () => fetchMapPrefixes(date) as Promise<{ features: PrefixFeature[] }>,
    ...PARA_SEMPRE,
    enabled: showPrefixes,
  })
  // Nomes dos IXes (código → nome de cidade) para montar as tags "IX <cidade>".
  const ixList = useQuery<{ ixps: Array<{ code: string; name: string }> }>({
    queryKey: ['ixps-index', date],
    queryFn: () => fetchIXPs(date ?? undefined) as Promise<{ ixps: Array<{ code: string; name: string }> }>,
    ...PARA_SEMPRE,
  })
  // Índice reverso AS → participação em IXes (membro / origina prefixos).
  const ixPresence = useQuery<IXPresenceResponse>({
    queryKey: ['asn-ix-presence', date],
    queryFn: () => fetchIXPresence(date),
    ...PARA_SEMPRE,
  })
  // PIX (PTTs físicos) do IX.br geolocalizados.
  const pixGeo = useQuery<{ features: PixFeature[] }>({
    queryKey: ['map-pix', date],
    queryFn: () => fetchMapPix(date) as Promise<{ features: PixFeature[] }>,
    ...PARA_SEMPRE,
  })
  // SCMs geolocalizados (Anatel) — carregado sempre para enriquecer sedes de AS.
  const scmGeo = useQuery<{ features: ScmGeoFeature[] }>({
    queryKey: ['map-scms-loc', date],
    queryFn: () => fetchOutorgasMapa('SCM', { date }) as Promise<{ features: ScmGeoFeature[] }>,
    ...PARA_SEMPRE,
  })
  // Usuários declarados ao SICI, por município (ibge → operadores).
  const siciMunData = useQuery<SiciMunicipiosMapaResponse>({
    queryKey: ['sici-municipios-mapa', date],
    queryFn: () => fetchAcessosMunicipiosMapa(date),
    ...PARA_SEMPRE,
  })
  // Centróides dos municípios (mesmo arquivo estático usado em AccessMunicipioMap) — o SICI é agregado por município, sem coordenada
  // própria, então a posição no mapa vem do centróide do código IBGE.
  const municipioCentroids = useQuery<Record<string, [number, number]>>({
    queryKey: ['municipio-centroids'],
    queryFn: () => fetch('/municipios-centroides.json').then(r => r.json()),
    ...PARA_SEMPRE,
  })
  return {
    asnGeo: asnGeo.data, prefixGeo: prefixGeo.data, ixList: ixList.data, ixPresence: ixPresence.data, pixGeo: pixGeo.data,
    scmGeo: scmGeo.data, siciMunData: siciMunData.data, municipioCentroids: municipioCentroids.data,
    // Primeira camada que não veio por acesso, taxa ou rede (o 404 de uma camada opcional não é aviso): a página diz a causa.
    erro: [asnGeo, prefixGeo, ixList, ixPresence, pixGeo, scmGeo, siciMunData].map((q) => q.error).find(ehErroDeAcessoOuFalha) ?? null,
  }
}

export async function geocodeQuery(query: string, date?: string): Promise<[number, number] | null> {
  try {
    const r = await fetchResolvePlace(query, date)
    if (r?.lat != null && r?.lon != null) return [r.lat, r.lon]
  } catch (e) {
    // Só "não encontrado" vira null; acesso, taxa e rede sobem para a página dizer a causa.
    if (!ehNaoEncontrado(e)) throw e
  }
  return null
}
