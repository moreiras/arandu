// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { DESCRICAO_METODO, type MetodoQuebras } from '../../lib/quebras'
import { COR_SEM_DADO, NOMES_TERCOS, PALETA_BIVARIADA } from './coresCoropletico'

/** Legenda de um coroplético: uma linha por classe (cor + faixa), "sem dado" e o método das quebras, que não depende só da cor. */
export function LegendaQuebras({ titulo, rotulos, cores, metodo, unidade, semDado, rotuloSemDado }: {
  titulo: string; rotulos: string[]; cores: string[]; metodo: MetodoQuebras; unidade: string; semDado?: number; rotuloSemDado?: string
}) {
  return (
    <figure aria-label={`Legenda: ${titulo}`} className="text-xs text-gray-600" data-testid="legenda">
      <figcaption className="font-medium text-gray-800">{titulo} <span className="font-normal text-gray-500">({unidade})</span></figcaption>
      <ul className="mt-1 space-y-0.5">
        {rotulos.map((r, i) => (
          <li key={i} className="flex items-center gap-2"><span className="inline-block h-3 w-5 rounded-sm border border-gray-300" style={{ background: cores[i] }} aria-hidden="true" />{r}</li>
        ))}
        <li className="flex items-center gap-2"><span className="inline-block h-3 w-5 rounded-sm border border-gray-300" style={{ background: COR_SEM_DADO }} aria-hidden="true" />{rotuloSemDado ?? 'sem dado'}{semDado ? ` (${semDado.toLocaleString('pt-BR')})` : ''}</li>
      </ul>
      <p className="mt-1 max-w-xs text-gray-500">{DESCRICAO_METODO[metodo]}</p>
    </figure>
  )
}

/** Legenda 3 × 3 do mapa bivariado: eixos nomeados e cada célula com a leitura em palavras (baixo/médio/alto). */
export function LegendaBivariada({ rotuloX, rotuloY }: { rotuloX: string; rotuloY: string }) {
  return (
    <figure aria-label={`Legenda bivariada: ${rotuloX} por ${rotuloY}`} className="text-xs text-gray-600" data-testid="legenda-bivariada">
      <figcaption className="font-medium text-gray-800">{rotuloX} × {rotuloY}</figcaption>
      <div className="mt-1 inline-grid grid-cols-3 gap-0.5" role="table" aria-label="Combinações">
        {[2, 1, 0].flatMap((linha) => [0, 1, 2].map((col) => (
          <span key={`${linha}${col}`} role="cell" title={`${rotuloX}: ${NOMES_TERCOS[col]} · ${rotuloY}: ${NOMES_TERCOS[linha]}`}
            className="h-6 w-6 rounded-sm border border-white" style={{ background: PALETA_BIVARIADA[linha][col] }} />
        )))}
      </div>
      <p className="mt-1">→ {rotuloX} (baixo a alto) · ↑ {rotuloY} (baixo a alto). Terços de cada indicador; sem dado em qualquer um dos dois fica cinza.</p>
    </figure>
  )
}
