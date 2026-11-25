// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { Selo } from '../components/entidade'
import type { MetodoQuebras } from './quebras'

/**
 * Indicador de mapa temático. **Normalização obrigatória**: todo indicador declara o denominador (`normalizacao`); valor absoluto sem
 * denominador não entra num coroplético (a área do município distorce a leitura). Os ids são os de `GET /territorio/mapa?indicador=`.
 */
export interface IndicadorMapa {
  id: string
  rotulo: string
  /** A fórmula em uma frase: o que é dividido pelo quê. */
  normalizacao: string
  unidade: string
  casas: number
  metodo: MetodoQuebras
  classes: number
  selo: Selo
  fontes: string[]
  /** Quanto maior, melhor/pior/neutro: orienta só a leitura da legenda; a escala de cor é sempre sequencial. */
  sentido: 'neutro' | 'mais-e-melhor' | 'mais-e-pior'
  /** O que significa a cor cinza, quando não é "sem dado" (ex.: município sem compromisso cadastrado). */
  semDado?: string
}

export const INDICADORES_MUNICIPAIS: IndicadorMapa[] = [
  { id: 'penetracao', rotulo: 'Acessos por 100 domicílios', normalizacao: 'acessos fixos declarados ÷ domicílios projetados × 100', unidade: 'acessos por 100 domicílios', casas: 0,
    metodo: 'quantis', classes: 5, selo: 'estimado', fontes: ['anatel_sici', 'ibge_censo_pnad'], sentido: 'mais-e-melhor' },
  { id: 'penetracao_pf', rotulo: 'Acessos de pessoa física por 100 domicílios', normalizacao: 'acessos fixos de pessoa física ÷ domicílios projetados × 100', unidade: 'acessos por 100 domicílios', casas: 0,
    metodo: 'quantis', classes: 5, selo: 'estimado', fontes: ['anatel_sici', 'ibge_censo_pnad'], sentido: 'mais-e-melhor' },
  { id: 'nao_visto_pct', rotulo: 'Domicílios sem acesso fixo de pessoa física (% dos domicílios, estimativa PNAD)', normalizacao: 'domicílios com internet sem acesso fixo de pessoa física ÷ domicílios projetados × 100 (estimativa que inclui quem usa só o celular)', unidade: '% dos domicílios', casas: 0,
    metodo: 'quantis', classes: 5, selo: 'estimado', fontes: ['anatel_sici', 'ibge_censo_pnad'], sentido: 'neutro' },
  { id: 'acessos_por_mil_hab', rotulo: 'Acessos por mil habitantes', normalizacao: 'acessos fixos declarados ÷ população estimada × 1.000', unidade: 'acessos por mil habitantes', casas: 0,
    metodo: 'quantis', classes: 5, selo: 'estimado', fontes: ['anatel_sici', 'ibge_censo_pnad'], sentido: 'mais-e-melhor' },
  { id: 'km_ptt', rotulo: 'Distância ao PTT mais próximo', normalizacao: 'distância em linha reta do centróide do município ao PTT do IX.br mais próximo', unidade: 'km', casas: 0,
    metodo: 'quantis', classes: 5, selo: 'fato', fontes: ['anatel_sici', 'curada_ixps'], sentido: 'mais-e-pior' },
]

/** Mapa do FUST: compromissos cadastrados por 10 mil habitantes; município sem compromisso fica sem cor. */
export const INDICADORES_FUST: IndicadorMapa[] = [
  { id: 'fust_por_10mil_hab', rotulo: 'Compromissos do FUST por 10 mil habitantes', normalizacao: 'compromissos de universalização cadastrados no FUST no município ÷ população × 10.000 (cadastro de obrigações, não desembolso)',
    unidade: 'compromissos por 10 mil habitantes', casas: 1, metodo: 'quantis', classes: 5, selo: 'fato', fontes: ['anatel_fust'], sentido: 'neutro', semDado: 'sem compromisso cadastrado' },
]

/** Rede no território: estimativa e inferência, com a suposição na normalização; município sem operadora com ASN e medida fica sem cor. */
export const INDICADORES_REDE: IndicadorMapa[] = [
  { id: 'ipv6_estimado_pct', rotulo: 'Acessos em IPv6 (estimativa, %)', normalizacao: 'acessos fixos × adoção de IPv6 do AS da operadora (APNIC) ÷ acessos com estimativa × 100; supõe a mesma adoção em todos os municípios da operadora',
    unidade: '% dos acessos', casas: 0, metodo: 'quantis', classes: 5, selo: 'estimado', fontes: ['anatel_sici', 'apnic_pop'], sentido: 'neutro', semDado: 'sem operadora com ASN e medida de IPv6' },
  { id: 'transito_unico_pct', rotulo: 'Acessos com um único provedor de trânsito (inferido, %)', normalizacao: 'acessos das operadoras cujos ASNs têm um só provedor de trânsito inferido ÷ acessos das operadoras com relação inferida × 100',
    unidade: '% dos acessos', casas: 0, metodo: 'quantis', classes: 5, selo: 'inferido', fontes: ['anatel_sici', 'caida_asrel'], sentido: 'neutro', semDado: 'sem operadora com relação de trânsito inferida' },
]

export const indicadorPorId = (id: string): IndicadorMapa | undefined => [...INDICADORES_MUNICIPAIS, ...INDICADORES_FUST, ...INDICADORES_REDE].find((i) => i.id === id)

export function formatarValor(v: number, i: IndicadorMapa): string {
  return v.toLocaleString('pt-BR', { maximumFractionDigits: i.casas, minimumFractionDigits: i.casas })
}
