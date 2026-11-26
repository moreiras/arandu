// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AccessError, fetchTerritorioMapa } from '../../services/api'
import { Coropletico } from '../../components/maps/Coropletico'
import { LegendaBivariada, LegendaQuebras } from '../../components/maps/LegendaQuebras'
import { coresDasClasses, expressaoBivariada, expressaoCor } from '../../components/maps/coresCoropletico'
import { ProvenienciaCompacta } from '../../components/ui'
import { useActiveDate } from '../../hooks/useSnapshot'
import { calcularQuebras, rotulosDasClasses } from '../../lib/quebras'
import { formatarValor, INDICADORES_MUNICIPAIS, indicadorPorId, type IndicadorMapa } from '../../lib/indicadoresMapa'

function useIndicador(id: string, ligado = true) {
  const date = useActiveDate()
  return useQuery({ queryKey: ['territorio-mapa', id, date], queryFn: () => fetchTerritorioMapa(id, date ?? undefined), enabled: !!date && ligado, staleTime: Infinity, gcTime: Infinity, retry: false })
}

/**
 * Mapa dos municípios: coroplético nacional de um indicador **normalizado** sobre a malha do IBGE (Fonte: IBGE), com a legenda de quebras e o método, ou
 * bivariado (dois indicadores em terços). A fonte, a data e a fórmula de normalização ficam sob o mapa.
 */
export default function MapaMunicipios({ indicadores = INDICADORES_MUNICIPAIS, titulo = 'Mapa dos municípios' }: { indicadores?: IndicadorMapa[]; titulo?: string }) {
  const navigate = useNavigate()
  const [id, setId] = useState(indicadores[0].id)
  const [id2, setId2] = useState<string | null>(null)       // null = mapa simples; com valor = bivariado
  const ind = indicadorPorId(id)!
  const ind2 = id2 ? indicadorPorId(id2)! : null
  const q1 = useIndicador(id)
  const q2 = useIndicador(id2 ?? id, !!id2)
  const valores = q1.data?.valores ?? {}
  const outros = q2.data?.valores ?? {}

  const mapa = useMemo(() => {
    if (!q1.data) return null
    if (ind2 && q2.data) {
      const qa = calcularQuebras(Object.values(valores), 3, 'quantis'); const qb = calcularQuebras(Object.values(outros), 3, 'quantis')
      return { cor: expressaoBivariada(valores, outros, qa, qb), legenda: null as null }
    }
    const quebras = calcularQuebras(Object.values(valores), ind.classes, ind.metodo)
    const cores = coresDasClasses(quebras.length + 1)
    const f = (v: number) => formatarValor(v, ind)
    return { cor: expressaoCor(valores, quebras, cores), legenda: { rotulos: rotulosDasClasses(quebras, f), cores } }
  }, [q1.data, q2.data, ind, ind2]) // eslint-disable-line react-hooks/exhaustive-deps

  const bloqueado = q1.error instanceof AccessError
  return (
    <section aria-labelledby="mapa-mun-titulo" className="rounded-lg border border-gray-200 bg-white p-4 space-y-3" data-testid="mapa-municipios">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="mapa-mun-titulo" className="text-base font-semibold text-gray-800">{titulo}</h2>
        <div className="flex w-full flex-wrap gap-2 text-sm sm:w-auto">
          <label className="flex min-w-0 max-w-full items-center gap-1">Indicador
            <select value={id} onChange={(e) => setId(e.target.value)} className="min-w-0 max-w-full rounded border border-gray-300 bg-white px-2 py-1">
              {indicadores.map((i) => <option key={i.id} value={i.id}>{i.rotulo}</option>)}
            </select>
          </label>
          {indicadores.length > 1 && <label className="flex min-w-0 max-w-full items-center gap-1">Comparar com
            <select value={id2 ?? ''} onChange={(e) => setId2(e.target.value || null)} className="min-w-0 max-w-full rounded border border-gray-300 bg-white px-2 py-1">
              <option value="">Mapa simples</option>
              {indicadores.filter((i) => i.id !== id).map((i) => <option key={i.id} value={i.id}>{i.rotulo}</option>)}
            </select>
          </label>}
        </div>
      </div>
      {bloqueado && <p className="text-sm text-aviso-700 bg-aviso-50 border border-aviso-200 rounded px-3 py-2" role="status">O mapa usa páginas avançadas e o tempo de uso sem login acabou. Entre para ver.</p>}
      {q1.isError && !bloqueado && <p className="text-sm text-gray-500" role="status">Não foi possível carregar este indicador agora (o snapshot pode não ter o produto de território).</p>}
      <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1fr)_16rem] items-start">
        <Coropletico cor={mapa?.cor ?? '#e5e7eb'} nivel="municipio" altura={480}
          descricao={`Mapa dos municípios do Brasil colorido por ${ind.rotulo.toLowerCase()}${ind2 ? ` e por ${ind2.rotulo.toLowerCase()}` : ''}. Os mesmos números estão nas páginas de cada município.`}
          rotulo={(ibge, nome, uf) => { const v = valores[ibge]; return `${nome}/${uf}: ${v == null ? 'sem dado' : `${formatarValor(v, ind)} ${ind.unidade}`}` }}
          aoClicar={(codigo, nivel) => navigate(nivel === 'uf' ? `/uf/${codigo}` : `/municipio/${codigo}`)} />
        <div className="space-y-3">
          {ind2 ? <LegendaBivariada rotuloX={ind.rotulo} rotuloY={ind2.rotulo} />
            : mapa?.legenda && <LegendaQuebras titulo={ind.rotulo} unidade={ind.unidade} rotulos={mapa.legenda.rotulos} cores={mapa.legenda.cores} metodo={ind.metodo} rotuloSemDado={ind.semDado} />}
          <p className="text-xs text-gray-600"><span className="font-medium">Normalização:</span> {ind.normalizacao}.</p>
          {ind2 && <p className="text-xs text-gray-600"><span className="font-medium">e:</span> {ind2.normalizacao}.</p>}
          <p className="text-xs text-gray-500">Limites municipais: Fonte: IBGE (Malha Municipal 2024), simplificados. Clique num município para abrir a página dele; o botão de bússola gira o mapa.</p>
        </div>
      </div>
      <ProvenienciaCompacta bloco={{ fontes: ind.fontes, selo: ind.selo, nota: q1.data ? (ind.fontes.includes('anatel_sici') ? `SICI ${q1.data.mes_referencia_sici}; Censo ${q1.data.censo_ano}; PNAD ${q1.data.pnad_ano}` : `População: Censo ${q1.data.censo_ano}`) : undefined }} snapshot={q1.data?.snapshot_date} />
    </section>
  )
}
