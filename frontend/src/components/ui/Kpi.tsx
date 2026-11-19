// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ReactNode } from 'react'
import { formatarReferencia } from '../entidade/proveniencia'
import { Dica } from './Dica'

/**
 * Indicador (KPI): valor, rótulo, referência de comparação, variação e fonte. A fonte e a data ficam no tooltip nativo do
 * valor (sem estado do React no hover). Valor ausente aparece como "—" e nunca como zero.
 */
/** Acentos sóbrios por tipo de indicador: faixa lateral e fundo suaves, valor em tom escuro (contraste AA conferido em `tokens.test.ts`). */
const TONS = {
  primario: { caixa: 'border-l-4 border-l-primario-500 bg-primario-50/60', valor: 'text-primario-800' },
  v4: { caixa: 'border-l-4 border-l-v4-500 bg-v4-50/60', valor: 'text-v4-800' },
  v6: { caixa: 'border-l-4 border-l-v6-500 bg-v6-50/60', valor: 'text-v6-800' },
  mercado: { caixa: 'border-l-4 border-l-mercado-500 bg-mercado-50/60', valor: 'text-mercado-800' },
  tecnico: { caixa: 'border-l-4 border-l-tecnico-500 bg-tecnico-50/60', valor: 'text-tecnico-800' },
  estimado: { caixa: 'border-l-4 border-l-estimado-500 bg-estimado-50/60', valor: 'text-estimado-800' },
  ok: { caixa: 'border-l-4 border-l-ok-500 bg-ok-50/60', valor: 'text-ok-800' },
} as const
export type TomKpi = keyof typeof TONS

export function Kpi({ rotulo, valor, referencia, variacao, fonte, dataRef, tom, explicacao }: {
  /** Acento de cor (opcional): identifica o tipo do indicador sem depender só da cor, pois o rótulo e o valor continuam sendo o conteúdo. */
  tom?: TomKpi
  rotulo: string
  /** O que o indicador mede, em uma ou duas frases (T2): abre num ⓘ ao lado do rótulo. */
  explicacao?: ReactNode
  valor: ReactNode
  /** Termo de comparação, ex.: "mediana da UF: 42%". */
  referencia?: string
  /** Variação já formatada, com sinal, ex.: "+3,1 p.p."; `bom` pinta de verde ou vermelho (omita se o sentido não é bom nem ruim). */
  variacao?: { texto: string; bom?: boolean }
  fonte?: string
  dataRef?: string | null
}) {
  const dica = fonte ? `Fonte: ${fonte}${dataRef ? ` · ref. ${formatarReferencia(dataRef)}` : ''}` : undefined
  const vazio = valor === null || valor === undefined || valor === ''
  return (
    <div className={`rounded-lg border border-gray-200 p-3 min-w-0 ${tom ? TONS[tom].caixa : 'bg-white'}`} data-testid="kpi">
      <div className="text-xs text-gray-500">{rotulo}{explicacao && <Dica texto={explicacao} rotulo={rotulo} />}</div>
      <div className={`mt-0.5 text-titulo-2 tabular-nums ${tom ? TONS[tom].valor : 'text-gray-900'}`} title={dica}>{vazio ? '—' : valor}</div>
      {(variacao || referencia) && (
        <div className="mt-0.5 flex flex-wrap gap-x-2 text-xs text-gray-500">
          {variacao && <span className={variacao.bom === undefined ? '' : variacao.bom ? 'text-ok-700' : 'text-perigo-700'}>{variacao.texto}</span>}
          {referencia && <span>{referencia}</span>}
        </div>
      )}
    </div>
  )
}
