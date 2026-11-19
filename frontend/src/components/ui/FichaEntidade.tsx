// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ReactNode } from 'react'
import { EntityHeader, type SeloServico } from '../entidade/EntityHeader'
import { Kpi } from './Kpi'

export interface KpiFicha { rotulo: string; valor: ReactNode; referencia?: string; variacao?: { texto: string; bom?: boolean }; fonte?: string; dataRef?: string | null }

/**
 * Ficha de uma entidade: cabeçalho (`EntityHeader`), frase-síntese opcional (com o selo de como foi obtida), grade de KPIs
 * (2 colunas no celular) e um espaço para o mini-mapa ou gráfico. É a parte fixa de cima do modelo de página do 1.6.6.
 */
export function FichaEntidade({ tipo, nome, trilha, identificadores, selos, ladoDoNome, snapshot, acoes, sintese, kpis, destaque }: {
  tipo?: string
  nome: string
  trilha?: ReactNode
  identificadores?: { rotulo: string; valor: string }[]
  selos?: SeloServico[]
  ladoDoNome?: ReactNode
  snapshot?: string | null
  acoes?: ReactNode
  /** Frase gerada por regras: texto, selo e a regra que a produziu. */
  sintese?: { texto: string; selo: 'fato' | 'inferido'; regra?: string }
  kpis?: KpiFicha[]
  destaque?: ReactNode
}) {
  return (
    <div className="space-y-3">
      <EntityHeader tipo={tipo} nome={nome} trilha={trilha} identificadores={identificadores} selos={selos} ladoDoNome={ladoDoNome} snapshot={snapshot} acoes={acoes} />
      {sintese && (
        <p className="text-gray-700" data-testid="sintese" title={sintese.regra ? `Regra: ${sintese.regra}` : undefined}>
          {sintese.texto} <span className="ml-1 rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">{sintese.selo === 'fato' ? 'Fato' : 'Inferido'}</span>
        </p>
      )}
      {(kpis?.length || destaque) && (
        <div className="grid gap-3 md:grid-cols-[1fr_minmax(0,18rem)]">
          {kpis && kpis.length > 0 && <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">{kpis.map((k) => <Kpi key={k.rotulo} {...k} />)}</div>}
          {destaque && <div className="min-w-0">{destaque}</div>}
        </div>
      )}
    </div>
  )
}
