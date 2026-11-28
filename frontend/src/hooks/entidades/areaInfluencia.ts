// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { fetchAreaInfluenciaNacional, fetchAreaInfluenciaPtt } from '../../services/api'
import type { VisaoArea } from '../../types/areaInfluencia'
import { useActiveDate } from '../useSnapshot'
import { IMUTAVEL } from './chaves'

/**
 * Área de influência de um PTT (as duas visões numa chamada). Snapshot sem o artefato responde "não encontrado" (204 pedido com `opcional`): o bloco
 * some em vez de mostrar erro, e não se tenta de novo.
 */
export function useAreaInfluenciaPtt(code: string | undefined) {
  const date = useActiveDate()
  return useQuery({ queryKey: ['area-influencia-ptt', code, date], enabled: !!code && !!date, queryFn: () => fetchAreaInfluenciaPtt(code!, date ?? undefined), ...IMUTAVEL, retry: false })
}

/** Área de influência por município, no país, numa visão. `ativo` adia a chamada até a aba ser aberta. */
export function useAreaInfluenciaNacional(visao: VisaoArea, ativo = true) {
  const date = useActiveDate()
  return useQuery({ queryKey: ['area-influencia-nacional', visao, date], enabled: ativo && !!date, queryFn: () => fetchAreaInfluenciaNacional(visao, date ?? undefined), ...IMUTAVEL, retry: false })
}
