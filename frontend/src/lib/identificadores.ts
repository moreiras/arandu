// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

/** Identificadores de rota que o cliente já sabe recusar: a página mostra "não encontrado" sem chamar a API (que daria 404 ou 422,
 *  registrados no console do navegador). */

/** ASN de 32 bits (RFC 6793): inteiro decimal de 1 a 4294967295, sem sinal, espaço nem zero à esquerda. */
export function asnValido(asn: string | number | undefined | null): boolean {
  const s = String(asn ?? '')
  return /^[1-9][0-9]{0,9}$/.test(s) && Number(s) <= 4294967295
}

/** Código de PTT (IX.br ou externo), o mesmo formato que a API aceita (`core.common.codigo_valido`). */
export function codigoPttValido(code: string | undefined | null): boolean {
  return /^[a-z0-9][a-z0-9-]{0,63}$/.test(code ?? '')
}
