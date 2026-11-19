// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { Regiao, ErbsMunicipio, FustMunicipio, QualidadeMunicipio, ReclamacoesMunicipio, ConsumidorMunicipio, IndicadoresMunicipio, TerritorioMunicipio, MovelMunicipioDetalhe, SiciMunicipioDetalhe, ContratosMunicipio, SerieMercadoMunicipio, MercadoGruposMunicipio, RedeTerritorioMunicipio } from '../../types/api'
import type { LonLat, PontoProximo } from '../../lib/geo'

/** O que um bloco da página de município recebe: os dois detalhes do SICI, o centróide e os PTTs mais próximos (já com a distância). */
export interface MunicipioCtx {
  ibge: string
  fixo?: SiciMunicipioDetalhe
  movel?: MovelMunicipioDetalhe
  centroide?: LonLat
  /** Variação, líder e ganho/perda em 12 meses (`include=indicadores`). */
  indicadores?: IndicadoresMunicipio | null
  /** Série mensal de acessos, HHI e participação das maiores operadoras (`include=serie_mercado`). */
  serieMercado?: SerieMercadoMunicipio | null
  /** HHI por CNPJ e por grupo (inferido) do município. */
  mercadoGrupos?: MercadoGruposMunicipio | null
  /** IPv6 estimado e dependência de trânsito. */
  redeTerritorio?: RedeTerritorioMunicipio | null
  /** População, domicílios, penetração e mercado não visto (`include=territorio`). */
  territorio?: TerritorioMunicipio | null
  /** Estações do SMP licenciadas no município (`include=erbs`). */
  erbs?: ErbsMunicipio | null
  /** Compromissos do FUST no município (`include=fust`). */
  fust?: FustMunicipio | null
  /** Último resultado do RQUAL no município (`include=qualidade`); fora da soma por raio. */
  qualidade?: QualidadeMunicipio | null
  /** Reclamações na Anatel no município (`include=reclamacoes`); fora da soma por raio. */
  reclamacoes?: ReclamacoesMunicipio | null
  /** Reclamações finalizadas no Consumidor.gov.br (`include=consumidor`). */
  consumidor?: ConsumidorMunicipio | null
  /** Operadoras com contratação de órgão sediado no município, PNCP em rodízio (`/contratos/municipios/{ibge}`). Só o município central, mesmo com raio. */
  contratos?: ContratosMunicipio | null
  /** Os 5 PTTs mais próximos (km em linha reta do centróide); vazio se não há centróide ou PIX. */
  proximos: PontoProximo[]
  carregandoPtts: boolean
  /** ASNs do município ou do conjunto: provedores, PTTs, trânsito e carregadores (`GET /regiao`). */
  regiao?: Regiao | null
  /** Presente quando a página soma um raio de municípios: quantos entram e qual é o central. */
  conjunto?: { n: number; central: string }
}

export const RAIO_PTT_PROXIMO_KM = 100
