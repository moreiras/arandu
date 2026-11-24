// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState, type ReactNode } from 'react'
import { ESCALA_SEQUENCIAL } from '../../lib/escalasMapa'
import { GradeUfs, POSICAO_UF } from './CartogramaUfs'

export interface IndicadorUf {
  id: string
  rotulo: string
  /** Valor da UF (null = sem dado ou suprimido). */
  valor: (uf: string) => number | null
  texto: (v: number) => string
  /** Teto da escala; sem ele, o maior valor das UFs. Percentuais usam 100 para a cor valer entre indicadores. */
  maximo?: number
  nota?: string
}

/**
 * Cartograma das UFs para um indicador de uma página temática, com a tabela completa recolhida em "Ver dados":
 * o mapa responde de relance, a tabela fica para quem precisa do número (e é a leitura de teclado e de leitor de tela,
 * já que as células da grade são decorativas).
 */
export function CartogramaIndicador({ titulo, indicadores, verDados, inicial }: { titulo?: string; indicadores: IndicadorUf[]; verDados?: ReactNode; inicial?: string }) {
  const [id, setId] = useState(inicial ?? indicadores[0]?.id)
  const ind = indicadores.find((i) => i.id === id) ?? indicadores[0]
  if (!ind) return null
  const valores = Object.keys(POSICAO_UF).map((uf) => ind.valor(uf)).filter((v): v is number => v != null)
  const maximo = ind.maximo ?? (valores.length ? Math.max(...valores) : 0)
  return (
    <div className="space-y-3" data-testid="cartograma-indicador">
      <div className="flex flex-wrap items-center justify-between gap-2">
        {titulo && <h3 className="text-sm font-semibold text-gray-700">{titulo}</h3>}
        {indicadores.length > 1 && (
          <div role="group" aria-label="Indicador do cartograma" className="inline-flex flex-wrap rounded-md border border-gray-200 overflow-hidden text-xs">
            {indicadores.map((i) => (
              <button key={i.id} type="button" aria-pressed={i.id === ind.id} onClick={() => setId(i.id)}
                className={`px-2.5 py-1 ${i.id === ind.id ? 'bg-primario-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}>{i.rotulo}</button>
            ))}
          </div>
        )}
      </div>
      <GradeUfs valores={ind.valor} maximo={maximo} texto={ind.texto} rotulo={ind.rotulo} />
      <div className="mx-auto max-w-md flex items-center gap-2 text-xs text-gray-500" aria-hidden="true">
        <span>0</span>
        <span className="h-2 flex-1 rounded" style={{ background: `linear-gradient(to right, ${ESCALA_SEQUENCIAL.join(', ')})` }} />
        <span>{maximo > 0 ? ind.texto(maximo) : '—'}</span>
      </div>
      {ind.nota && <p className="text-xs text-gray-600">{ind.nota}</p>}
      <p className="text-xs text-gray-500">Cada quadrado é uma UF no lugar aproximado do mapa (mesmo tamanho para todas). Cor do roxo (menor valor) ao amarelo (maior valor); cinza = sem dado ou suprimido.</p>
      {verDados && (
        <details className="text-sm">
          <summary className="cursor-pointer text-primario-600 hover:underline">Ver dados (tabela)</summary>
          <div className="mt-2">{verDados}</div>
        </details>
      )}
    </div>
  )
}
