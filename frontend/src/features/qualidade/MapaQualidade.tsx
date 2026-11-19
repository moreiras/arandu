// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchQualidadeMapa } from '../../services/api'
import { Coropletico } from '../../components/maps/Coropletico'
import { LegendaQuebras } from '../../components/maps/LegendaQuebras'
import { COR_SEM_DADO, coresDasClasses, expressaoCor } from '../../components/maps/coresCoropletico'
import { calcularQuebras, rotulosDasClasses } from '../../lib/quebras'
import { useActiveDate } from '../../hooks/useSnapshot'
import type { QualIndicador } from '../../types/api'

/** Cores da faixa (0 abaixo da inferior, 1 entre, 2 acima da superior): divergente neutra, sem verde/vermelho, porque o sentido de "melhor" depende do indicador. */
const COR_FAIXA = ['#7c3aed', '#d1d5db', '#d97706']

/**
 * Mapa municipal de um indicador do RQUAL: o valor (média das prestadoras medidas no município) em quantis, ou a faixa em relação às duas referências da Anatel.
 * Cinza = município sem medição nas grandes prestadoras (não quer dizer qualidade ruim nem boa). Nada aqui nomeia empresa nem diz "melhor" ou "pior".
 */
export default function MapaQualidade({ servico, indicador }: { servico: string; indicador: QualIndicador }) {
  const navigate = useNavigate()
  const date = useActiveDate()
  const [modo, setModo] = useState<'valor' | 'faixa'>('valor')
  const q = useQuery({ queryKey: ['qualidade-mapa', servico, indicador.codigo, date], enabled: !!date, queryFn: () => fetchQualidadeMapa({ servico, indicador: indicador.codigo, date: date ?? undefined }), staleTime: Infinity, retry: false })
  const d = q.data
  const temFaixa = !!d?.faixas
  const modoEf = modo === 'faixa' && temFaixa ? 'faixa' : 'valor'
  const mapa = useMemo(() => {
    if (!d) return null
    if (modoEf === 'faixa') {
      const por: Record<string, number> = d.faixas!
      return { cor: ['match', ['to-string', ['get', 'ibge']], ...Object.entries(por).flatMap(([ibge, f]) => [ibge, COR_FAIXA[f]]), COR_SEM_DADO] as unknown[], legenda: null }
    }
    const quebras = calcularQuebras(Object.values(d.valores), 5, 'quantis')
    const cores = coresDasClasses(quebras.length + 1)
    return { cor: expressaoCor(d.valores, quebras, cores), legenda: { rotulos: rotulosDasClasses(quebras, (v) => v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })), cores } }
  }, [d, modoEf])
  return (
    <section aria-label="Mapa do indicador por município" className="rounded-lg border border-gray-200 bg-white p-4 space-y-3" data-testid="mapa-qualidade">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-gray-700">{indicador.codigo} por município</h3>
        {temFaixa && (
          <div role="group" aria-label="Leitura do mapa" className="inline-flex rounded-md border border-gray-200 overflow-hidden text-xs">
            {([['valor', 'Valor'], ['faixa', 'Faixa da Anatel']] as const).map(([id, rot]) => (
              <button key={id} type="button" aria-pressed={modoEf === id} onClick={() => setModo(id)} className={`px-2.5 py-1 ${modoEf === id ? 'bg-primario-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}>{rot}</button>
            ))}
          </div>
        )}
      </div>
      {q.isError && <p className="text-sm text-gray-500" role="status">Este indicador não tem resultado municipal neste snapshot.</p>}
      <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1fr)_16rem] items-start">
        <Coropletico cor={mapa?.cor ?? COR_SEM_DADO} nivel="municipio" altura={420}
          descricao={`Mapa dos municípios do Brasil colorido pelo indicador ${indicador.codigo} do RQUAL (${indicador.descricao}). Os mesmos resultados estão na página de cada município.`}
          rotulo={(ibge, nome, uf) => { const v = d?.valores[ibge]; return `${nome}/${uf}: ${v == null ? 'sem medição' : `${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} ${indicador.unidade}`}` }}
          aoClicar={(codigo, nivel) => navigate(nivel === 'uf' ? `/uf/${codigo}` : `/municipio/${codigo}`)} />
        <div className="space-y-3 text-xs text-gray-600">
          {modoEf === 'faixa' && d?.faixas_rotulos ? (
            <figure aria-label="Legenda: faixa em relação às referências da Anatel" data-testid="legenda">
              <figcaption className="font-medium text-gray-800">Em relação às referências da Anatel</figcaption>
              <ul className="mt-1 space-y-0.5">
                {[2, 1, 0].map((f) => <li key={f} className="flex items-center gap-2"><span className="inline-block h-3 w-5 rounded-sm border border-gray-300" style={{ background: COR_FAIXA[f] }} aria-hidden="true" />{d.faixas_rotulos![String(f)]}</li>)}
                <li className="flex items-center gap-2"><span className="inline-block h-3 w-5 rounded-sm border border-gray-300" style={{ background: COR_SEM_DADO }} aria-hidden="true" />sem medição</li>
              </ul>
              <p className="mt-1">Referências: superior {d.referencias.superior}, inferior {d.referencias.inferior}. As cores não dizem se é melhor ou pior: o sentido depende do indicador.</p>
            </figure>
          ) : mapa?.legenda && <LegendaQuebras titulo={indicador.codigo} unidade={indicador.unidade} rotulos={mapa.legenda.rotulos} cores={mapa.legenda.cores} metodo="quantis" rotuloSemDado="sem medição" />}
          {d && <p><span className="font-medium">Como é calculado:</span> {d.normalizacao}. {d.total.toLocaleString('pt-BR')} municípios medidos.</p>}
          <p className="text-gray-500">Limites municipais: Fonte: IBGE (Malha Municipal 2024), simplificados. Só as grandes prestadoras são medidas; município sem medição fica cinza.</p>
        </div>
      </div>
    </section>
  )
}
