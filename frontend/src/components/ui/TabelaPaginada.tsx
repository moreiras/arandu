// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ColumnDef } from '@tanstack/react-table'
import { TabelaDados } from './TabelaDados'

/** Tabela de 10 linhas por página que vira cartões no celular. É a `TabelaDados` com 10 linhas. */
export function TabelaPaginada<T>({ tamanhoPagina = 10, ...props }: {
  colunas: ColumnDef<T, any>[]
  dados: T[]
  rotulo: string
  tamanhoPagina?: number
  vazio?: string
  snapshot?: string | null
  forcarCartao?: boolean
}) {
  return <TabelaDados {...props} tamanhoPagina={tamanhoPagina} tamanhos={[10, 25, 50, 100]} />
}
