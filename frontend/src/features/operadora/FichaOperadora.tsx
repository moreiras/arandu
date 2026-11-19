// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Kpi } from '../../components/ui'
import { DESCRICAO_SELO, ROTULO_SELO } from '../../components/entidade'
import type { OperadoraCtx } from './contexto'
import { kpisOperadora, REGRAS_VERSAO, sinteseOperadora } from './sintese'

const COR_SELO = { fato: 'bg-fato-600', inferido: 'bg-inferido-600', estimado: 'bg-estimado-600' } as const

/** Ficha-resumo da operadora: síntese por regras (sem IA) e os indicadores principais; fica acima das abas e some em `?versao=1`. */
export function FichaOperadora({ nome, ctx }: { nome: string; ctx: OperadoraCtx }) {
  const frases = sinteseOperadora(nome, ctx)
  const kpis = kpisOperadora(ctx).filter((k) => k.valor != null)
  return (
    <section aria-label="Resumo da operadora" className="rounded-lg border border-gray-200 bg-white p-4 space-y-3" data-testid="ficha-operadora">
      <ul className="space-y-1 text-sm text-gray-800">
        {frases.map((f) => (
          <li key={f.id} className="flex gap-2" data-testid={`frase-${f.id}`}>
            <span className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${COR_SELO[f.selo]}`} aria-hidden="true" />
            <span><span className="sr-only">{ROTULO_SELO[f.selo]}: </span>{f.texto}<span className="ml-1 text-xs text-gray-500" title={DESCRICAO_SELO[f.selo]}>({ROTULO_SELO[f.selo].toLowerCase()})</span></span>
          </li>
        ))}
      </ul>
      {kpis.length > 0 && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
          {kpis.map((k) => <Kpi key={k.id} rotulo={k.rotulo} valor={k.valor} referencia={k.referencia} />)}
        </div>
      )}
      <details className="text-xs text-gray-500">
        <summary className="cursor-pointer select-none">Como esta síntese é gerada</summary>
        <p className="mt-1 max-w-3xl">Frases montadas por regras fixas (versão <code>{REGRAS_VERSAO}</code>) a partir dos campos do snapshot, sem modelo de linguagem; o selo diz se é fato, inferência ou estimativa. Os acessos são declarados pela empresa à Anatel (SICI): a parcela é sobre acessos declarados, não sobre receita.</p>
      </details>
    </section>
  )
}
