// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useMemo } from 'react'
import { useQueries, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import { layerQuery } from './consulta'
import type { LayerData } from './consulta'
import type { LayerStatus } from './PainelCamadas'
import { FETCH_ORDER, LAYERS, LAYER_BY_ID, MAX_CONCURRENT } from './tipos'
import type { DataLayerId, LayerId, MapState } from './tipos'

/**
 * Busca por camada, em fila (menor → maior), com concorrência limitada. O PIX é sempre buscado (leve): as coordenadas servem ao
 * círculo de raio. Devolve também o status de cada camada (para o painel) e o tamanho do recorte.
 * `exportar` é chamado pelo botão de CSV (a página decide se exige login).
 */
export function useCamadasDados(
  state: MapState,
  debounced: MapState,
  date: string | undefined,
  exportar: (features: GeoJSON.Feature[], id: DataLayerId, snapshot: string) => void,
) {
  const queryClient = useQueryClient()
  const specs = FETCH_ORDER.map(id => {
    const { key, fn } = layerQuery(id, { ...debounced, on: state.on }, date)
    return { id, key, fn, active: id === 'pix' || state.on[id] }
  })
  let pendingAhead = 0
  const results = useQueries({
    queries: specs.map(sp => {
      const qs = queryClient.getQueryState(sp.key)
      const settled = qs?.status === 'success' || qs?.status === 'error'
      const enabled = sp.active && (settled || pendingAhead < MAX_CONCURRENT)
      if (sp.active && !settled) pendingAhead++
      return {
        queryKey: sp.key,
        queryFn: ({ signal }: { signal: AbortSignal }) => sp.fn(signal),
        enabled,
        staleTime: Infinity,
        gcTime: 10 * 60 * 1000,
        retry: 1,
        placeholderData: keepPreviousData,
      }
    }),
  })
  const resultById = Object.fromEntries(FETCH_ORDER.map((id, i) => [id, results[i]])) as
    Record<DataLayerId, (typeof results)[number]>

  const statuses = useMemo(() => {
    const out = {} as Record<LayerId, LayerStatus>
    for (const l of LAYERS) {
      const r = resultById[l.id as DataLayerId]
      if (!r) { out[l.id] = { state: state.on[l.id] ? 'done' : 'off', stale: false }; continue }
      const data = r.data as LayerData | undefined
      const count = data?.features.length
      let st: LayerStatus['state'] = 'off'
      if (state.on[l.id]) {
        if (r.isError && !r.isFetching) st = 'error'
        else if (r.isFetching) st = 'loading'
        else if (!data || r.isPlaceholderData) st = 'queued'
        else st = 'done'
      }
      out[l.id] = {
        state: st,
        count,
        stale: !!r.isPlaceholderData,
        retry: () => { r.refetch() },
        download: l.csv && data
          ? () => exportar(data.features, l.id as DataLayerId, data.snapshot_date ?? date ?? 'snapshot')
          : undefined,
      }
    }
    return out
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [results, state.on, date])

  // Tamanho do recorte: de qualquer camada com recorte já carregada
  const matchedAsns = useMemo(() => {
    for (const l of LAYERS) {
      if (!l.recorte || !state.on[l.id]) continue
      const r = resultById[l.id as DataLayerId]
      const m = (r?.data as LayerData | undefined)?.matched_asns
      if (m != null && !r.isPlaceholderData) return m
    }
    return undefined
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [results, state.on])

  const activeData = FETCH_ORDER.filter(id => state.on[id])
  const loadingLabels = activeData.filter(id => statuses[id].state === 'loading').map(id => LAYER_BY_ID[id].label)
  const doneCount = activeData.filter(id => statuses[id].state === 'done' || statuses[id].state === 'error').length
  const errors = activeData.filter(id => statuses[id].state === 'error')

  return { specs, results, resultById, statuses, matchedAsns, activeData, loadingLabels, doneCount, errors }
}
