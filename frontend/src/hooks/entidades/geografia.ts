// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchMapPix } from '../../services/api'
import type { LonLat, PontoNomeado } from '../../lib/geo'
import { useActiveDate } from '../useSnapshot'
import { IMUTAVEL } from './chaves'
import { ERRO_ORCAMENTO_ESGOTADO, useOrcamentoAvancado } from '../../auth/AuthContext'

const CENTROIDS_URL = '/municipios-centroides.json'

/** Centróides dos municípios (IBGE → [lon, lat]); arquivo estático do front, uma vez por sessão. Chave compartilhada com os mapas. */
export function useCentroides() {
  return useQuery<Record<string, LonLat>>({
    queryKey: ['municipios-centroides'],
    queryFn: () => fetch(CENTROIDS_URL).then((r) => r.json()),
    ...IMUTAVEL,
  })
}

/** PIX dos PTTs (pontos de troca físicos) com coordenadas, um por (PTT, local); base para "PTT mais próximo". */
export function usePtts(): { ptts: PontoNomeado[]; carregando: boolean; erro: unknown } {
  const date = useActiveDate()
  const { pronto, esgotado } = useOrcamentoAvancado()
  const q = useQuery({ queryKey: ['map-pix', date], queryFn: () => fetchMapPix(date ?? undefined), enabled: !!date && pronto && !esgotado, ...IMUTAVEL, retry: false })
  const ptts = useMemo(() => {
    const vistos = new Set<string>()
    const lista: PontoNomeado[] = []
    for (const f of (q.data?.features ?? []) as Array<{ geometry?: { coordinates?: number[] }; properties?: Record<string, unknown> }>) {
      const c = f.geometry?.coordinates
      const codigo = String(f.properties?.ixp_code ?? '')
      if (!c || c.length < 2 || !codigo) continue
      const chave = `${codigo}|${c[0]}|${c[1]}`
      if (vistos.has(chave)) continue
      vistos.add(chave)
      lista.push({ codigo, nome: String(f.properties?.ixp_name ?? f.properties?.name ?? codigo), lonlat: [c[0], c[1]] })
    }
    return lista
  }, [q.data])
  return { ptts, carregando: q.isLoading, erro: esgotado ? ERRO_ORCAMENTO_ESGOTADO : q.error }
}
