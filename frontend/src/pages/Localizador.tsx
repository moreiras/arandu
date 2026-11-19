import { useCallback, useMemo, useState } from 'react'
import { useActiveDate } from '../hooks/useSnapshot'
import {
  agruparPorCoordenada, contagemEntidades, contagensIx, etiquetasIx, filtrarNoRaio, indicesScm, mapaDeNomes, montarEntidades,
  municipiosSiciNoRaio, operadoresSici, pixNoRaio, resumoDoRaio, scmsNoRaio,
} from '../features/localizador/calculos'
import type { Ponto, PresencaIx } from '../features/localizador/calculos'
import { baixarCsv, montarCsv } from '../features/localizador/csv'
import { nearestIxCode } from '../features/localizador/geo'
import { PainelControles } from '../features/localizador/PainelControles'
import { PainelEntidades } from '../features/localizador/PainelEntidades'
import { geocodeQuery, useLocalizadorDados } from '../features/localizador/useLocalizadorDados'
import { useMapaLocalizador } from '../features/localizador/useMapaLocalizador'
import { Link } from 'react-router-dom'

/**
 * Localizador de ASes (/localizador): ASes, prefixos, SCMs e usuários SICI num raio em volta de um ponto.
 * A página só compõe: dados em `useLocalizadorDados`, cálculos puros em `calculos.ts` (cobertos por testes), feições e balões em
 * `balloes.ts`, mapa em `useMapaLocalizador` e os painéis em `Painel*.tsx`.
 */
export function Localizador() {
  const date = useActiveDate() ?? undefined
  const [markerPos, setMarkerPos] = useState<Ponto | null>(null)
  const [radius, setRadius] = useState(80)
  // todas as camadas ligadas ao abrir (sedes de AS, prefixos, SCM e usuários do SICI).
  const [show, setShowState] = useState({ asns: true, prefixes: true, scms: true, sici: true })
  const setShow = useCallback((p: Partial<typeof show>) => setShowState(s => ({ ...s, ...p })), [])
  const [search, setSearch] = useState('')
  const [searching, setSearching] = useState(false)
  const [copied, setCopied] = useState(false)
  const [modal, setModal] = useState<{ title: string; html: string } | null>(null)

  const dados = useLocalizadorDados(date, show.prefixes)
  const { asnGeo, prefixGeo, ixList, ixPresence, pixGeo, scmGeo, siciMunData, municipioCentroids } = dados

  // Nomes dos IXes (código → nome de cidade) para as tags "IX <cidade>".
  const ixNames = useMemo(() => {
    const m: Record<string, string> = {}
    for (const e of ixList?.ixps ?? []) m[e.code] = e.name
    return m
  }, [ixList])
  const ixLabel = useCallback((code: string) => `IX ${ixNames[code] ?? code.toUpperCase()}`, [ixNames])

  const asnNameMap = useMemo(() => mapaDeNomes(asnGeo), [asnGeo])
  const { filteredAsns, asnDots, prefixBubbles } = useMemo(
    () => filtrarNoRaio({ markerPos, radius, showAsns: show.asns, showPrefixes: show.prefixes, asnGeo, prefixGeo, asnNameMap }),
    [markerPos, radius, show.asns, show.prefixes, asnGeo, prefixGeo, asnNameMap],
  )
  const nearestIx = useMemo(() => (markerPos ? nearestIxCode(markerPos[0], markerPos[1]) : null), [markerPos])
  const pixDots = useMemo(() => pixNoRaio(markerPos, radius, pixGeo), [markerPos, radius, pixGeo])
  const scmsInRadius = useMemo(() => scmsNoRaio(markerPos, radius, scmGeo), [markerPos, radius, scmGeo])
  const siciMunInRadius = useMemo(
    () => municipiosSiciNoRaio(markerPos, radius, siciMunData, municipioCentroids), [markerPos, radius, siciMunData, municipioCentroids])
  const siciOperadores = useMemo(() => operadoresSici(siciMunInRadius), [siciMunInRadius])
  const { asnToCnpj, cnpjAllAsns, scmCnpjs } = useMemo(() => indicesScm(scmGeo, asnGeo), [scmGeo, asnGeo])
  const entities = useMemo(
    () => montarEntidades({ filteredAsns, scmsInRadius, asnToCnpj, cnpjAllAsns, scmCnpjs, asnNameMap, showScms: show.scms, showSici: show.sici, siciOperadores }),
    [filteredAsns, scmsInRadius, asnToCnpj, cnpjAllAsns, scmCnpjs, asnNameMap, show.scms, show.sici, siciOperadores],
  )
  const entityCounts = useMemo(() => contagemEntidades(entities), [entities])
  const coordGroups = useMemo(
    () => agruparPorCoordenada({ asnDots, scmsInRadius, showAsns: show.asns, showScms: show.scms, markerPos }),
    [asnDots, scmsInRadius, show.asns, show.scms, markerPos],
  )
  const stats = useMemo(
    () => resumoDoRaio({ filteredAsns, scmsInRadius, siciOperadores, showScms: show.scms, showSici: show.sici }),
    [filteredAsns, scmsInRadius, siciOperadores, show.scms, show.sici],
  )

  // Para cada AS: IXes onde é membro / origina prefixos; tags e contagens de participação.
  const ixOf = useCallback((asn: number): PresencaIx => ixPresence?.asns[String(asn)] ?? { m: [], o: [] }, [ixPresence])
  const tagsDoAs = useCallback((asn: number) => etiquetasIx(ixOf(asn).m, nearestIx, ixLabel), [ixOf, nearestIx, ixLabel])
  const ixCounts = useMemo(() => contagensIx(filteredAsns, ixOf, nearestIx), [filteredAsns, ixOf, nearestIx])

  const { mapDivRef, mapRef } = useMapaLocalizador({
    markerPos, radius, setMarkerPos, abrirModal: setModal, show, asnDots, prefixBubbles, pixDots, coordGroups, scmsInRadius,
    siciMunInRadius, asnToCnpj, asnNameMap,
  })

  const handleSearch = useCallback(async () => {
    if (!search.trim()) return
    setSearching(true)
    try {
      const pos = await geocodeQuery(search.trim(), date)
      if (pos) {
        setMarkerPos(pos)
        mapRef.current?.flyTo({ center: [pos[1], pos[0]], zoom: 11 })
      }
    } finally {
      setSearching(false)
    }
  }, [search, date, mapRef])

  const handleCopy = useCallback(() => {
    const text = entities
      .map(e => [...e.asns.map(a => `AS${a}`), ...(e.cnpj ? [e.cnpj] : [])].join(' '))
      .join('\n')
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }, [entities])

  const handleCsv = useCallback(
    () => baixarCsv(montarCsv(entities, ixOf, nearestIx, ixLabel), nearestIx),
    [entities, ixOf, nearestIx, ixLabel],
  )

  const panelBase =
    'absolute z-20 bg-white/90 backdrop-blur-sm rounded-xl shadow-lg border border-gray-200 pointer-events-auto'

  return (
    <div className="space-y-1">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Localizador de ASes</h1>
        <p className="text-sm text-gray-500">
          Encontre Sistemas Autônomos próximos a uma localização no Brasil
        </p>
      </div>

      {/* Wrapper: map + floating panels */}
      <div
        // `isolate`: os painéis flutuantes empilham só dentro do mapa; sem isso passavam por cima do cabeçalho fixo e dos menus ao rolar.
        className="relative isolate rounded-xl overflow-hidden border border-gray-200"
        style={{ height: 'calc(100vh - 160px)', minHeight: 480 }}
      >
        {/* MapLibre map (w-full/h-full: MapLibre força position:relative no container,
            então não dá para depender de `absolute inset-0` para o tamanho) */}
        <div ref={mapDivRef} className="w-full h-full" />

        {/* Modal de entidades agregadas (abre ao clicar em marcador com 2+ entidades) */}
        {modal && (
          <div
            className="absolute inset-0 z-50 flex items-center justify-center bg-black/40"
            onClick={() => setModal(null)}
          >
            <div
              className="bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-80 flex flex-col"
              style={{ maxHeight: '70%' }}
              onClick={e => e.stopPropagation()}
            >
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-700 flex-shrink-0">
                <span className="text-xs font-semibold text-white leading-snug">{modal.title}</span>
                <button
                  className="ml-3 flex-shrink-0 text-gray-400 hover:text-white text-base leading-none"
                  onClick={() => setModal(null)}
                >✕</button>
              </div>
              <div
                className="overflow-y-auto p-3 text-xs text-gray-200 flex-1"
                dangerouslySetInnerHTML={{ __html: modal.html }}
              />
            </div>
          </div>
        )}

        <PainelControles
          className={`${panelBase} top-3 left-3 p-3 w-64 space-y-3`}
          search={search} setSearch={setSearch} searching={searching} onSearch={handleSearch}
          radius={radius} setRadius={setRadius} show={show} setShow={setShow}
        />

        <PainelEntidades
          className={`${panelBase} top-3 right-3 bottom-3 w-60 flex flex-col`}
          entities={entities} entityCounts={entityCounts} markerPos={markerPos} stats={stats} filteredAsnsCount={filteredAsns.length}
          nearestIx={nearestIx} ixLabel={ixLabel} ixCounts={ixCounts} copied={copied} onCopy={handleCopy} onCsv={handleCsv}
          temPresenca={!!ixPresence} tagsDoAs={tagsDoAs}
        />
      </div>

      {/* os municípios e as UFs da área, com link para as páginas deles. */}
      {markerPos && siciMunInRadius.length > 0 && (
        <section className="rounded-lg border border-gray-200 bg-white p-4 space-y-3" aria-labelledby="area-municipios" data-testid="localizador-municipios">
          <h2 id="area-municipios" className="text-titulo-3 text-gray-800">Municípios e estados na área</h2>
          <p className="text-sm">
            <span className="text-gray-600">Estados: </span>
            {[...new Set(siciMunInRadius.map((m) => m.uf))].sort().map((uf, i) => (
              <span key={uf}>{i > 0 && ', '}<Link to={`/uf/${uf}`} className="text-primario-700 hover:underline">{uf}</Link></span>
            ))}
          </p>
          <ul className="grid gap-x-4 gap-y-1 text-sm sm:grid-cols-2 lg:grid-cols-3">
            {[...siciMunInRadius].sort((a, b) => (b.acessos ?? 0) - (a.acessos ?? 0)).map((m) => (
              <li key={m.ibge} className="flex justify-between gap-2">
                <Link to={`/municipio/${m.ibge}`} className="text-primario-700 hover:underline">{m.nome}/{m.uf}</Link>
                <span className="text-xs text-gray-500 tabular-nums">{(m.acessos ?? 0).toLocaleString('pt-BR')} acessos · {m.operadores.length} operadoras</span>
              </li>
            ))}
          </ul>
          <p className="text-xs text-gray-500">Municípios com centro dentro do raio, por acessos fixos declarados ao SICI (do maior para o menor).</p>
        </section>
      )}
    </div>
  )
}
