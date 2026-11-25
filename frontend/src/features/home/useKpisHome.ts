// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { chaves, IMUTAVEL } from '../../hooks/entidades/chaves'
import { useActiveDate } from '../../hooks/useSnapshot'
import { useAppStore } from '../../store/app'
import { fetchAcessosStats, fetchSnapshot } from '../../services/api'
import { montarKpis } from './kpisBrasilEmNumeros'

/** Os KPIs da Home ("O Brasil em números" e a síntese do topo): rede (resumo do snapshot, com o anterior para a variação) e mercado (SICI). Uma só definição das consultas. */
export function useKpisHome() {
  const date = useActiveDate()
  const latest = useAppStore((s) => s.latestSnapshot)
  const atual = useQuery({ queryKey: chaves.snapshot(date), queryFn: () => fetchSnapshot(date!), enabled: !!date, ...IMUTAVEL, retry: false })
  // Snapshot anterior: o que o manifesto diz ter sido usado na comparação (`comparado_com`); sem ele, os indicadores saem sem variação (nunca inventada).
  const anteriorData = (atual.data?.manifest as { comparado_com?: string | null } | null)?.comparado_com ?? null
  const anterior = useQuery({ queryKey: chaves.snapshot(anteriorData), queryFn: () => fetchSnapshot(anteriorData!), enabled: !!anteriorData, ...IMUTAVEL, retry: false })
  const sici = useQuery({ queryKey: ['sici-stats-home', date], queryFn: () => fetchAcessosStats(date ?? undefined, 1), enabled: !!date, ...IMUTAVEL, retry: false })
  const data = date ?? latest
  return { kpis: montarKpis(atual.data?.summary, anterior.data?.summary, sici.data, data), data }
}
