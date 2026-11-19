// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ReactNode } from 'react'
import { Navigate, useSearchParams } from 'react-router-dom'
import { ALIAS, type Destino } from './destinos'

/**
 * Rota dissolvida em panoramas: redireciona para o lugar novo (regra 8 do AGENTS.md: nada some sem alias). `?versao=1` mostra a página de origem.
 */
export function AliasPanorama({ de, antiga }: { de: Destino['de']; antiga: ReactNode }) {
  const [params] = useSearchParams()
  if (params.get('versao') === '1') return <>{antiga}</>
  return <Navigate replace to={ALIAS[de]} />
}
