// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchRoutingAnalysis } from '../../../services/api'
import type { BlocoProps } from '../../entidade/registry'
import type { PrefixoCtx } from '../contexto'

/** MOAS (mais de uma origem): a análise de roteamento tem ~14 MB, por isso só é buscada quando o usuário pede. */
export function MoasBloco({ dados }: BlocoProps<PrefixoCtx>) {
  const [pedido, setPedido] = useState(false)
  const q = useQuery({ queryKey: ['routing-analysis', dados.date], queryFn: () => fetchRoutingAnalysis(dados.date ?? undefined), enabled: pedido, staleTime: Infinity, gcTime: Infinity, retry: false })
  if (!pedido) {
    return <button type="button" onClick={() => setPedido(true)} className="text-sm text-primario-600 hover:underline">Verificar na análise de roteamento (baixa ~14 MB)</button>
  }
  if (q.isLoading) return <p className="text-sm text-gray-500">Carregando a análise…</p>
  if (q.isError || !q.data) return <p className="text-sm text-gray-500">Análise de roteamento indisponível neste snapshot.</p>
  const moas = (q.data.moas ?? []).find((m) => m.prefix === dados.prefix)
  return moas ? (
    <div className="text-sm">
      <p className="text-aviso-800 bg-aviso-50 border border-aviso-200 rounded px-3 py-2">Este prefixo é anunciado por <strong>{moas.origins.length} ASes</strong> diferentes (MOAS):</p>
      <div className="mt-2 flex flex-wrap gap-2">{moas.origins.map((a) => <Link key={a} to={`/asn/${a}`} className="font-mono text-primario-600 hover:underline">AS{a}</Link>)}</div>
    </div>
  ) : <p className="text-sm text-gray-600">Nenhuma origem múltipla (MOAS) registrada para este prefixo.</p>
}
