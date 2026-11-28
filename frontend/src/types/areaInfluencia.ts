// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

// Área de influência observada dos PTTs (`/ixps/area-influencia`, `/ixps/{code}/area-influencia`).
export type VisaoArea = 'diretos' | 'todos'
/** Visões de um PTT: as duas de influência provável (com disputa entre PTTs) e as duas de alcance (sem disputa; só por PTT). */
export type VisaoAreaPtt = VisaoArea | 'alcance_diretos' | 'alcance_todos'
export interface AreaInfluenciaFaixaTotais { municipios: number; acessos: number }
/** Um PTT numa visão: P50, P80 e P90 da distância (km, ponderada por acessos), mediana por operadora e municípios por faixa. */
export interface AreaInfluenciaVisao {
  operadoras: number; municipios: number; acessos: number
  p50_km: number; p80_km: number; p90_km: number; mediana_operadora_km: number
  faixas: { ate_p50: AreaInfluenciaFaixaTotais; p50_a_p80: AreaInfluenciaFaixaTotais; alem_p80: AreaInfluenciaFaixaTotais }
  /** IBGE → [acessos atribuídos ao PTT, faixa 1 a 3]. */
  municipios_faixa: Record<string, [number, number]>
}
export interface AreaInfluenciaMeta {
  snapshot_date: string; natureza: string; limites: string; metodo: Record<string, string | Record<string, string>>
  fontes: { sici: string | null; ptts: string; pix: string; centroides: string }
  faixas: Record<string, string>
}
export interface AreaInfluenciaTotais { acessos: number; acessos_atribuidos: number; acessos_sem_ptt: number; acessos_sem_centroide: number; cnpjs_com_varios_asns: number }
export interface AreaInfluenciaPix { total: number; coordenada: number; endereco: number; sede: number; aproximado: boolean; pontos: Array<[number, number, 'coordenada' | 'endereco' | 'sede']> }
export interface AreaInfluenciaPtt extends AreaInfluenciaMeta {
  ixp: string; nome: string; uf: string; pix: AreaInfluenciaPix
  totais: Partial<Record<VisaoArea, AreaInfluenciaTotais>>
  visoes: Partial<Record<VisaoAreaPtt, AreaInfluenciaVisao | null>>
  /** IBGE → "Nome/UF" dos municípios das listas. */
  municipios_nomes: Record<string, string>
}
export interface AreaInfluenciaResumoPtt extends Omit<AreaInfluenciaVisao, 'municipios_faixa'> { nome: string; uf: string; pix_aproximado: boolean; ponto: [number, number] | null }
export interface AreaInfluenciaNacional extends AreaInfluenciaMeta {
  visao: VisaoArea; rotulo_visao: string
  campos_municipio: string[]
  total: AreaInfluenciaTotais
  ptts_com_pix_aproximado: string[]
  ptts: Record<string, AreaInfluenciaResumoPtt>
  /** IBGE → [PTT principal, faixa nele, acessos atribuídos ao principal, acessos atribuídos no município, nº de PTTs]. */
  municipios: Record<string, [string, number, number, number, number]>
}
