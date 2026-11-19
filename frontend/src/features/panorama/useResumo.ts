// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { fetchHealth, fetchSnapshot } from '../../services/api'
import { useActiveDate } from '../../hooks/useSnapshot'

/** Resumo do snapshot para as abas dos panoramas (mesma chave de consulta da Visão geral: nada é buscado duas vezes). Dados de mercado, como o
 * total de outorgas SCM, ficam no Panorama de mercado. */
export function useResumo() {
  const date = useActiveDate()
  const { data: health } = useQuery({ queryKey: ['health'], queryFn: fetchHealth })
  const resolvedDate = date ?? health?.latest_snapshot ?? ''
  const detalhe = useQuery({ queryKey: ['snapshot-details', resolvedDate], queryFn: () => fetchSnapshot(resolvedDate), enabled: !!resolvedDate, staleTime: Infinity, gcTime: Infinity })
  return { date, health, summary: detalhe.data?.summary ?? null, carregando: detalhe.isLoading }
}
