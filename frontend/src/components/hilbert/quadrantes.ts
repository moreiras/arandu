// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/**
 * Quadrantes dos mapas de Hilbert para acesso pelo teclado: nome acessível e posição de cada botão. Funções puras, sem React.
 */
import { POS_TO_D16, cellIndexToV6Prefix, getPosToD1024, type V6BlockConfig } from './hilbert'

/** Lado, em células, do quadrante /20 dos blocos IPv6 (64×64 de /32). */
export const V6_QUADRANTE = 64

/** Nome acessível do botão que amplia um quadrante, a partir do prefixo. */
export const nomeAmpliar = (prefixo: string) => `Ampliar quadrante ${prefixo}`

/** Prefixo /20 do quadrante (gx, gy) de um bloco IPv6; é o mesmo que o título do zoom mostra. */
export function prefixoQuadranteV6(config: V6BlockConfig, gx: number, gy: number): string {
  const x = gx * V6_QUADRANTE
  const y = gy * V6_QUADRANTE
  const d = config.gridSize === 256 ? POS_TO_D16[y * 256 + x] : getPosToD1024()[y * 1024 + x]
  return cellIndexToV6Prefix(d & ~0xfff, config).replace('::/32', '::/20')
}

/** Prefixo /8 do quadrante IPv4 a partir do primeiro octeto. */
export const prefixoQuadranteV4 = (slashEight: number) => `${slashEight}.0.0.0/8`
