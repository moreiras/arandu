// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

/**
 * Orientação preferida dos mapas: o padrão é sul para cima (180°) e a
 * escolha de quem usa fica no armazenamento local do navegador, valendo entre sessões e sem login. Nada vai ao servidor.
 */
export const ORIENTACAO_SUL = 180
export const ORIENTACAO_NORTE = 0
const CHAVE = 'arandurape.mapa.orientacao'

/** Lê a preferência; qualquer falha do armazenamento (modo privado, bloqueio) cai no padrão. */
export function orientacaoPreferida(armazem?: Pick<Storage, 'getItem'>): number {
  try {
    const s = armazem ?? globalThis.localStorage
    const v = s.getItem(CHAVE)
    if (v === 'norte') return ORIENTACAO_NORTE
  } catch { /* sem armazenamento: usa o padrão */ }
  return ORIENTACAO_SUL
}

/** Grava a preferência a partir do ângulo escolhido (entre 90° e 270° conta como sul para cima). */
export function lembrarOrientacao(bearing: number, armazem?: Pick<Storage, 'setItem'>): void {
  const b = ((bearing % 360) + 360) % 360
  const sul = b > 90 && b < 270
  try {
    const s = armazem ?? globalThis.localStorage
    s.setItem(CHAVE, sul ? 'sul' : 'norte')
  } catch { /* ignora */ }
}
