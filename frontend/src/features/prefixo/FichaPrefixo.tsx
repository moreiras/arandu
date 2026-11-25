// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { DESCRICAO_SELO, ROTULO_SELO } from '../../components/entidade'
import type { PrefixoInfo } from '../../services/api'
import { REGRAS_VERSAO_PREFIXO, sintesePrefixo } from './sintese'

const COR_SELO = { fato: 'bg-fato-600', inferido: 'bg-inferido-600', estimado: 'bg-estimado-600' } as const

/** Ficha-resumo do prefixo: a síntese em frases com selo, sem abas (a página é curta). Some em `?versao=1`. */
export function FichaPrefixo({ info }: { info: PrefixoInfo }) {
  const frases = sintesePrefixo(info)
  return (
    <section aria-label="Resumo do prefixo" className="rounded-lg border border-gray-200 bg-white p-4" data-testid="ficha-prefixo">
      <ul className="space-y-1 text-sm text-gray-800">
        {frases.map((f) => (
          <li key={f.id} className="flex gap-2" data-testid={`frase-${f.id}`}>
            <span className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${COR_SELO[f.selo]}`} aria-hidden="true" />
            <span><span className="sr-only">{ROTULO_SELO[f.selo]}: </span>{f.texto}<span className="ml-1 text-xs text-gray-500" title={DESCRICAO_SELO[f.selo]}>({ROTULO_SELO[f.selo].toLowerCase()})</span></span>
          </li>
        ))}
      </ul>
      <details className="mt-2 text-xs text-gray-500">
        <summary className="cursor-pointer select-none">Como esta síntese é gerada</summary>
        <p className="mt-1 max-w-3xl">Frases montadas por regras fixas (versão <code>{REGRAS_VERSAO_PREFIXO}</code>) a partir dos campos do snapshot, sem modelo de linguagem; o selo diz se é fato, inferência ou estimativa.</p>
      </details>
    </section>
  )
}
