// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/**
 * Quadrantes dos mapas de Hilbert para acesso pelo teclado: nome acessível e posição de cada botão. Funções puras, sem React.
 */
import { POS_TO_D16, getPosToD1024, type V6BlockConfig } from './hilbert'

/** Lado, em células, do quadrante /20 dos blocos IPv6 (64×64 de /32). */
export const V6_QUADRANTE = 64

/** Nome acessível do botão que amplia um quadrante, a partir do prefixo. */
export const nomeAmpliar = (prefixo: string) => `Ampliar quadrante ${prefixo}`

/**
 * Prefixo /20 do quadrante que contém a célula `d` de um bloco IPv6, na forma comprimida da RFC 5952 (minúsculas, sem zeros à esquerda,
 * "::" no lugar da maior sequência de grupos zero). Só os dois primeiros grupos podem ser não nulos, então o resultado é "g1::" ou "g1:g2::".
 * É o texto do título do zoom e do nome do botão do quadrante.
 */
export function prefixoQuadranteDeCelula(config: V6BlockConfig, d: number): string {
  const q = d & ~0xfff
  const g1 = (config.baseG1 | (q >> 16)) & 0xffff
  const g2 = q & 0xffff
  return `${g1.toString(16)}:${g2 === 0 ? '' : g2.toString(16) + ':'}:/20`
}

/** Prefixo /20 do quadrante (gx, gy) de um bloco IPv6 (grade de quadrantes de 64×64 células). */
export function prefixoQuadranteV6(config: V6BlockConfig, gx: number, gy: number): string {
  const x = gx * V6_QUADRANTE
  const y = gy * V6_QUADRANTE
  const d = config.gridSize === 256 ? POS_TO_D16[y * 256 + x] : getPosToD1024()[y * 1024 + x]
  return prefixoQuadranteDeCelula(config, d)
}

/** Prefixo /8 do quadrante IPv4 a partir do primeiro octeto. */
export const prefixoQuadranteV4 = (slashEight: number) => `${slashEight}.0.0.0/8`
