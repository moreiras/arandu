// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Kpi } from '../../components/ui'
import { DESCRICAO_SELO, ROTULO_SELO } from '../../components/entidade'
import type { ASNDocument, ReferenciasAsn } from '../../types/api'
import { kpisAs, REGRAS_VERSAO, sinteseAs } from './sintese'

const COR_SELO = { fato: 'bg-fato-600', inferido: 'bg-inferido-600', estimado: 'bg-estimado-600' } as const

/**
 * Ficha-resumo do AS: a síntese em frases (regras versionadas, sem IA, cada uma com selo) e os indicadores com a referência de comparação
 * (posição e medianas entre os ASes brasileiros). Fica acima das abas e some em `?versao=1`.
 */
export function FichaAsn({ doc, referencias }: { doc: ASNDocument; referencias?: ReferenciasAsn | null }) {
  const frases = sinteseAs(doc, referencias)
  return (
    <section aria-label="Resumo do AS" className="rounded-lg border border-gray-200 bg-white p-4 space-y-3" data-testid="ficha-as">
      <ul className="space-y-1 text-sm text-gray-800">
        {frases.map((f) => (
          <li key={f.id} className="flex gap-2" data-testid={`frase-${f.id}`}>
            <span className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${COR_SELO[f.selo]}`} aria-hidden="true" />
            <span><span className="sr-only">{ROTULO_SELO[f.selo]}: </span>{f.texto}<span className="ml-1 text-xs text-gray-500" title={DESCRICAO_SELO[f.selo]}>({ROTULO_SELO[f.selo].toLowerCase()})</span></span>
          </li>
        ))}
      </ul>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
        {kpisAs(doc, referencias).map((k) => (
          <Kpi key={k.id} rotulo={k.rotulo} valor={k.valor == null ? null : `${k.valor.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}${k.sufixo ?? ''}`} referencia={k.referencia} selo={k.selo} fonte={k.fonte} dataRef={doc.snapshot_date} />
        ))}
      </div>
      <details className="text-xs text-gray-500">
        <summary className="cursor-pointer select-none">Como esta síntese é gerada</summary>
        <p className="mt-1 max-w-3xl">
          Frases montadas por regras fixas (versão <code>{REGRAS_VERSAO}</code>) a partir dos campos do snapshot, sem modelo de linguagem. O selo diz se a frase é um fato
          observado, uma inferência ou uma estimativa; regra sem dado não gera frase. As referências comparam com os ASes brasileiros com registro no Registro.br.
        </p>
      </details>
    </section>
  )
}
