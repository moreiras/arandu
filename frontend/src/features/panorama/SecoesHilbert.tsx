// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useLayoutEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchHilbertV4, fetchHilbertV6 } from '../../services/api'
import { useActiveDate } from '../../hooks/useSnapshot'
import { HilbertMap16, LAYER_META } from '../../components/hilbert/HilbertMap16'
import type { LayerKey } from '../../components/hilbert/HilbertMap16'
import { HilbertMapV6 } from '../../components/hilbert/HilbertMapV6'
import { corLegivel } from '../../lib/contraste'

/** Espaço IPv6 em curva de Hilbert (resolução /32), a mesma seção da Visão geral; só busca o dado quando é montada (aba aberta). */
export function SecaoHilbertV6() {
  const date = useActiveDate()
  const { data, isLoading } = useQuery({ queryKey: ['hilbert-v6', date], queryFn: () => fetchHilbertV6(date ?? undefined), staleTime: Infinity, gcTime: Infinity })
  return (
    <div>
      <h2 className="text-base font-semibold text-gray-800 mb-2">Espaço IPv6: curva de Hilbert (resolução /32)</h2>
      {isLoading ? <div className="h-48 bg-gray-100 rounded-lg animate-pulse" /> : <HilbertMapV6 data={data ?? null} blockWidth={220} />}
    </div>
  )
}

/** Espaço IPv4 em curva de Hilbert (resolução /16), com o seletor de camada e a legenda de cada uma (a seção da antiga Visão geral). */
export function SecaoHilbertV4() {
  const date = useActiveDate()
  const [activeLayer, setActiveLayer] = useState<LayerKey>('rir_br')
  const ref = useRef<HTMLDivElement>(null)
  const [largura, setLargura] = useState(380)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver((e) => setLargura(Math.min(Math.floor(e[0].contentRect.width), 380)))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  const { data, isLoading } = useQuery({ queryKey: ['hilbert-v4', date], queryFn: () => fetchHilbertV4(date ?? undefined), staleTime: Infinity, gcTime: Infinity })
  return (
    <div>
      <h2 className="text-base font-semibold text-gray-800 mb-2">Espaço IPv4: curva de Hilbert (resolução /16)</h2>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {(Object.keys(LAYER_META) as LayerKey[]).map((key) => {
          const meta = LAYER_META[key]
          const active = activeLayer === key
          return (
            <button key={key} type="button" onClick={() => setActiveLayer(key)} title={meta.description} aria-pressed={active}
              className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${active ? 'text-white border-transparent' : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400'}`}
              style={active ? { backgroundColor: corLegivel(meta.color), borderColor: corLegivel(meta.color) } : undefined}>
              {meta.label}
            </button>
          )
        })}
      </div>
      <p className="text-xs text-gray-500 mb-3 leading-relaxed border-l-2 pl-2" style={{ borderColor: LAYER_META[activeLayer].color }}>{LAYER_META[activeLayer].legend}</p>
      <div ref={ref}>
        {isLoading ? <div className="bg-gray-100 rounded-lg animate-pulse" style={{ height: largura }} /> : <HilbertMap16 data={data ?? null} activeLayer={activeLayer} width={largura} date={date ?? undefined} />}
      </div>
      <p className="text-xs text-gray-400 mt-1.5">Cada célula = bloco /16. A intensidade cresce com o número de /24 presentes; todo bloco com dado aparece, mesmo com um só /24. Clique em um bloco /8 destacado para ampliar.</p>
    </div>
  )
}
