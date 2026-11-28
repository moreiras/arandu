// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ReactNode } from 'react'

/**
 * "Como ler": método, fórmulas, faixas de cor, ressalvas longas e definições, num `<details>` fechado
 * por padrão e com a mesma aparência em todo o site. O que o leitor precisa para não interpretar errado (estimativa, dado parcial) fica
 * visível fora daqui. `testId` só muda quando o recolhido é o bloco unificado de uma seção (`FontesEDatas`). `titulo` muda o resumo quando o conteúdo é o cálculo ("Como é calculado").
 */
export function ComoLer({ children, titulo = 'Como ler', aberto = false, className = '', testId = 'como-ler' }: { children: ReactNode; titulo?: string; aberto?: boolean; className?: string; testId?: string }) {
  return (
    <details className={`group/comoler rounded border border-gray-200 bg-gray-50/70 text-sm text-gray-700 ${className}`} open={aberto || undefined} data-testid={testId}>
      <summary className="flex min-h-6 cursor-pointer select-none items-center gap-1.5 px-3 py-1 text-xs font-medium text-primario-700 hover:text-primario-900">
        <span aria-hidden="true" className="transition-transform group-open/comoler:rotate-90">▸</span>
        {titulo}
      </summary>
      <div className="space-y-2 px-3 pb-3 pt-1 leading-relaxed [&_p]:max-w-[80ch]">{children}</div>
    </details>
  )
}
