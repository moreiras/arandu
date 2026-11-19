// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useCallback, useMemo } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { EntityPage } from '../features/entidade/EntityPage'
import { CabecalhoMunicipio } from '../features/municipio/CabecalhoMunicipio'
import { FichaMunicipio } from '../features/municipio/FichaMunicipio'
import type { MunicipioCtx } from '../features/municipio/contexto'
import { PainelRaio } from '../features/municipio/PainelRaio'
import { agregarMunicipios } from '../features/municipio/agregado'
import { RAIO_MAX_KM, conjuntoNoRaio } from '../features/municipio/raio'
import '../features/municipio'
import { useCentroides, useContratosMunicipio, useFontes, useMunicipioPerfil, usePerfisMunicipios, useRegiao } from '../hooks/entidades'
import type { PerfilMunicipio } from '../types/api'

/**
 * Município como painel: indicadores no topo e depois Mercado → Rede → Infraestrutura (blocos de `features/municipio`).
 * Chamadas: o perfil `/municipios/{ibge}` (SICI fixo e móvel, centróide e PTTs mais próximos) e o manifesto (proveniência).
 * Raio (`?raio=km`): com raio > 0 a página soma os até 50 municípios mais próximos (um perfil por município, as mesmas chamadas e o
 * mesmo cache); com 0 km (padrão) é só o município e nada muda nas chamadas.
 */
export function MunicipioPage() {
  const { ibge } = useParams<{ ibge: string }>()
  const [params, setParams] = useSearchParams()
  const raioKm = Math.max(0, Math.min(RAIO_MAX_KM, Math.round(Number(params.get('raio'))) || 0))
  const versaoAntiga = params.get('versao') === '1'      // a página sem síntese e sem abas (`?versao=1`)
  const { fontes } = useFontes()
  const q = useMunicipioPerfil(ibge)
  const { data: centroides } = useCentroides()
  const conjunto = useMemo(() => (ibge && centroides ? conjuntoNoRaio(ibge, centroides, raioKm) : null), [ibge, centroides, raioKm])
  const vizinhos = useMemo(() => (raioKm > 0 && conjunto ? conjunto.selecionados.slice(1).map((v) => v.ibge) : []), [raioKm, conjunto])
  const viz = usePerfisMunicipios(vizinhos)
  const conjuntoIbges = useMemo(() => (raioKm > 0 ? (conjunto ? conjunto.selecionados.map((v) => v.ibge) : []) : ibge ? [ibge] : []), [raioKm, conjunto, ibge])
  const regiao = useRegiao(conjuntoIbges)
  const contratos = useContratosMunicipio(ibge)
  const onRaio = useCallback((km: number) => setParams((p) => { const n = new URLSearchParams(p); if (km > 0) n.set('raio', String(km)); else n.delete('raio'); return n }, { replace: true }), [setParams])

  const d = q.dados
  const perfilCentral = d?.perfil
  const agregado = useMemo(() => {
    if (raioKm === 0 || !conjunto || !perfilCentral || viz.carregando) return null
    return agregarMunicipios([perfilCentral, ...viz.perfis])
  }, [raioKm, conjunto, perfilCentral, viz.carregando, viz.perfis])
  const perfisPorIbge = useMemo(() => {
    const m: Record<string, PerfilMunicipio | null | undefined> = {}
    if (perfilCentral) m[perfilCentral.ibge] = perfilCentral
    vizinhos.forEach((v, i) => { m[v] = viz.perfis[i] })
    return m
  }, [perfilCentral, vizinhos, viz.perfis])

  if (q.isLoading) return <div className="text-sm text-gray-400">Carregando…</div>
  const base = d?.fixo ?? d?.movel
  if (!d || !base) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h1 className="text-lg font-semibold text-gray-800 mb-1">Município não encontrado</h1>
        <p className="text-sm text-gray-500">
          Nenhum acesso de banda larga declarado para o código IBGE {ibge}.
        </p>
      </div>
    )
  }

  const somando = raioKm > 0 && !!conjunto
  const n = conjunto?.selecionados.length ?? 1
  const ctx: MunicipioCtx = {
    ibge: base.ibge, fixo: d.fixo, movel: d.movel, centroide: d.centroide, indicadores: d.indicadores, serieMercado: d.perfil?.serie_mercado, mercadoGrupos: d.perfil?.mercado_grupos, redeTerritorio: d.perfil?.rede_territorio, territorio: d.perfil?.territorio, erbs: d.perfil?.erbs, fust: d.perfil?.fust, qualidade: d.perfil?.qualidade, reclamacoes: d.perfil?.reclamacoes, consumidor: d.perfil?.consumidor, contratos: contratos.data ?? null,
    proximos: d.proximos, carregandoPtts: false, regiao: regiao.data ?? null,
    ...(somando && agregado ? { ...agregado, conjunto: { n, central: base.ibge } } : {}),
  }
  return (
    <div className="space-y-5">
      <CabecalhoMunicipio nome={base.nome} uf={base.uf} ibge={base.ibge} mesReferencia={base.mes_referencia} snapshot={base.snapshot_date} />
      {conjunto && centroides && (
        <PainelRaio conjunto={conjunto} raioKm={raioKm} onRaio={onRaio} centroides={centroides} perfis={perfisPorIbge} prontos={viz.prontos} total={viz.total} />
      )}
      {somando && viz.carregando ? (
        <div className="text-sm text-gray-400" role="status">Somando os municípios do raio…</div>
      ) : (
        <>
          {somando && (
            <div className="text-sm rounded-lg border border-primario-100 bg-primario-50 text-primario-900 px-3 py-2" data-testid="banner-agregado">
              Os blocos abaixo somam <strong>{n.toLocaleString('pt-BR')} municípios</strong> em volta de {base.nome}. Para ver só o município, volte o raio a 0 km.
            </div>
          )}
          {!versaoAntiga && !somando && <FichaMunicipio nome={base.nome} ctx={ctx} />}
          <EntityPage entidade="municipio" rotulo={`Município de ${base.nome}/${base.uf}`} dados={ctx} snapshot={base.snapshot_date} fontes={fontes} espacamento="space-y-5" />
        </>
      )}
    </div>
  )
}
