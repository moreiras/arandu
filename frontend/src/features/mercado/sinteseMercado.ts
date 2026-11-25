// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { SiciMovelStats, SiciStats } from '../../types/api'
import { limitar, n0, pct1, type FraseSintese } from '../../lib/sintese'

export const REGRAS_SINTESE_MERCADO = 'sintese-mercado-1'
const FONTE = 'SICI, Anatel (declarado pelas operadoras)'

/** Soma dos três maiores CNPJs em % do total declarado; nulo sem total ou com menos de três CNPJs (a regra é "três maiores"). */
export function parcelaTresMaiores(top: Array<{ acessos: number }> | undefined, total: number | undefined): number | null {
  if (!top || top.length < 3 || !total || total <= 0) return null
  const s = [...top].sort((a, b) => b.acessos - a.acessos).slice(0, 3).reduce((t, o) => t + o.acessos, 0)
  return (100 * s) / total
}

/**
 * Síntese do Panorama de mercado (PT-22, panorama-mercado 5.3): do que as seções de banda larga fixa e móvel já buscam (`/acessos/stats`, fixo e
 * móvel, mesma consulta e mesma chave). Cada serviço leva o próprio mês de referência e nunca se soma fixo com móvel. "Três maiores" é ranking nominal
 * implícito, por isso a regra (acessos declarados por CNPJ, sem agrupar por grupo) vai na própria frase e nenhuma empresa é nomeada.
 */
export function sinteseMercado(fixo: SiciStats | null | undefined, movel: SiciMovelStats | null | undefined): FraseSintese[] {
  const tres = parcelaTresMaiores(fixo?.top_operadoras, fixo?.total_acessos)
  return limitar([
    fixo && fixo.total_acessos > 0 && { id: 'fixo', selo: 'fato', fonte: FONTE, dataRef: fixo.mes_referencia,
      texto: `Foram declarados ${n0(fixo.total_acessos)} acessos de banda larga fixa ao SICI, por ${n0(fixo.operadoras_ativas)} CNPJs com acessos no mês de referência.` },
    tres != null && { id: 'tres-maiores', selo: 'fato', fonte: FONTE, dataRef: fixo?.mes_referencia,
      texto: `Os três CNPJs com mais acessos fixos declarados somam ${pct1(tres)} do total (regra: acessos declarados por CNPJ, sem agrupar por grupo econômico).` },
    movel && movel.total_acessos > 0 && { id: 'movel', selo: 'fato', fonte: FONTE, dataRef: movel.mes_referencia,
      texto: `Foram declaradas ${n0(movel.total_acessos)} linhas de banda larga móvel, sem M2M${movel.acessos_m2m != null ? `, e ${n0(movel.acessos_m2m)} acessos M2M à parte` : ''}.` },
  ])
}
