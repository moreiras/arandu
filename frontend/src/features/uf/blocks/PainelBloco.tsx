// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { fetchUfs } from '../../../services/api'
import { useActiveDate } from '../../../hooks/useSnapshot'
import { referenciaUf } from '../referenciasUf'
import type { BlocoProps } from '../../entidade/registry'
import type { MunicipioUf, UfCtx } from '../contexto'
import { KPI, fmt } from '../../municipio/ui'
import { RAIO_SEM_PTT_KM } from '../contexto'

export function PainelBloco({ dados }: BlocoProps<UfCtx>) {
  const { ixps, municipios, totais, operadorasTotal, operadorasPresentesTotal, semCentroides } = dados
  // a mesma consulta e a mesma chave do bloco "A UF entre as 27": nada é buscado duas vezes; sem `/ufs` os cartões ficam sem a linha de referência
  const date = useActiveDate()
  const q = useQuery({ queryKey: ['ufs', date], queryFn: () => fetchUfs(date ?? undefined), staleTime: 10 * 60 * 1000, retry: false })
  const ref = (id: Parameters<typeof referenciaUf>[2]) => referenciaUf(q.data?.items, dados.uf, id)
  const pen = dados.territorio?.penetracao
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
        <KPI label="Acessos fixos" value={fmt(totais.acessos)} hint={totais.acessos == null ? 'sem SICI neste snapshot' : `${fmt(totais.municipios)} municípios com banda larga`} referencia={ref('acessos')} />
        <KPI label="Fibra" value={totais.fibra_pct == null ? '—' : `${totais.fibra_pct.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`} hint="dos acessos fixos (FTTH/FTTB)" referencia={ref('fibra')} />
        {pen != null && <KPI label="Acessos por 100 domicílios" value={(pen * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} hint="estimativa: acessos declarados ÷ domicílios projetados" referencia={ref('penetracao')} />}
        <KPI label="PTTs" value={fmt(ixps.length)} hint="IX.br na UF" referencia={ref('ptts')} />
        <KPI label="ASNs com sede na UF" value={fmt(totais.asns)} hint="ASNs brasileiros; a UF é a da sede da organização" referencia={ref('asns')} />
        <KPI label="Usuários estimados em ASNs sediados na UF" value={fmt(totais.usuarios)} hint={`APNIC, ${fmt(totais.asns)} ASNs brasileiros com sede na UF; não é a população conectada (ver Uso da Internet)`} />
        <KPI label="Operadoras com acesso na UF" value={fmt(operadorasPresentesTotal)} hint={`CNPJs com acesso fixo declarado na UF; ${fmt(operadorasTotal)} com sede na UF`} />
      </div>
      {!semCentroides && <FaixasDistancia municipios={municipios} />}
    </div>
  )
}

/** Faixas de distância em linha reta ao PTT mais próximo: onde ficam os acessos fixos (e quantos municípios) em relação ao ponto de troca.
 * Escala de um só tom, do claro (perto) ao escuro (longe): a cor ordena as faixas sem sugerir alerta (PT-30). */
export const FAIXAS_KM: Array<{ ate: number; rotulo: string; cor: string }> = [
  { ate: 50, rotulo: 'até 50 km', cor: 'bg-tecnico-200' },
  { ate: RAIO_SEM_PTT_KM, rotulo: '50 a 100 km', cor: 'bg-tecnico-400' },
  { ate: 300, rotulo: '100 a 300 km', cor: 'bg-tecnico-600' },
  { ate: Infinity, rotulo: 'mais de 300 km', cor: 'bg-tecnico-800' },
]

export function agruparPorFaixa(municipios: MunicipioUf[]): Array<{ rotulo: string; cor: string; acessos: number; municipios: number }> {
  const faixas = FAIXAS_KM.map((f) => ({ rotulo: f.rotulo, cor: f.cor, acessos: 0, municipios: 0 }))
  for (const m of municipios) {
    if (m.kmPtt == null) continue
    const i = FAIXAS_KM.findIndex((f) => m.kmPtt! <= f.ate)
    faixas[i].acessos += m.acessos
    faixas[i].municipios += 1
  }
  return faixas
}

function FaixasDistancia({ municipios }: { municipios: MunicipioUf[] }) {
  const faixas = agruparPorFaixa(municipios)
  const total = faixas.reduce((t, f) => t + f.acessos, 0)
  if (total <= 0) return null
  return (
    <div>
      <div className="text-xs text-gray-600 mb-1">Acessos fixos por distância ao PTT mais próximo (linha reta do centróide do município)</div>
      <div className="flex h-4 rounded-full overflow-hidden bg-gray-100" role="img"
        aria-label={faixas.map((f) => `${f.rotulo}: ${(100 * f.acessos / total).toFixed(0)}%`).join('; ')}>
        {faixas.map((f) => f.acessos > 0 && <div key={f.rotulo} className={f.cor} style={{ width: `${(100 * f.acessos) / total}%` }} title={`${f.rotulo}: ${fmt(f.acessos)} acessos em ${fmt(f.municipios)} municípios`} />)}
      </div>
      <ul className="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-gray-500">
        {faixas.map((f) => (
          <li key={f.rotulo} className="flex items-center gap-1">
            <span className={`inline-block w-2.5 h-2.5 rounded-sm ${f.cor}`} aria-hidden />
            {f.rotulo}: <strong className="tabular-nums text-gray-700">{(100 * f.acessos / total).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}%</strong> · {fmt(f.municipios)} mun.
          </li>
        ))}
      </ul>
    </div>
  )
}
