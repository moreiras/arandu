// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { SobreposicaoOperadora, HistoricoBloco, ErbsOperadora, MultasOperadora, ProntidaoOperadora, IndicadoresOperadora, QualidadeOperadora, ReclamacoesOperadora, ConsumidorOperadora, OperadoraDetalhe, OperadoraMovelDetalhe, OperadoraRede, STFCDetailResponse, SEACDetailResponse , CadastroOperadora, FinanciamentoOperadora, ContratosOperadora, SCMRecord } from '../../types/api'
import { servicosDaOperadora, temOutorga, type FontesServicos, type ServicoOperadora } from './servicos'

/** O que um bloco da página de operadora recebe: as quatro respostas (SCM/SICI, SMP/SICI móvel, STFC, SeAC) e o que a página deriva delas. */
export interface OperadoraCtx {
  data?: OperadoraDetalhe
  dataMovel?: OperadoraMovelDetalhe
  dataStfc?: STFCDetailResponse
  dataSeac?: SEACDetailResponse
  rede?: OperadoraRede | null
  cnpjFinal: string
  hasScm: boolean
  hasSici: boolean
  hasStfc: boolean
  hasSeac: boolean
  /** Serviços pelo cadastro de outorgas (`servicosDaOperadora`): a única fonte para dizer que a empresa tem outorga. */
  servicos: ServicoOperadora[]
  b2cPct: number
  historico?: HistoricoBloco | null
  /** Parcela, posição, variações e a situação da declaração ao SICI (`include=indicadores`). */
  indicadores?: IndicadoresOperadora | null
  /** Operadoras que mais aparecem nos mesmos municípios. */
  sobreposicao?: SobreposicaoOperadora | null
  /** Estações do SMP licenciadas da operadora (`include=erbs`). */
  erbs?: ErbsOperadora | null
  /** Multas constituídas da Anatel contra a empresa (`include=multas`). */
  multas?: MultasOperadora | null
  /** Prontidão em segurança de roteamento dos ASNs da operadora (`include=prontidao`). */
  prontidao?: ProntidaoOperadora | null
  /** RQUAL das prestadoras ligadas ao CNPJ (`include=qualidade`). */
  qualidade?: QualidadeOperadora | null
  /** Reclamações das marcas ligadas ao CNPJ (`include=reclamacoes`). */
  reclamacoes?: ReclamacoesOperadora | null
  /** Reclamações finalizadas no Consumidor.gov.br (`include=consumidor`). */
  consumidor?: ConsumidorOperadora | null
  /** Cadastro de telecom da Receita × SICI: matriz, estabelecimentos e presença física (`/empresas/operadoras/{cnpj}`). */
  cadastro?: CadastroOperadora | null
  /** Crédito público (BNDES) e sanções (CEIS/CNEP) da operadora (`/financiamento/operadoras/{cnpj}`). */
  financiamento?: FinanciamentoOperadora | null
  /** Contratos públicos (PNCP) da operadora, em rodízio de coleta (`/contratos/operadoras/{cnpj}`). */
  contratos?: ContratosOperadora | null
}

/** O que a página e o relatório derivam das respostas, pela mesma regra: outorga só com registro de outorga (`servicosDaOperadora`),
 * SICI só com acessos declarados, B2C sobre os acessos fixos declarados. */
export function derivarOperadora(f: Omit<FontesServicos, 'data'> & { data?: { outorgas_scm?: SCMRecord[]; acessos?: number | null; pf?: number | null } | null }) {
  const servicos = servicosDaOperadora(f)
  const acessos = f.data?.acessos
  const hasSici = acessos != null
  return {
    servicos,
    hasScm: temOutorga(servicos, 'SCM'),
    hasSmp: temOutorga(servicos, 'SMP'),
    hasStfc: temOutorga(servicos, 'STFC'),
    hasSeac: temOutorga(servicos, 'SeAC'),
    hasSici,
    b2cPct: hasSici && acessos ? (100 * (f.data?.pf ?? 0)) / acessos : 0,
  }
}
