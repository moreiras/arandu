// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** ASNs que não identificam uma rede na Internet pública. O cadastro do IX.br traz alguns (ex.: AS65000), e não há página para eles. */

const FAIXAS: [number, number, string][] = [
  [0, 0, 'ASN reservado (RFC 7607)'],
  [23456, 23456, 'AS_TRANS (RFC 6793)'],
  [64496, 64511, 'ASN de documentação (RFC 5398)'],
  [64512, 65534, 'ASN privado (RFC 6996)'],
  [65535, 65535, 'ASN reservado (RFC 7300)'],
  [65536, 65551, 'ASN de documentação (RFC 5398)'],
  [4200000000, 4294967294, 'ASN privado (RFC 6996)'],
  [4294967295, 4294967295, 'ASN reservado (RFC 7300)'],
]

/** Descrição da faixa especial do ASN, ou null se for um ASN público. */
export function asnEspecial(asn: number): string | null {
  for (const [ini, fim, rotulo] of FAIXAS) if (asn >= ini && asn <= fim) return rotulo
  return null
}
