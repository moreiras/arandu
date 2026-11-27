// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/**
 * Anel ao redor de cada célula isolada (ver `celulasIsoladas`), para o SVG do mapa; coordenadas da grade. Cinza-ardósia, como o contorno
 * de quadrante com dado. O anel não altera a célula.
 */
export function AneisIsoladas({ pontos, gridSize, larguraCss, raioPx, tracoPx }: { pontos: Array<[number, number]>; gridSize: number; larguraCss: number; raioPx: number; tracoPx: number }) {
  const u = gridSize / larguraCss
  return (
    <g data-testid="aneis-isoladas">
      {pontos.map(([x, y]) => (
        <circle key={`${x},${y}`} cx={x + 0.5} cy={y + 0.5} r={raioPx * u} fill="none" stroke="#1e293b" strokeOpacity={0.55} strokeWidth={tracoPx * u} />
      ))}
    </g>
  )
}
