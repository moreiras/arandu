// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Kpi, NotaVariosTotais } from '../../components/ui'
import type { KpiHome } from './kpisBrasilEmNumeros'
import { useKpisHome } from './useKpisHome'
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
  const { kpis: { rede, mercado } } = useKpisHome()
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
