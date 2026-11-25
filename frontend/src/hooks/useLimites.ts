// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { fetchLimites } from '../services/api'

/** Os limites de uso publicados pela API (`/api/v1/limites`). Mudam só com a configuração do servidor, então ficam em cache por 5 minutos. */
export function useLimites() {
  return useQuery({ queryKey: ['limites'], queryFn: fetchLimites, staleTime: 5 * 60_000, retry: false })
}
