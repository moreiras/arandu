// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { lazy, Suspense, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { LegendaQuebras } from '../../components/maps/LegendaQuebras'
import { coresDasClasses, expressaoCor } from '../../components/maps/coresCoropletico'
import { useCentroides } from '../../hooks/entidades'
import { calcularQuebras, rotulosDasClasses } from '../../lib/quebras'
import { INDICADORES_REDE } from '../../lib/indicadoresMapa'
import { fetchTerritorioMapa } from '../../services/api'
import { useActiveDate } from '../../hooks/useSnapshot'
import type { UfCtx } from './contexto'

const Coropletico = lazy(() => import('../../components/maps/Coropletico').then((m) => ({ default: m.Coropletico })))

type Ind = { id: string; rotulo: string; unidade: string; normalizacao: string; valor: (m: UfCtx['municipios'][number]) => number | null; casas: number; /** vem de `/territorio/mapa` (artefato nacional), buscado só quando o indicador é escolhido */ remoto?: boolean; selo?: string }
const INDICADORES: Ind[] = [
  { id: 'fibra', rotulo: '% de fibra', unidade: '% dos acessos fixos', casas: 0, normalizacao: 'acessos fixos em fibra (FTTH/FTTB) ÷ acessos fixos declarados do município × 100', valor: (m) => m.fibraPct ?? null },
  { id: 'hhi', rotulo: 'Concentração (HHI)', unidade: 'HHI (0 a 10.000)', casas: 0, normalizacao: 'soma dos quadrados das parcelas de cada operadora nos acessos fixos do município', valor: (m) => m.hhi ?? null },
  { id: 'kmPtt', rotulo: 'Distância ao PTT', unidade: 'km', casas: 0, normalizacao: 'distância em linha reta do centróide do município ao PTT do IX.br mais próximo', valor: (m) => m.kmPtt ?? null },
  // Rede: estimativa e inferência por município, vindas do mapa nacional; a UF só recorta. Município sem operadora com ASN e medida fica cinza.
  ...INDICADORES_REDE.map((r): Ind => ({ id: r.id, rotulo: r.rotulo.replace(/ \(.*\)$/, ''), unidade: r.unidade, casas: r.casas, normalizacao: r.normalizacao, valor: () => null, remoto: true, selo: r.selo })),
]

/**
 * Coroplético dos municípios da UF, sobre a malha do IBGE enquadrada na UF. Só indicadores **normalizados** (parcela, índice ou distância, nunca valor absoluto);
 * município sem dado fica cinza e os de fora da UF não são pintados. A tabela "Municípios" abaixo é o caminho por teclado.
 */
export function MapaUf({ dados }: { dados: UfCtx }) {
  const navigate = useNavigate()
  const { data: centroides } = useCentroides()
  const [id, setId] = useState('fibra')
  const ind = INDICADORES.find((i) => i.id === id)!
  const date = useActiveDate()
  const remoto = useQuery({ queryKey: ['territorio-mapa', id, date], enabled: !!ind.remoto && !!date, queryFn: () => fetchTerritorioMapa(id, date ?? undefined), staleTime: Infinity, retry: false })
  const mapa = useMemo(() => {
    const valores: Record<string, number> = {}
    for (const m of dados.municipios) { const v = ind.remoto ? remoto.data?.valores[m.ibge] ?? null : ind.valor(m); if (v != null) valores[m.ibge] = v }
    const quebras = calcularQuebras(Object.values(valores), 5, 'quantis')
    const cores = coresDasClasses(quebras.length + 1)
    const f = (v: number) => v.toLocaleString('pt-BR', { maximumFractionDigits: ind.casas })
    return { valores, cor: expressaoCor(valores, quebras, cores), rotulos: rotulosDasClasses(quebras, f), cores, f }
  }, [dados.municipios, ind, remoto.data])
  const caixa = useMemo<[[number, number], [number, number]] | undefined>(() => {
    if (!centroides) return undefined
    const pts = dados.municipios.map((m) => centroides[m.ibge]).filter(Boolean)
    if (pts.length === 0) return undefined
    const lons = pts.map((p) => p[0]), lats = pts.map((p) => p[1])
    return [[Math.min(...lons) - 0.4, Math.min(...lats) - 0.4], [Math.max(...lons) + 0.4, Math.max(...lats) + 0.4]]
  }, [centroides, dados.municipios])
  const carregandoRemoto = !!ind.remoto && remoto.isLoading
  if ((Object.keys(mapa.valores).length === 0 && !ind.remoto) || !caixa) return <p className="text-sm text-gray-500">Sem dado municipal para colorir o mapa desta UF neste snapshot.</p>
  return (
    <div className="space-y-3" data-testid="mapa-uf">
      <div role="group" aria-label="Indicador do mapa" className="inline-flex rounded-md border border-gray-200 overflow-hidden text-xs">
        {INDICADORES.map((i) => (
          <button key={i.id} type="button" aria-pressed={i.id === id} onClick={() => setId(i.id)}
            className={`px-2.5 py-1 ${i.id === id ? 'bg-primario-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}>{i.rotulo}</button>
        ))}
      </div>
      {carregandoRemoto && <p className="text-sm text-gray-400" role="status">Carregando o indicador…</p>}
      {ind.remoto && !carregandoRemoto && Object.keys(mapa.valores).length === 0 && <p className="text-sm text-gray-500">Nenhum município desta UF tem este indicador no snapshot: faltam operadoras com ASN e medida. Não quer dizer que o valor seja zero.</p>}
      <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1fr)_14rem] items-start">
        <Suspense fallback={<p className="text-sm text-gray-400" role="status">Carregando o mapa…</p>}>
          <Coropletico key={dados.uf} cor={mapa.cor} nivel="municipio" altura={420} caixa={caixa}
            descricao={`Mapa dos municípios de ${dados.uf} coloridos por ${ind.rotulo.toLowerCase()}. Os mesmos números estão na tabela de municípios.`}
            rotulo={(ibge, nome, uf) => { const v = mapa.valores[ibge]; return `${nome}/${uf}: ${v == null ? 'sem dado' : `${mapa.f(v)} ${ind.unidade}`}` }}
            aoClicar={(codigo, nivel) => navigate(nivel === 'uf' ? `/uf/${codigo}` : `/municipio/${codigo}`)} />
        </Suspense>
        <div className="space-y-2">
          <LegendaQuebras titulo={ind.rotulo} unidade={ind.unidade} rotulos={mapa.rotulos} cores={mapa.cores} metodo="quantis" />
          <p className="text-xs text-gray-600"><span className="font-medium">Normalização:</span> {ind.normalizacao}.{ind.selo && <> Natureza: <strong>{ind.selo}</strong> (não é medida direta).</>}</p>
        </div>
      </div>
      <p className="text-xs text-gray-500">Limites municipais: Fonte: IBGE (Malha Municipal 2024), simplificados. Classes com o mesmo número de municípios (quantis).</p>
    </div>
  )
}
