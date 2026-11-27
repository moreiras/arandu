// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { GRID16, getGrid1024 } from './hilbert'

/**
 * Células IPv6 isoladas e finas: funções puras, sem React.
 * Num bloco /12 a grade tem 1024 células de lado e o mapa mostra de 160 a 260 px, então cada /32 vira menos de 1 px de tela e um prefixo
 * pequeno (um /48 no /12 de um RIR) some. O marcador é um anel ao redor da célula, que não muda de tamanho.
 */

/** Lado da célula, em px de tela, abaixo do qual ela é "fina": menos de 1 px não é desenhada como ponto. */
export const LADO_FINO_PX = 1
/** Teto de anéis por mapa, para não encher o SVG; passando dele, ficam os de menor índice de Hilbert. */
export const MAX_MARCADORES = 1000
/** Raio do anel e espessura do traço, em px de tela. */
export const RAIO_MARCADOR_PX = 5
export const TRACO_MARCADOR_PX = 1.5

export const LEGENDA_MARCADOR = 'Um anel cinza ao redor de uma célula indica um prefixo isolado, pequeno demais para aparecer como ponto; o tamanho da célula não muda.'

/**
 * Índices das células finas e isoladas. Critério: o lado da célula na tela (`larguraCss / gridSize`) é menor que `LADO_FINO_PX` e, na
 * grade de "pixels de tela" (blocos de `ceil(1 / lado)` células de lado), o pixel da célula não tem outra célula com dado e nenhum dos 8
 * vizinhos tem dado. Quem tem vizinha já forma uma mancha visível; só a célula sozinha precisa de marcador.
 * `posicao` devolve (x, y) na grade para o índice de Hilbert.
 */
export function celulasIsoladas(
  celulas: ArrayLike<number> | null | undefined,
  posicao: (d: number) => [number, number],
  gridSize: number,
  larguraCss: number,
): number[] {
  if (!celulas || celulas.length === 0 || larguraCss <= 0) return []
  const lado = larguraCss / gridSize
  if (lado >= LADO_FINO_PX) return []
  const tam = Math.ceil(LADO_FINO_PX / lado)
  const colunas = Math.ceil(gridSize / tam)
  const contagem = new Map<number, number>()
  const chaves: number[] = new Array(celulas.length)
  for (let i = 0; i < celulas.length; i++) {
    const [x, y] = posicao(celulas[i])
    const k = Math.floor(y / tam) * colunas + Math.floor(x / tam)
    chaves[i] = k
    contagem.set(k, (contagem.get(k) ?? 0) + 1)
  }
  const saida: number[] = []
  for (let i = 0; i < celulas.length; i++) {
    const k = chaves[i]
    if (contagem.get(k) !== 1) continue
    const cx = k % colunas
    let vizinha = false
    for (let dy = -1; dy <= 1 && !vizinha; dy++) {
      for (let dx = -1; dx <= 1; dx++) {
        if (dx === 0 && dy === 0) continue
        const nx = cx + dx
        if (nx < 0 || nx >= colunas) continue
        if (contagem.has(k + dy * colunas + dx)) { vizinha = true; break }
      }
    }
    if (!vizinha) saida.push(celulas[i])
  }
  saida.sort((a, b) => a - b)
  return saida.slice(0, MAX_MARCADORES)
}

/** (x, y) na grade de um índice de Hilbert do bloco IPv6 (256×256 no legado, 1024×1024 nos /12). */
export function posicaoCelulaV6(gridSize: number): (d: number) => [number, number] {
  if (gridSize === 256) return (d) => [GRID16[d].x, GRID16[d].y]
  const g = getGrid1024()
  return (d) => [g.x[d], g.y[d]]
}
