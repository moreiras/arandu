// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { GrupoFontes, Kpi, ResumoEmTexto } from '../../components/ui'
import type { OperadoraCtx } from './contexto'
import { kpisOperadora, REGRAS_VERSAO, sinteseOperadora } from './sintese'

/**
 * Ficha-resumo da operadora (PT-30): primeiro os indicadores principais e depois o resumo em texto, por regras fixas e sem IA. Selos, fontes e
 * datas ficam num único bloco recolhido. Fica acima das abas e some em `?versao=1`.
 */
export function FichaOperadora({ nome, ctx }: { nome: string; ctx: OperadoraCtx }) {
  const frases = sinteseOperadora(nome, ctx)
  const kpis = kpisOperadora(ctx).filter((k) => k.valor != null)
  const snapshot = ctx.data?.snapshot_date ?? ctx.dataMovel?.snapshot_date ?? null
  return (
    <section aria-label="Resumo da operadora" className="rounded-lg border border-gray-200 bg-white p-4 space-y-3" data-testid="ficha-operadora">
      <GrupoFontes snapshot={snapshot}>
        {kpis.length > 0 && (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
            {kpis.map((k) => <Kpi key={k.id} rotulo={k.rotulo} valor={k.valor} referencia={k.referencia} selo={k.selo} fonte={k.fonte} dataRef={k.dataRef} />)}
          </div>
        )}
        <ResumoEmTexto frases={frases} regras={REGRAS_VERSAO} notaComoLer="Os acessos são os que a empresa declara à Anatel pelo SICI, e a parcela é calculada sobre os acessos declarados, não sobre a receita." />
      </GrupoFontes>
    </section>
  )
}
