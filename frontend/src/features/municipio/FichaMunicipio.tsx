// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { DESCRICAO_SELO, ROTULO_SELO } from '../../components/entidade'
import type { MunicipioCtx } from './contexto'
import { REGRAS_VERSAO, sinteseMunicipio } from './sintese'

const COR_SELO = { fato: 'bg-fato-600', inferido: 'bg-inferido-600', estimado: 'bg-estimado-600' } as const

/** Síntese do município acima das abas; some em `?versao=1`. */
export function FichaMunicipio({ nome, ctx }: { nome: string; ctx: MunicipioCtx }) {
  const frases = sinteseMunicipio(nome, ctx)
  if (frases.length === 0) return null
  return (
    <section aria-label="Resumo do município" className="rounded-lg border border-gray-200 bg-white p-4 space-y-2" data-testid="ficha-municipio">
      <ul className="space-y-1 text-sm text-gray-800">
        {frases.map((f) => (
          <li key={f.id} className="flex gap-2" data-testid={`frase-${f.id}`}>
            <span className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${COR_SELO[f.selo]}`} aria-hidden="true" />
            <span><span className="sr-only">{ROTULO_SELO[f.selo]}: </span>{f.texto}<span className="ml-1 text-xs text-gray-500" title={DESCRICAO_SELO[f.selo]}>({ROTULO_SELO[f.selo].toLowerCase()})</span></span>
          </li>
        ))}
      </ul>
      <details className="text-xs text-gray-500">
        <summary className="cursor-pointer select-none">Como esta síntese é gerada</summary>
        <p className="mt-1 max-w-3xl">Frases montadas por regras fixas (versão <code>{REGRAS_VERSAO}</code>) a partir dos campos do snapshot, sem modelo de linguagem. Os acessos são declarados pelas empresas à Anatel (SICI).</p>
      </details>
    </section>
  )
}
