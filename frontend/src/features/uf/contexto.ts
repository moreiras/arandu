// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { RedeTerritorioUf, MercadoGruposUf, CeticEstimativasUf, DemandaOfertaUf, ErbsUf, FustUf, QualidadeUf, ReclamacoesUf, ConsumidorUf, TransitoUf, RadarUf, ExposicaoUf, ProntidaoUf, HistoricoBloco, TerritorioUf, IXPIndexEntry, OperadoraRow, OperadoraPresenteUf, PerfilUf , CadastroMercadoUf } from '../../types/api'

export const RAIO_SEM_PTT_KM = 100

/** Município da UF com a distância ao PTT mais próximo (null se não há centróide). */
export interface MunicipioUf {
  ibge: string
  nome: string
  acessos: number
  operadores: number
  hhi: number
  kmPtt: number | null
  fibraPct?: number | null
  ptt?: string
}

/** O que um bloco da página de UF recebe. */
export interface UfCtx {
  uf: string
  ixps: IXPIndexEntry[]
  municipios: MunicipioUf[]
  /** Sem distância ao PTT em nenhum município (centróides ou PIX indisponíveis no servidor). */
  semCentroides: boolean
  totais: PerfilUf['totais']
  asns?: { quantidade: number; usuarios: number }
  /** Sediadas na UF (acessos no país). */
  operadoras: OperadoraRow[]
  operadorasTotal: number
  /** Com acesso declarado na UF, com os acessos na UF (UF-E2). */
  operadorasPresentes: OperadoraPresenteUf[]
  operadorasPresentesTotal: number
  mesReferencia?: string
  historico?: HistoricoBloco | null
  /** População, domicílios, penetração e mercado não visto da UF (`include=territorio`). */
  territorio?: TerritorioUf | null
  /** HHI por CNPJ e por grupo (inferido) da UF. */
  mercadoGrupos?: MercadoGruposUf | null
  /** IPv6 estimado, usuários atrás de ROV e dependência de trânsito. */
  redeTerritorio?: RedeTerritorioUf | null
  /** Estimativas da TIC Domicílios para a UF (`include=cetic`). */
  cetic?: CeticEstimativasUf | null
  /** Demanda × oferta de banda larga fixa da UF (`include=cetic`). */
  demandaOferta?: DemandaOfertaUf | null
  /** Estações do SMP licenciadas na UF (`include=erbs`). */
  erbs?: ErbsUf | null
  /** Compromissos do FUST na UF (`include=fust`). */
  fust?: FustUf | null
  /** Prontidão em segurança de roteamento da UF (`include=prontidao`). */
  prontidao?: ProntidaoUf | null
  /** RQUAL por prestadora, último ano, na UF (`include=qualidade`). */
  qualidade?: QualidadeUf | null
  /** Reclamações na Anatel na UF por ano e serviço (`include=reclamacoes`). */
  reclamacoes?: ReclamacoesUf | null
  /** Concentração do trânsito inferido dos ASNs com sede na UF (`include=transito`). */
  transito?: TransitoUf | null
  /** Cloudflare Radar agregado dos ASNs da UF, derivado (`include=radar`). */
  radar?: RadarUf | null
  /** Exposição de serviços agregada dos ASNs da UF já lidos, derivada (`include=exposicao`). */
  exposicao?: ExposicaoUf | null
  /** Reclamações finalizadas no Consumidor.gov.br (`include=consumidor`). */
  consumidor?: ConsumidorUf | null
  /** Empresas de telecom da UF (`/empresas/mercado?uf=`). */
  cadastro?: CadastroMercadoUf | null
}
