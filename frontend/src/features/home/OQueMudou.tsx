// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AccessError, queryColecao } from '../../services/api'
import { formatarData } from '../../lib/datas'
import { useActiveDate } from '../../hooks/useSnapshot'
import { CARTOES } from './cartoes'

interface Evento { asn?: number; uf?: string; data?: string }

/** "O que mudou" em uma linha: os ASes brasileiros novos confirmados na tabela de roteamento (1 linha) e o caminho para tudo o que mudou. */
export function OQueMudou() {
  const date = useActiveDate()
  const c = CARTOES.find((x) => x.id === 'o-que-mudou')?.consulta
  const q = useQuery({
    queryKey: ['o-que-mudou-home', date],
    queryFn: () => queryColecao<{ items?: Evento[]; total?: number }>('eventos', { ...((c && c.tipo === 'query' ? c.corpo : {}) as Record<string, unknown>), limit: 1 }, date ?? undefined),
    enabled: !!date && c?.tipo === 'query', staleTime: Infinity, gcTime: Infinity, retry: false,
  })
  const total = q.data?.total
  const ultimo = q.data?.items?.[0]
  const sem = q.error instanceof AccessError
  return (
    <p className="text-sm text-gray-700 bg-white border border-gray-200 rounded-lg px-4 py-3" data-testid="o-que-mudou">
      <span className="font-medium text-gray-900">O que mudou: </span>
      {total != null && total > 0
        ? <>{total.toLocaleString('pt-BR')} ASes brasileiros novos confirmados na tabela de roteamento{ultimo?.data ? <>, o mais recente em {formatarData(ultimo.data)}</> : null}. </>
        : total === 0 ? 'nenhum AS brasileiro novo confirmado nos últimos snapshots. ' : sem ? 'entre para ver as mudanças recentes. ' : q.isLoading ? 'carregando… ' : ''}
      <Link to="/mudancas" className="text-primario-700 hover:underline">Ver tudo que mudou →</Link>
    </p>
  )
}
