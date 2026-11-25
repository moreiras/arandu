// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { DESCRICAO_SELO, ROTULO_SELO } from '../entidade/proveniencia'
import { SELOS, SeloMarca } from './SeloMarca'

/**
 * Legenda dos selos, no rodapé de todas as páginas (PT-30). Lê o vocabulário de `proveniencia.ts`: o nome e a frase de cada selo são os
 * mesmos da página Sobre. Cada selo aparece com forma, sigla e nome, então a leitura não depende da cor.
 */
export function LegendaSelos() {
  return (
    <section aria-label="Legenda dos selos" className="mx-auto max-w-4xl px-4 text-left text-xs text-gray-700" data-testid="legenda-selos">
      <h2 className="mb-1 text-center text-xs font-semibold text-gray-700">Legenda dos selos</h2>
      <ul className="grid gap-x-6 gap-y-1 sm:grid-cols-3">
        {SELOS.map((s) => (
          <li key={s} className="flex items-start gap-2" data-selo-legenda={s}>
            <SeloMarca selo={s} className="mt-0.5 flex-shrink-0" />
            <span><span className="font-medium">{ROTULO_SELO[s]}:</span> {DESCRICAO_SELO[s]}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
