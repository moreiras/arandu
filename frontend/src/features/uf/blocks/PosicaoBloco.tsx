// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { fetchUfs } from '../../../services/api'
import { useActiveDate } from '../../../hooks/useSnapshot'
import { CartogramaUfs, METRICAS, METRICAS_NORMALIZADAS, posicaoNaMetrica } from '../../estados/CartogramaUfs'
import type { BlocoProps } from '../../entidade/registry'
import type { UfCtx } from '../contexto'

/** A UF entre as 27: o cartograma nacional com a UF em destaque e a posição dela em cada indicador normalizado. Posição 1 = maior valor, sem juízo de bom ou ruim. */
export function PosicaoBloco({ dados }: BlocoProps<UfCtx>) {
  const date = useActiveDate()
  const q = useQuery({ queryKey: ['ufs', date], queryFn: () => fetchUfs(date ?? undefined), staleTime: 10 * 60 * 1000 })
  const ufs = q.data?.items ?? []
  if (q.isLoading) return <div className="h-40 bg-gray-50 rounded animate-pulse" />
  if (ufs.length === 0) return null
  const metricas = METRICAS_NORMALIZADAS.flatMap((id) => METRICAS.filter((m) => m.id === id))
  return (
    <div className="grid md:grid-cols-2 gap-4 items-start" data-testid="posicao-uf">
      <CartogramaUfs ufs={ufs} metricas={METRICAS_NORMALIZADAS} titulo="O Brasil por estado" compacto destaque={dados.uf} />
      <ul className="text-sm space-y-1">
        {metricas.map((m) => {
          const p = posicaoNaMetrica(ufs, dados.uf, m.valor)
          return <li key={m.id} className="flex justify-between gap-3 border-b border-gray-100 py-1"><span className="text-gray-600">{m.rotulo}</span><span className="tabular-nums">{p ? `${p.posicao}º de ${p.de} UFs` : 'sem dado'}</span></li>
        })}
      </ul>
    </div>
  )
}
