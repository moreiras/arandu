// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { FraseSintese } from '../../lib/sintese'
import { MAX_FRASES, MIN_FRASES } from '../../lib/sintese'
import { LinhaProveniencia } from './Kpi'

/**
 * Síntese em texto no topo da página (PT-22): de duas a quatro frases geradas por regra a partir dos números exibidos na própria página, cada uma
 * com a linha de proveniência dos KPIs (selo por extenso, fonte e data de referência; o selo nunca depende só de cor). Sem frases suficientes o
 * bloco não aparece. `aoVivo` marca a região como `role="status"` (o localizador a atualiza a cada mudança de ponto ou raio).
 */
export function SinteseTopo({ frases, snapshot, regras, rotulo = 'Em resumo', aoVivo = false, comoLer, minFrases = MIN_FRASES }: {
  frases: FraseSintese[]
  snapshot?: string | null
  /** Identificador da versão das regras de montagem das frases (muda quando uma regra muda). */
  regras: string
  rotulo?: string
  aoVivo?: boolean
  /** Uma frase de "Como ler" específica da página, depois da nota fixa. */
  comoLer?: string
  /** Mínimo de frases para mostrar o bloco (duas por padrão; o localizador mostra uma só quando o raio está vazio). */
  minFrases?: number
}) {
  if (frases.length < minFrases) return null
  const lista = frases.slice(0, MAX_FRASES)
  return (
    <section aria-label={rotulo} className="rounded-lg border border-gray-200 bg-white p-4 space-y-2" data-testid="sintese-topo" {...(aoVivo ? { role: 'status', 'aria-live': 'polite' as const } : {})}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4">
        <h2 className="text-sm font-semibold text-gray-800">{rotulo}</h2>
        {snapshot && <span className="text-xs text-gray-600">Snapshot <span className="font-mono">{snapshot}</span></span>}
      </div>
      <ul className="space-y-2">
        {lista.map((f) => (
          <li key={f.id} data-testid={`sintese-${f.id}`}>
            <p className="text-sm text-gray-900">{f.texto}</p>
            <LinhaProveniencia selo={f.selo} fonte={f.fonte} dataRef={f.dataRef} className="text-xs text-gray-600" />
          </li>
        ))}
      </ul>
      <p className="text-xs text-gray-600 max-w-[90ch]">
        Frases geradas por regra fixa (versão <code>{regras}</code>) a partir dos números desta página; descrevem, não explicam causas.{comoLer ? ` ${comoLer}` : ''}
      </p>
    </section>
  )
}
