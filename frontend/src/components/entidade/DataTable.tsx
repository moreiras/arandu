// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ReactNode } from 'react'
import type { ColumnDef, Row } from '@tanstack/react-table'
import { TabelaDados } from '../ui/TabelaDados'

/**
 * Tabela das páginas de entidade: a `TabelaDados`, com cabeçalho fixo, dicas por coluna, seletor de linhas por página e cartões
 * no celular, com a assinatura desta.
 */
export function DataTable<T>(props: {
  colunas: ColumnDef<T, any>[]
  dados: T[]
  tamanhoPagina?: number
  linhaExpandida?: (linha: Row<T>) => ReactNode
  snapshot?: string | null
  vazio?: string
  acoes?: ReactNode
  rotulo: string
}) {
  return <TabelaDados {...props} />
}
