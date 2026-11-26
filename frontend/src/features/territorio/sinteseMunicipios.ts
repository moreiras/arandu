// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ResumoTerritorio } from '../../types/api'
import { compacto, limitar, n0, palavra, pct1, plural, type FraseSintese } from '../../lib/sintese'
import { nomeUf } from '../../lib/ufs'

export const REGRAS_SINTESE_MUNICIPIOS = 'sintese-municipios-2'

const razao = (v: number) => v.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

/**
 * Síntese de `/municipios` (PT-22, municípios 5.2): frases dos agregados de `GET /territorio/resumo` (país ou UF), os mesmos números que a API devolve e que a lista soma. "Longe de PTT"
 * é dito como "a mais de 100 km em linha reta de um ponto de interconexão do IX.br", nunca "sem Internet"; a comparação de penetração entre os grupos é de médias e a frase diz que não
 * mede causa (renda, urbanização e densidade explicam parte). Grupo vazio ou razão nula não gera frase.
 */
export function sinteseMunicipios(r: ResumoTerritorio | null | undefined): FraseSintese[] {
  if (!r || r.total.municipios === 0) return []
  const { total, a_mais_de_100km: longe, ate_100km: perto, penetracao: p } = r
  const onde = r.escopo.uf ? ` na UF ${nomeUf(r.escopo.uf)}` : ''
  const ref = r.snapshot_date
  const FONTE_PTT = 'IBGE (população estimada, Censo 2022), SICI e PTTs do IX.br (distância em linha reta)'
  return limitar([
    longe.municipios > 0 && total.populacao_estimada > 0 && { id: 'longe', selo: 'estimado', fonte: FONTE_PTT, dataRef: ref,
      texto: `A mais de ${n0(r.raio_sem_ptt_km)} km em linha reta de um ponto de interconexão do IX.br${onde} vivem ${compacto(longe.populacao_estimada)} pessoas (${pct1((100 * longe.populacao_estimada) / total.populacao_estimada)} da população estimada), em ${plural(longe.municipios, 'município', 'municípios')}.` },
    longe.acessos_por_domicilio != null && perto.acessos_por_domicilio != null && { id: 'razao', selo: 'estimado', fonte: 'SICI, Anatel, e domicílios projetados (Censo 2022 e PNAD)', dataRef: r.mes_referencia_sici,
      texto: `Nesses municípios há ${razao(longe.acessos_por_domicilio)} acesso fixo declarado por domicílio projetado. Nos que ficam até ${n0(r.raio_sem_ptt_km)} km, são ${razao(perto.acessos_por_domicilio)}. A comparação é de médias entre os grupos e não mede causa.` },
    p.com_mais_acessos_que_domicilios > 0 && { id: 'acima-de-1', selo: 'estimado', fonte: 'SICI, Anatel, e domicílios projetados (Censo 2022 e PNAD)', dataRef: r.mes_referencia_sici,
      texto: `${n0(p.com_mais_acessos_que_domicilios)} ${p.com_mais_acessos_que_domicilios === 1 ? 'município' : 'municípios'} ${p.com_mais_acessos_que_domicilios === 1 ? 'tem' : 'têm'} mais acessos fixos declarados do que domicílios projetados; acesso não é domicílio (há acessos de empresas e mais de um acesso por domicílio).` },
    { id: 'cobertura', selo: 'fato', fonte: 'IBGE (tabela de municípios e Censo 2022)', dataRef: ref,
      texto: `A penetração foi calculada em ${n0(p.municipios_com_penetracao)} de ${n0(total.municipios)} ${palavra(total.municipios, 'município', 'municípios')}, os que têm ao menos ${n0(p.porte_minimo_domicilios)} domicílios. Outros ${n0(p.municipios_abaixo_do_porte)} ${palavra(p.municipios_abaixo_do_porte, 'tem', 'têm')} menos que isso, e ${n0(p.municipios_sem_domicilios)} ${palavra(p.municipios_sem_domicilios, 'não tem', 'não têm')} domicílios no Censo.` },
  ])
}
