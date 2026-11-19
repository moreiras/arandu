// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import { ACCENT, type Accent } from './ui'

// ---------------------------------------------------------------------------
// Tabela de rotas global com badges RPKI inline
// ---------------------------------------------------------------------------

export const RPKI_DOT: Record<string, string> = {
  valid:     'bg-ok-500',
  invalid:   'bg-perigo-500',
  not_found: 'bg-gray-300',
}

export const RPKI_LABEL: Record<string, string> = {
  valid:     'válido',
  invalid:   'inválido',
  not_found: 'sem ROA',
}

export function GlobalTableSection({
  title,
  accent,
  prefixes,
  rirPrefixes,
  rpkiValidation,
  cols,
  diffNote,
}: {
  title: string
  accent: Accent
  prefixes: string[]
  rirPrefixes: string[]
  rpkiValidation: Record<string, string>
  cols: 1 | 2
  diffNote?: string
}) {
  const { dot, text } = ACCENT[accent]

  // Validação RPKI sempre exibida para todo prefixo anunciado — ausência de status
  // (sem ROA cobrindo) conta como "sem ROA", não fica omitida.
  const counts = { valid: 0, invalid: 0, not_found: 0 }
  for (const p of prefixes) {
    const s = (rpkiValidation[p] ?? 'not_found') as keyof typeof counts
    if (s in counts) counts[s]++
  }

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-800 mb-1.5 flex items-center gap-2 flex-wrap">
        <span className={`inline-block w-3 h-3 rounded-sm ${dot}`} />
        {title}
        {diffNote && (
          <span className="text-xs font-normal text-gray-400">{diffNote}</span>
        )}
        {prefixes.length > 0 && (
          <span className="flex items-center gap-2 ml-auto">
            {counts.valid > 0 && (
              <span className="inline-flex items-center gap-1 text-xs font-normal text-ok-700">
                <span className="w-1.5 h-1.5 rounded-full bg-ok-500" />{counts.valid} válido{counts.valid !== 1 ? 's' : ''}
              </span>
            )}
            {counts.invalid > 0 && (
              <span className="inline-flex items-center gap-1 text-xs font-normal text-perigo-700">
                <span className="w-1.5 h-1.5 rounded-full bg-perigo-500" />{counts.invalid} inválido{counts.invalid !== 1 ? 's' : ''}
              </span>
            )}
            {counts.not_found > 0 && (
              <span className="inline-flex items-center gap-1 text-xs font-normal text-gray-500">
                <span className="w-1.5 h-1.5 rounded-full bg-gray-300" />{counts.not_found} sem ROA
              </span>
            )}
          </span>
        )}
      </h3>
      <div className="bg-gray-50 rounded border border-gray-200 p-3 max-h-36 overflow-y-auto font-mono text-xs">
        <div className={`grid gap-y-0.5 ${cols === 2 ? 'grid-cols-2 gap-x-3' : 'grid-cols-1'}`}>
          {prefixes.slice(0, 50).map((p) => {
            const rpkiStatus = rpkiValidation[p] ?? 'not_found'
            const isNew = !rirPrefixes.includes(p)
            return (
              <div key={p} className="flex items-center gap-1.5">
                <span className={isNew ? `${text} font-medium` : 'text-gray-500'}>
                  {p}
                </span>
                <span
                  title={RPKI_LABEL[rpkiStatus]}
                  className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${RPKI_DOT[rpkiStatus] ?? 'bg-gray-300'}`}
                />
              </div>
            )
          })}
        </div>
      </div>
      <p className="text-xs text-gray-400 mt-1">
        {rirPrefixes.length > 0 && 'Colorido = visível na tabela global mas não no Registro.br · '}
        Ponto = status RPKI (verde = válido, vermelho = inválido, cinza = sem ROA cobrindo)
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Componentes auxiliares
// ---------------------------------------------------------------------------

