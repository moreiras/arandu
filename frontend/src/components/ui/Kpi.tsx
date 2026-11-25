// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ReactNode } from 'react'
import { formatarReferencia, ROTULO_SELO, type Selo } from '../entidade/proveniencia'
import { Dica } from './Dica'

/**
 * Indicador (KPI): valor, rótulo, referência de comparação, variação e proveniência. Valor ausente aparece como "—" e nunca como zero.
 *
 * API de proveniência (PT-14, honestidade semântica do AGENTS.md):
 * - `selo`: natureza do dado, `'fato' | 'estimado' | 'inferido'` (definições em `DESCRICAO_SELO`, `entidade/proveniencia.ts`).
 *   Fato é declarado ou medido na fonte; estimado vem de amostragem ou modelo; inferido é derivado por regra.
 * - `fonte`: de onde vem o número, em texto curto ("APNIC Labs").
 * - `dataRef`: a data (AAAA-MM-DD) ou o mês (AAAA-MM) a que o número se refere, não a data da coleta.
 * Com qualquer um dos três, o KPI mostra a linha visível "Estimado · APNIC Labs · ref. 2026-11-15" sob o valor, em texto (nunca só
 * cor) e lida por leitor de tela; o `title` do valor repete fonte e data apenas como redundância. Número exibido sem selo, fonte
 * e data é exceção a justificar (ex.: contagem de um conjunto cuja fonte está no bloco). Sem estado do React no hover.
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

/** Data de referência na linha visível: dia ou mês em AAAA-MM-DD / AAAA-MM (o horário de um carimbo ISO não entra). */
function refVisivel(v: string): string {
  const m = /^(\d{4}-\d{2}(?:-\d{2})?)(?:$|T)/.exec(v)
  return m ? m[1] : v
}

export function Kpi({ rotulo, valor, referencia, variacao, selo, fonte, dataRef, tom, explicacao }: {
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
  /** Natureza do dado (fato, estimado ou inferido); aparece por extenso na linha de proveniência. */
  selo?: Selo
  fonte?: string
  /** Data ou mês a que o número se refere (AAAA-MM-DD ou AAAA-MM). */
  dataRef?: string | null
}) {
  const partes = [selo ? ROTULO_SELO[selo] : null, fonte || null, dataRef ? `ref. ${refVisivel(dataRef)}` : null].filter((p): p is string => !!p)
  const dica = fonte ? `Fonte: ${fonte}${dataRef ? ` · ref. ${formatarReferencia(dataRef)}` : ''}` : undefined
  const vazio = valor === null || valor === undefined || valor === ''
  return (
    <div className={`rounded-lg border border-gray-200 p-3 min-w-0 ${tom ? TONS[tom].caixa : 'bg-white'}`} data-testid="kpi" data-kpi-rotulo={rotulo}>
      <div className="text-xs text-gray-500">{rotulo}{explicacao && <Dica texto={explicacao} rotulo={rotulo} />}</div>
      <div className={`mt-0.5 text-titulo-2 tabular-nums ${tom ? TONS[tom].valor : 'text-gray-900'}`} title={dica} data-kpi-valor>{vazio ? '—' : valor}</div>
      {partes.length > 0 && (
        <p className="mt-0.5 text-xs text-gray-600" data-kpi-proveniencia data-kpi-selo={selo}>
          <span className="sr-only">Natureza, fonte e data de referência: </span>{partes.join(' · ')}
        </p>
      )}
      {(variacao || referencia) && (
        <div className="mt-0.5 flex flex-wrap gap-x-2 text-xs text-gray-500">
          {variacao && <span className={variacao.bom === undefined ? '' : variacao.bom ? 'text-ok-700' : 'text-perigo-700'}>{variacao.texto}</span>}
          {referencia && <span>{referencia}</span>}
        </div>
      )}
    </div>
  )
}
