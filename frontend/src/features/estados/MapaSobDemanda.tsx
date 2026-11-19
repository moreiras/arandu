// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { lazy, Suspense, useState } from 'react'
import { INDICADORES_MUNICIPAIS, type IndicadorMapa } from '../../lib/indicadoresMapa'

const MapaMunicipios = lazy(() => import('./MapaMunicipios'))

/** O mapa dos municípios pesa cerca de 0,5 MB (MapLibre e tiles): só carrega quando a pessoa pede (orçamento de página). */
export function MapaSobDemanda({ indicadores = INDICADORES_MUNICIPAIS, titulo = 'Mapa dos municípios', chamada = 'Os 5.571 municípios coloridos por um indicador normalizado, ou dois indicadores comparados. Carrega cerca de 0,5 MB.' }: { indicadores?: IndicadorMapa[]; titulo?: string; chamada?: string }) {
  const [aberto, setAberto] = useState(false)
  if (!aberto) {
    return (
      <section aria-labelledby="mapa-mun-chamada" className="rounded-lg border border-gray-200 bg-white p-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="mapa-mun-chamada" className="text-base font-semibold text-gray-800">{titulo}</h2>
          <p className="text-sm text-gray-500">{chamada}</p>
        </div>
        <button type="button" onClick={() => setAberto(true)} className="rounded-md bg-primario-600 px-3 py-1.5 text-sm text-white hover:bg-primario-700">Mostrar o mapa</button>
      </section>
    )
  }
  return <Suspense fallback={<p className="text-sm text-gray-400" role="status">Carregando o mapa dos municípios…</p>}><MapaMunicipios indicadores={indicadores} titulo={titulo} /></Suspense>
}
