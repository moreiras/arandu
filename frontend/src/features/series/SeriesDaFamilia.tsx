// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../../auth/AuthContext'
import { EstadoDados } from '../../components/ui/EstadoDados'
import { useSnapshots } from '../../hooks/useSnapshot'
import { fetchSerieNacional } from '../../services/api'
import { SeriesNacionais } from './SerieComparavel'

/**
 * Séries nacionais de uma família (`roteamento` ou `seguranca`) com a regra de comparabilidade. Sem login a API entrega só os 2 snapshots
 * atuais (política de histórico): a série aparece como pontos e tabela, e o aviso diz onde está a série inteira.
 */
export function SeriesDaFamilia({ familia, titulo }: { familia: 'roteamento' | 'seguranca'; titulo: string }) {
  const { anon, loading } = useAuth()
  const snaps = useSnapshots()
  const recentes = (snaps.data?.snapshots ?? []).slice(-2)
  const from = anon ? recentes[0] : undefined
  const pronto = !loading && !!snaps.data
  const q = useQuery({ queryKey: ['serie-nacional', familia, from ?? 'tudo'], queryFn: () => fetchSerieNacional(familia, from), enabled: pronto, staleTime: 5 * 60 * 1000, retry: false })
  if (q.isError) return <EstadoDados erro={q.error} oQue={`as séries de ${titulo.toLowerCase()}`} mensagem="A série não está publicada para este período." aoTentarDeNovo={() => void q.refetch()} />
  if (!q.data) return <p className="text-sm text-gray-400" role="status">Carregando séries…</p>
  if (q.data.metricas.length === 0) return null
  return <SeriesNacionais serie={q.data} titulo={titulo} aviso={anon ? 'Sem login a série mostra só os 2 snapshots mais recentes; entre para ver a série inteira.' : undefined} />
}
