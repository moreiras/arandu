// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { GrupoFontes, Kpi, ResumoEmTexto } from '../../components/ui'
import type { ASNDocument, ReferenciasAsn } from '../../types/api'
import { kpisAs, REGRAS_VERSAO, sinteseAs } from './sintese'

/**
 * Ficha-resumo do AS (PT-30): primeiro os indicadores, com a referência de comparação (posição e medianas entre os ASes brasileiros), e depois o
 * resumo em texto, gerado por regras versionadas, sem IA. Selos, fontes e datas dos cartões e das frases ficam num único bloco recolhido.
 * Fica acima das abas e some em `?versao=1`.
 */
export function FichaAsn({ doc, referencias }: { doc: ASNDocument; referencias?: ReferenciasAsn | null }) {
  const frases = sinteseAs(doc, referencias)
  return (
    <section aria-label="Resumo do AS" className="rounded-lg border border-gray-200 bg-white p-4 space-y-3" data-testid="ficha-as">
      <GrupoFontes snapshot={doc.snapshot_date}>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
          {kpisAs(doc, referencias).map((k) => (
            <Kpi key={k.id} rotulo={k.rotulo} valor={k.valor == null ? null : `${k.valor.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}${k.sufixo ?? ''}`} referencia={k.referencia} selo={k.selo} fonte={k.fonte} dataRef={doc.snapshot_date} />
          ))}
        </div>
        <ResumoEmTexto frases={frases} regras={REGRAS_VERSAO} notaComoLer="As referências comparam o AS com os ASes brasileiros que têm registro no Registro.br." />
      </GrupoFontes>
    </section>
  )
}
