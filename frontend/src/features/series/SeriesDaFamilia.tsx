// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { EstadoDados } from '../../components/ui/EstadoDados'
import { fetchSerieNacional } from '../../services/api'
import { SeriesNacionais } from './SerieComparavel'

/**
 * Séries nacionais de uma família (`roteamento` ou `seguranca`) com a regra de comparabilidade. A rota é aberta e só traz totais do Brasil
 * (política de acesso, decisão do mantenedor): todos veem a série inteira, com a mesma URL e a mesma resposta, sem aviso de login.
 */
export function SeriesDaFamilia({ familia, titulo }: { familia: 'roteamento' | 'seguranca'; titulo: string }) {
  const q = useQuery({ queryKey: ['serie-nacional', familia], queryFn: () => fetchSerieNacional(familia), staleTime: 5 * 60 * 1000, retry: false })
  if (q.isError) return <EstadoDados erro={q.error} oQue={`as séries de ${titulo.toLowerCase()}`} mensagem="A série não está publicada para este período." aoTentarDeNovo={() => void q.refetch()} />
  if (!q.data) return <p className="text-sm text-gray-400" role="status">Carregando séries…</p>
  if (q.data.metricas.length === 0) return null
  return <SeriesNacionais serie={q.data} titulo={titulo} />
}
