// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useRef, type ReactNode } from 'react'
import { formatarReferencia, ROTULO_SELO, type Selo } from '../entidade/proveniencia'
import { Dica } from './Dica'
import { useEmGrupoFontes, useRegistrarFontes } from './FontesEDatas'
import { aspectoDoSelo } from '../../lib/paletaSelos'
import { CLASSES_CARTAO_COM_DICA, SeloDica } from './SeloDica'

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
 *
 * PT-30: dentro de um `GrupoFontes` (`FontesEDatas.tsx`) o cartão mostra só o selo (forma e cor, sem letra) no canto superior direito,
 * um botão com nome acessível e uma dica de fonte e data (`SeloDica`), e entrega fonte e data ao bloco recolhido "Fontes e datas
 * destes números" da seção, que agrega e deduplica. O fundo e a faixa lateral seguem a cor do selo, alternando com branco e cinza
 * (`lib/paletaSelos.ts`). Fora de um grupo, nada muda.
 */
/** Acentos sóbrios por tipo de indicador: faixa lateral e fundo suaves; o valor é sempre neutro (PT-30), pois cor no número sugere juízo. */
const TONS = {
  primario: { caixa: 'border-l-4 border-l-primario-500 bg-primario-50/60', valor: 'text-gray-900' },
  v4: { caixa: 'border-l-4 border-l-v4-500 bg-v4-50/60', valor: 'text-gray-900' },
  v6: { caixa: 'border-l-4 border-l-v6-500 bg-v6-50/60', valor: 'text-gray-900' },
  mercado: { caixa: 'border-l-4 border-l-mercado-500 bg-mercado-50/60', valor: 'text-gray-900' },
  tecnico: { caixa: 'border-l-4 border-l-tecnico-500 bg-tecnico-50/60', valor: 'text-gray-900' },
  estimado: { caixa: 'border-l-4 border-l-estimado-500 bg-estimado-50/60', valor: 'text-gray-900' },
  ok: { caixa: 'border-l-4 border-l-ok-500 bg-ok-50/60', valor: 'text-gray-900' },
} as const
export type TomKpi = keyof typeof TONS

/** Data de referência na linha visível: dia ou mês em AAAA-MM-DD / AAAA-MM (o horário de um carimbo ISO não entra). */
function refVisivel(v: string): string {
  const m = /^(\d{4}-\d{2}(?:-\d{2})?)(?:$|T)/.exec(v)
  return m ? m[1] : v
}

/** Texto da linha de proveniência ("Estimado · APNIC Labs · ref. 2026-11-15"); vazio sem selo, fonte e data. */
export function textoProveniencia(selo?: Selo, fonte?: string, dataRef?: string | null): string {
  return [selo ? ROTULO_SELO[selo] : null, fonte || null, dataRef ? `ref. ${refVisivel(dataRef)}` : null].filter((p): p is string => !!p).join(' · ')
}

/** A linha de proveniência do `Kpi`, para os indicadores de outro desenho (faixas de números grandes) que não usam o `Kpi` comum. */
export function LinhaProveniencia({ selo, fonte, dataRef, className = 'mt-0.5 text-xs text-gray-600' }: { selo?: Selo; fonte?: string; dataRef?: string | null; className?: string }) {
  const texto = textoProveniencia(selo, fonte, dataRef)
  if (!texto) return null
  return (
    <p className={className} data-kpi-proveniencia data-kpi-selo={selo}>
      <span className="sr-only">Natureza, fonte e data de referência: </span>{texto}
    </p>
  )
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
  /** Variação já formatada, com sinal, ex.: "+3,1 p.p."; `bom` é aceito por compatibilidade, mas não pinta mais (PT-30: sem verde nem vermelho de juízo). */
  variacao?: { texto: string; bom?: boolean }
  /** Natureza do dado (fato, estimado ou inferido); aparece por extenso na linha de proveniência. */
  selo?: Selo
  fonte?: string
  /** Data ou mês a que o número se refere (AAAA-MM-DD ou AAAA-MM). */
  dataRef?: string | null
}) {
  const emGrupo = useEmGrupoFontes()
  const vazio = valor === null || valor === undefined || valor === ''
  useRegistrarFontes(emGrupo && !vazio && (selo || fonte || dataRef) ? [{ selo, fonte, dataRef }] : [])
  const cartao = useRef<HTMLDivElement>(null)
  const seloDoCartao = emGrupo && !vazio ? selo : undefined
  const aspecto = seloDoCartao ? aspectoDoSelo(seloDoCartao) : null
  const dica = !emGrupo && fonte ? `Fonte: ${fonte}${dataRef ? ` · ref. ${formatarReferencia(dataRef)}` : ''}` : undefined
  return (
    <div
      ref={cartao}
      className={`rounded-lg border border-gray-200 p-3 min-w-0 ${aspecto ? `${CLASSES_CARTAO_COM_DICA} border-l-4 bg-white ${aspecto.classes.faixa} ${aspecto.classes.fundoCiclo}` : tom ? TONS[tom].caixa : 'bg-white'}`}
      data-testid="kpi"
      data-kpi-rotulo={rotulo}
    >
      <div className={`text-xs text-gray-600 ${aspecto ? 'pr-6' : ''}`}>{rotulo}{explicacao && <Dica texto={explicacao} rotulo={rotulo} />}</div>
      <div className={`mt-0.5 text-titulo-2 tabular-nums ${tom ? TONS[tom].valor : 'text-gray-900'}`} title={dica} data-kpi-valor>{vazio ? '—' : valor}</div>
      {emGrupo
        ? seloDoCartao && <span data-kpi-proveniencia data-kpi-selo={seloDoCartao}><SeloDica selo={seloDoCartao} fonte={fonte} dataRef={dataRef} cartao={cartao} /></span>
        : <LinhaProveniencia selo={selo} fonte={fonte} dataRef={dataRef} />}
      {(variacao || referencia) && (
        <div className="mt-0.5 flex flex-wrap gap-x-2 text-xs text-gray-600">
          {variacao && <span>{variacao.texto}</span>}
          {referencia && <span>{referencia}</span>}
        </div>
      )}
    </div>
  )
}
