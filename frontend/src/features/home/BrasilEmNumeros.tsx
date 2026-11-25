// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { Kpi, NotaVariosTotais } from '../../components/ui'
import { chaves, IMUTAVEL } from '../../hooks/entidades/chaves'
import { useActiveDate } from '../../hooks/useSnapshot'
import { useAppStore } from '../../store/app'
import { fetchAcessosStats, fetchSnapshot } from '../../services/api'
import { montarKpis, type KpiHome } from './kpisBrasilEmNumeros'
import { ComoLerNumerosPais, KpisSegurancaPais } from '../panorama/IndicadoresBrasil'

function Faixa({ titulo, itens, cor }: { titulo: string; itens: KpiHome[]; cor: string }) {
  return (
    <div>
      <h3 className={`text-xs font-semibold uppercase tracking-wide mb-1.5 ${cor}`}>{titulo}</h3>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {itens.map((k) => (
          <Kpi key={k.id} rotulo={k.estimado ? `${k.rotulo} (estimativa)` : k.rotulo} valor={k.valor} tom={k.tom} variacao={k.variacao} selo={k.selo} fonte={k.fonte} dataRef={k.dataRef} />
        ))}
      </div>
    </div>
  )
}

/** "O Brasil em números": rede (resumo do snapshot) e mercado (SICI). A variação compara com o snapshot anterior e com o mês anterior da série; o tooltip do valor traz fonte e data. */
export function BrasilEmNumeros() {
  const date = useActiveDate()
  const latest = useAppStore((s) => s.latestSnapshot)
  const atual = useQuery({ queryKey: chaves.snapshot(date), queryFn: () => fetchSnapshot(date!), enabled: !!date, ...IMUTAVEL, retry: false })
  // Snapshot anterior: o que o manifesto diz ter sido usado na comparação (`comparado_com`); sem ele, os indicadores saem sem variação (nunca inventada).
  const anteriorData = (atual.data?.manifest as { comparado_com?: string | null } | null)?.comparado_com ?? null
  const anterior = useQuery({ queryKey: chaves.snapshot(anteriorData), queryFn: () => fetchSnapshot(anteriorData!), enabled: !!anteriorData, ...IMUTAVEL, retry: false })
  const sici = useQuery({ queryKey: ['sici-stats-home', date], queryFn: () => fetchAcessosStats(date ?? undefined, 1), enabled: !!date, ...IMUTAVEL, retry: false })
  const { rede, mercado } = montarKpis(atual.data?.summary, anterior.data?.summary, sici.data, date ?? latest)
  return (
    <section aria-labelledby="numeros-titulo" className="space-y-3">
      <h2 id="numeros-titulo" className="text-titulo-3 text-gray-900">O Brasil em números</h2>
      <Faixa titulo="Rede" itens={rede} cor="text-v4-700" />
      <Faixa titulo="Mercado" itens={mercado} cor="text-mercado-700" />
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wide mb-1.5 text-tecnico-700">IPv6 e segurança</h3>
        <KpisSegurancaPais />
      </div>
      <ComoLerNumerosPais />
      <NotaVariosTotais />
    </section>
  )
}
