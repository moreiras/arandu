// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Unidades da Federação (sigla → nome). */
export const UFS: Record<string, string> = {
  AC: 'Acre', AL: 'Alagoas', AP: 'Amapá', AM: 'Amazonas', BA: 'Bahia', CE: 'Ceará', DF: 'Distrito Federal', ES: 'Espírito Santo',
  GO: 'Goiás', MA: 'Maranhão', MT: 'Mato Grosso', MS: 'Mato Grosso do Sul', MG: 'Minas Gerais', PA: 'Pará', PB: 'Paraíba',
  PR: 'Paraná', PE: 'Pernambuco', PI: 'Piauí', RJ: 'Rio de Janeiro', RN: 'Rio Grande do Norte', RS: 'Rio Grande do Sul',
  RO: 'Rondônia', RR: 'Roraima', SC: 'Santa Catarina', SP: 'São Paulo', SE: 'Sergipe', TO: 'Tocantins',
}

export function nomeUf(sigla: string): string {
  return UFS[sigla.toUpperCase()] ?? sigla.toUpperCase()
}

/** Macro-regiões do IBGE, com as UFs de cada uma (ordem do IBGE para as regiões, alfabética pelo nome dentro delas). */
export const REGIOES: Array<{ id: string; nome: string; ufs: string[] }> = [
  { id: 'N', nome: 'Norte', ufs: ['AC', 'AP', 'AM', 'PA', 'RO', 'RR', 'TO'] },
  { id: 'NE', nome: 'Nordeste', ufs: ['AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE'] },
  { id: 'CO', nome: 'Centro-Oeste', ufs: ['DF', 'GO', 'MT', 'MS'] },
  { id: 'SE', nome: 'Sudeste', ufs: ['ES', 'MG', 'RJ', 'SP'] },
  { id: 'S', nome: 'Sul', ufs: ['PR', 'RS', 'SC'] },
]
