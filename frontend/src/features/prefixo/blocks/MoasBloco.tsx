// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchRoutingAnalysis } from '../../../services/api'
import { EstadoDados } from '../../../components/ui/EstadoDados'
import type { RoutingAnalysis } from '../../../types/routingAnalysis'
import type { BlocoProps } from '../../entidade/registry'
import type { PrefixoCtx } from '../contexto'

/** Aviso de MOAS não medido (snapshot cuja coleta guardou uma origem por prefixo); a API manda o mesmo texto em `moas_indisponivel`. */
export const MOAS_INDISPONIVEL = 'Origem múltipla (MOAS) não medida neste snapshot: a coleta da tabela global deste snapshot guardou uma origem por prefixo, o que não permite detectar prefixos anunciados por mais de um AS. MOAS existe e é raro; a falta de número aqui é limite da coleta, não ausência de eventos.'

/** O MOAS do snapshot foi medido (lista e resumo presentes)? Lista vazia com resumo é "nenhum observado"; sem resumo, não medido. */
export function moasMedido(data: Pick<RoutingAnalysis, 'moas' | 'moas_resumo'> | undefined | null): boolean {
  return !!data && Array.isArray(data.moas) && !!data.moas_resumo
}

export function AvisoMoasNaoMedido({ texto }: { texto?: string }) {
  return <p className="text-sm text-gray-600" data-testid="moas-indisponivel">{texto || MOAS_INDISPONIVEL}</p>
}

/**
 * MOAS do prefixo: a análise de roteamento tem ~14 MB, por isso só é buscada quando o usuário pede. Três desfechos: o prefixo tem
 * mais de uma origem observada (lista as origens e os coletores), nenhuma foi observada (com o número de coletores da família) ou o
 * snapshot não mediu (aviso). Erro de acesso ou de rede vira EstadoDados, nunca "nenhum MOAS".
 */
export function MoasBloco({ dados }: BlocoProps<PrefixoCtx>) {
  const [pedido, setPedido] = useState(false)
  const q = useQuery({ queryKey: ['routing-analysis', dados.date], queryFn: () => fetchRoutingAnalysis(dados.date ?? undefined), enabled: pedido, staleTime: Infinity, gcTime: Infinity, retry: false })
  if (!pedido) {
    return <button type="button" onClick={() => setPedido(true)} className="text-sm text-primario-600 hover:underline">Verificar na análise de roteamento (baixa ~14 MB)</button>
  }
  if (q.isError) return <EstadoDados erro={q.error} oQue="a análise de roteamento" snapshot={dados.date} aoTentarDeNovo={() => q.refetch()} />
  if (!q.data) return <EstadoDados estado="carregando" mensagem="Carregando a análise de roteamento…" />
  const data = q.data
  if (!moasMedido(data)) return <AvisoMoasNaoMedido texto={data.moas_indisponivel} />
  const afi = dados.prefix.includes(':') ? 'v6' : 'v4'
  const resumo = data.moas_resumo!
  if (!resumo.prefixos[afi]) return <AvisoMoasNaoMedido texto={data.moas_indisponivel} />
  const entrada = (data.moas ?? []).find((m) => m.prefix === dados.prefix)
  const coletores = resumo.coletores[afi]?.length ?? 0
  if (!entrada) {
    return (
      <p className="text-sm text-gray-600" data-testid="moas-nenhum">
        {resumo.lista_truncada
          ? `A lista de MOAS deste snapshot foi cortada em ${resumo.lista_limite.toLocaleString('pt-BR')} prefixos e este não está nela; não dá para afirmar que não haja origem múltipla.`
          : `Nenhuma origem múltipla (MOAS) observada para este prefixo exato neste snapshot, entre ${coletores} coletores da tabela global.`}
      </p>
    )
  }
  return (
    <div className="text-sm space-y-2" data-testid="moas-observado">
      <p>Este prefixo foi observado com <strong>{entrada.origens.length} ASes de origem</strong> diferentes (MOAS), entre {coletores} coletores:</p>
      <ul className="space-y-1">
        {entrada.origens.map((o) => (
          <li key={o.asn}>
            <Link to={`/asn/${o.asn}${dados.date ? `?date=${dados.date}` : ''}`} className="font-mono text-primario-600 hover:underline">AS{o.asn}</Link>
            {o.name && <span className="text-gray-600"> {o.name}</span>}
            <span className="text-gray-500"> · vista em {o.coletores} {o.coletores === 1 ? 'coletor' : 'coletores'} ({o.coletores_nomes.join(', ')})</span>
          </li>
        ))}
      </ul>
      <p className="text-xs text-gray-500">{resumo.como_ler}</p>
    </div>
  )
}
