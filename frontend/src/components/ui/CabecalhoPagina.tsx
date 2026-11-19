// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ReactNode } from 'react'
import { ComoLer } from './ComoLer'

/**
 * Cabeçalho das páginas de tema: migalhas, `<h1>` com o token do sistema visual, descrição curta,
 * "Como ler" opcional (fechado) e ações à direita. As páginas de entidade usam o `EntityHeader`.
 */
export function CabecalhoPagina({ titulo, descricao, trilha, acoes, comoLer, children }: {
  titulo: ReactNode
  descricao?: ReactNode
  trilha?: ReactNode
  acoes?: ReactNode
  comoLer?: ReactNode
  /** Conteúdo extra ao lado do título (contagem, selo). */
  children?: ReactNode
}) {
  return (
    <header className="space-y-1.5" data-testid="cabecalho-pagina">
      {trilha}
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h1 className="text-titulo-1 text-gray-900">{titulo}</h1>
        {children}
        {acoes && <div className="ml-auto">{acoes}</div>}
      </div>
      {descricao && <p className="max-w-[80ch] text-sm text-gray-600">{descricao}</p>}
      {comoLer && <ComoLer className="max-w-3xl">{comoLer}</ComoLer>}
    </header>
  )
}
