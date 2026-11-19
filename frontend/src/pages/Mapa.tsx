// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { lazy, Suspense } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ExplorerMap } from '../components/maps/ExplorerMap'
import { useActiveDate } from '../hooks/useSnapshot'
import { INDICADORES_FUST, INDICADORES_MUNICIPAIS, INDICADORES_REDE } from '../lib/indicadoresMapa'

const MapaMunicipios = lazy(() => import('../features/estados/MapaMunicipios'))
const TODOS = [...INDICADORES_MUNICIPAIS, ...INDICADORES_REDE, ...INDICADORES_FUST]

/**
 * `/mapa`: o explorador de camadas (redes, PTTs, prefixos, infraestrutura) e a vista
 * "Indicador municipal": os municípios coloridos por um dos indicadores normalizados (mercado, rede e FUST), o mesmo mapa da página de
 * Municípios. Estado em `?vista=`.
 */
export function Mapa() {
  const date = useActiveDate()
  const [params, setParams] = useSearchParams()
  const vista = params.get('vista') === 'indicador' ? 'indicador' : 'camadas'
  const trocar = (v: 'camadas' | 'indicador') => setParams((ant) => { const n = new URLSearchParams(ant); if (v === 'camadas') n.delete('vista'); else n.set('vista', v); return n })
  return (
    <>
      {/* Sem cabeçalho visível (o mapa ocupa a tela), mas a página precisa de um <h1> para quem navega por títulos (NBR 17225, 5.3). */}
      <h1 className="sr-only">Mapa da Internet no Brasil</h1>
      <div className="absolute left-1/2 top-2 z-20 -translate-x-1/2" role="group" aria-label="Vista do mapa">
        <div className="inline-flex overflow-hidden rounded-full border border-gray-300 bg-white/95 text-xs shadow">
          {([['camadas', 'Camadas'], ['indicador', 'Indicador municipal']] as const).map(([v, r]) => (
            <button key={v} type="button" aria-pressed={vista === v} onClick={() => trocar(v)}
              className={`min-h-[28px] px-3 py-1 ${vista === v ? 'bg-primario-600 text-white' : 'text-gray-700 hover:bg-gray-50'}`}>{r}</button>
          ))}
        </div>
      </div>
      {vista === 'camadas' ? <ExplorerMap date={date ?? undefined} /> : (
        <div className="h-full overflow-auto bg-gray-50 px-4 pb-6 pt-12">
          <div className="mx-auto max-w-6xl">
            <Suspense fallback={<p className="text-sm text-gray-500" role="status">Carregando o mapa dos municípios…</p>}>
              <MapaMunicipios indicadores={TODOS} titulo="Indicador municipal" />
            </Suspense>
          </div>
        </div>
      )}
    </>
  )
}
