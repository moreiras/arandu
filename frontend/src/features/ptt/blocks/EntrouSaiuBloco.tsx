// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchMudancas } from '../../../services/api'
import type { BlocoProps } from '../../entidade/registry'
import type { PttCtx } from '../contexto'

const TIPOS = 'ixp_entrada,ixp_saida,ixp_entrada_observada,ixp_saida_observada'
const ROTULO: Record<string, string> = {
  ixp_entrada: 'entrou (cadastro)', ixp_saida: 'saiu (cadastro)', ixp_entrada_observada: 'entrou (peering direto observado)', ixp_saida_observada: 'saiu (peering direto observado)',
}

/**
 * Quem entrou e quem saiu do PTT entre snapshots. São diferenças observadas: "cadastro" é a lista de membros do PTT, "peering direto observado" é o par
 * visto nas rotas coletadas; saída observada pode ser falha de coleta e só vale depois da janela de confirmação.
 */
export function EntrouSaiuBloco({ dados }: BlocoProps<PttCtx>) {
  const { code, nameMap } = dados
  const q = useQuery({ queryKey: ['ptt-entrou-saiu', code], queryFn: () => fetchMudancas({ tipo: TIPOS, ixp: code, estado: 'confirmado', limit: 100 }), staleTime: 10 * 60 * 1000 })
  const itens = q.data?.items ?? []
  if (q.isLoading) return <div className="h-20 bg-gray-50 rounded animate-pulse" />
  if (itens.length === 0) return <p className="text-sm text-gray-500">Nenhuma entrada ou saída confirmada neste PTT no histórico disponível.</p>
  return (
    <div className="space-y-2" data-testid="entrou-saiu">
      <p className="text-sm text-gray-600">{q.data!.total} evento{q.data!.total === 1 ? '' : 's'} confirmado{q.data!.total === 1 ? '' : 's'}; os mais recentes primeiro.</p>
      <ul className="text-sm divide-y divide-gray-100 border border-gray-100 rounded">
        {itens.map((e) => (
          <li key={`${e.data}-${e.tipo}-${e.entidade}`} className="flex flex-wrap items-center gap-x-3 gap-y-0.5 px-3 py-1.5">
            <span className="text-xs text-gray-500 tabular-nums w-20">{e.data}</span>
            {e.asn != null && <Link to={`/asn/${e.asn}`} className="text-primario-700 hover:underline">AS{e.asn}</Link>}
            <span className="text-gray-600 truncate flex-1 min-w-[8rem]">{e.asn != null ? nameMap[String(e.asn)] ?? '' : ''}</span>
            <span className={`text-xs rounded-full px-2 py-0.5 ${e.tipo.includes('entrada') ? 'bg-ok-50 text-ok-700' : 'bg-aviso-50 text-aviso-700'}`}>{ROTULO[e.tipo] ?? e.tipo}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
