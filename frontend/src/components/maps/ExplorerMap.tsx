import { useEffect, useMemo, useRef, useState } from 'react'
import { AccessError, type MapQueryBody, type PixCobertura } from '../../services/api'
import { estadoDoErro, formatarEspera } from '../ui/EstadoDados'
import { useAuth } from '../../auth/AuthContext'
import { baixarCsv } from './explorer/csv'
import { Legend } from './explorer/Legenda'
import { resumirScm } from './explorer/scmSici'
import { Spinner } from './explorer/icones'
import { LayerPanel } from './explorer/PainelCamadas'
import { INITIAL, LAYER_BY_ID } from './explorer/tipos'
import type { MapState } from './explorer/tipos'
import { useCamadasDados } from './explorer/useCamadasDados'
import { useMapaExplorer } from './explorer/useMapaExplorer'

/**
 * Mapa "Explorar" (/mapa). A lógica foi dividida em `explorer/`: `consulta.ts` (estado → corpo das consultas),
 * `useCamadasDados` (busca por camada), `camadasMapa.ts` + `interacoes.ts` + `popups.ts` (MapLibre) e `useMapaExplorer` (ciclo de vida);
 * aqui só a composição da tela.
 */
export function ExplorerMap({ date }: { date?: string }) {
  const { requireLogin } = useAuth()
  const requireLoginRef = useRef(requireLogin)
  requireLoginRef.current = requireLogin
  const [state, setState] = useState<MapState>(INITIAL)
  // Parâmetros das consultas com debounce (texto/números digitados); o liga/desliga
  // das camadas usa o estado imediato.
  const [debounced, setDebounced] = useState<MapState>(INITIAL)
  // no celular o painel é uma folha que sobe de baixo e começa fechada (o mapa ocupa a tela)
  const [panelOpen, setPanelOpen] = useState(() => !(typeof window.matchMedia === 'function' && window.matchMedia('(max-width: 639px)').matches))

  useEffect(() => {
    const id = setTimeout(() => setDebounced(state), 400)
    return () => clearTimeout(id)
  }, [state])

  // PTT "selecionado": o do grupo PTT, se ligado; senão o da proximidade.
  const selectedIx = (state.on.prefixos_ix_v4 || state.on.prefixos_ix_v6)
    ? state.ixCode
    : (state.nearIxp || null)

  const exportar = (features: GeoJSON.Feature[], id: Parameters<typeof baixarCsv>[1], snapshot: string) => {
    if (!requireLoginRef.current('exportar')) return
    baixarCsv(features, id, snapshot)
  }
  const dados = useCamadasDados(state, debounced, date, exportar)
  const { mapError, containerRef } = useMapaExplorer({
    state, statuses: dados.statuses, resultById: dados.resultById, selectedIx, panelOpen,
    corpoSedes: () => dados.specs.find(sp => sp.id === 'asns_geo')?.key[3] as MapQueryBody | undefined,
  })
  const { loadingLabels, errors, activeData, doneCount } = dados
  const dadosScm = state.on.outorgas_scm ? dados.resultById.outorgas_scm?.data : undefined
  const resumoScm = useMemo(() => resumirScm(dadosScm as GeoJSON.FeatureCollection | undefined), [dadosScm])
  // A causa do erro das camadas (orçamento, login, taxa) muda a ação: "falha" só quando é falha mesmo.
  const causa = errors.map((id) => dados.resultById[id]?.error).find((e) => e instanceof AccessError) as AccessError | undefined
  const tipoErro = causa ? estadoDoErro(causa) : 'falha'
  const prefixoErro = tipoErro === 'orcamento' ? 'O tempo de uso sem login acabou; entre para ver'
    : tipoErro === 'login' ? 'Exige login'
    : tipoErro === 'taxa' ? `Muitas consultas em pouco tempo; tente de novo${causa?.retryAfter != null ? ` em ${formatarEspera(causa.retryAfter)}` : ' em instantes'}`
    : 'Falha ao carregar'

  return (
    <div className="absolute inset-0">
      <div ref={containerRef} className="absolute inset-0" />

      {loadingLabels.length > 0 && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 pointer-events-none">
          <div className="bg-white/90 backdrop-blur-sm text-sm text-gray-500 rounded-full px-4 py-1.5 shadow flex items-center gap-2">
            <Spinner className="h-4 w-4 text-primario-400" />
            <span>
              Carregando {Math.min(doneCount + 1, activeData.length)} de {activeData.length} camadas
              <span className="text-gray-400"> · {loadingLabels.join(' e ')}…</span>
            </span>
          </div>
        </div>
      )}

      {errors.length > 0 && loadingLabels.length === 0 && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 pointer-events-none">
          <div className="bg-perigo-50 border border-perigo-200 text-xs text-perigo-700 rounded-full px-3 py-1 shadow" role="status">
            {prefixoErro}: {errors.map(id => LAYER_BY_ID[id].label).join(', ')}
          </div>
        </div>
      )}

      {mapError && (
        <div className="absolute top-14 left-1/2 -translate-x-1/2 z-20 pointer-events-none">
          <div className="bg-perigo-50 border border-perigo-200 text-xs text-perigo-700 rounded-lg px-3 py-2 shadow max-w-[520px]">
            Falha ao renderizar o mapa: {mapError}
          </div>
        </div>
      )}

      {!panelOpen && (
        <button
          onClick={() => setPanelOpen(true)}
          className="absolute top-4 left-4 z-20 bg-white hover:bg-gray-50 shadow-md rounded-lg px-3 py-2 text-xs font-medium text-gray-700 flex items-center gap-1.5 border border-gray-100 transition-colors"
        >
          <svg className="w-3.5 h-3.5 text-gray-500" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 15a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
          </svg>
          Camadas
        </button>
      )}

      {panelOpen && (
        <div className="absolute top-0 left-0 h-full w-72 shadow-xl z-20 border-r border-gray-100 overflow-hidden max-sm:top-auto max-sm:bottom-0 max-sm:h-[65%] max-sm:w-full max-sm:rounded-t-xl max-sm:border-t max-sm:border-r-0" data-testid="painel-camadas">
          <LayerPanel
            state={state}
            onChange={setState}
            onClose={() => setPanelOpen(false)}
            statuses={dados.statuses}
            matchedAsns={dados.matchedAsns}
            selectedIx={selectedIx}
            date={date}
            resumoScm={resumoScm}
            pixCobertura={(dados.resultById.pix?.data as { pix_cobertura?: PixCobertura } | undefined)?.pix_cobertura ?? null}
          />
        </div>
      )}

      <div className="absolute bottom-8 right-4 z-10">
        <Legend state={state} resumoScm={resumoScm} />
      </div>
    </div>
  )
}
