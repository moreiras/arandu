// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Painel de camadas do mapa "Explorar": recorte de ASes, grupos de camadas, ajustes por camada. */
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchIXPs } from '../../../services/api'
import { DownloadIcon, CloseIcon, FunnelIcon, Spinner } from './icones'
import { hasRecorte, makeGroup, makePredicate } from './consulta'
import { Swatch } from './Legenda'
import { PredicateRow } from './PredicateRow'
import { INITIAL, LAYERS, LAYER_BY_ID } from './tipos'
import type { FilterGroup, LayerDef, LayerId, MapState, Predicate } from './tipos'

export interface LayerStatus {
  state: 'off' | 'queued' | 'loading' | 'error' | 'done'
  count?: number
  stale: boolean
  retry?: () => void
  download?: () => void
}

/** Predefinições do mapa: ligam um conjunto de camadas e desligam as outras; o recorte e os filtros não mudam. */
export const PREDEFINICOES: Array<{ id: string; rotulo: string; dica: string; camadas: LayerId[] }> = [
  { id: 'infraestrutura', rotulo: 'Infraestrutura', dica: 'PIX dos PTTs, cabos, enlaces, linhas de transmissão e rodovias federais', camadas: ['pix', 'submarine', 'terrestrial', 'power', 'roads_federal'] },
  { id: 'mercado', rotulo: 'Mercado', dica: 'Sedes dos ASes, operadores SCM, antenas do SMP e PIX', camadas: ['asns_geo', 'outorgas_scm', 'erbs', 'pix'] },
  { id: 'tecnico', rotulo: 'Técnico', dica: 'Prefixos IPv6 e IPv4 do Brasil e PIX', camadas: ['prefixes_v6', 'prefixes_v4', 'pix'] },
]

export function aplicarPredefinicao(state: MapState, camadas: LayerId[]): MapState {
  const on = Object.fromEntries(Object.keys(state.on).map((id) => [id, camadas.includes(id as LayerId)])) as MapState['on']
  return { ...state, on }
}

const inp = 'border border-gray-200 rounded px-1.5 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-primario-500 bg-white'
const sectionHdr = 'text-xs font-semibold uppercase tracking-wide text-gray-400'
const opBtn = (active: boolean) =>
  `text-xs px-1.5 py-0.5 rounded font-medium border transition-colors cursor-pointer ${
    active ? 'bg-primario-600 text-white border-primario-600' : 'border-gray-200 text-gray-500 hover:bg-gray-50'
  }`

function Section({
  title, extra, open, onToggle, children,
}: {
  title: string
  extra?: React.ReactNode
  open: boolean
  onToggle: () => void
  children: React.ReactNode
}) {
  return (
    <div className="border-b border-gray-100">
      <div className="flex items-center justify-between gap-2 px-3 pt-2.5 pb-1.5">
        <button onClick={onToggle} className={`${sectionHdr} flex items-center gap-1 hover:text-gray-600`}>
          <span className={`inline-block transition-transform ${open ? 'rotate-90' : ''}`}>▸</span>
          {title}
        </button>
        {extra}
      </div>
      {open && <div className="px-3 pb-3">{children}</div>}
    </div>
  )
}

function StatusBadge({ status }: { status: LayerStatus }) {
  switch (status.state) {
    case 'queued':
      return <span className="text-xs text-gray-400" title="Na fila">⏳</span>
    case 'loading':
      return (
        <span className="flex items-center gap-1">
          {status.count != null && <span className="text-xs text-gray-300 tabular-nums">{status.count.toLocaleString('pt-BR')}</span>}
          <Spinner />
        </span>
      )
    case 'error':
      return (
        <button onClick={status.retry} className="text-xs text-perigo-500 hover:text-perigo-700" title="Falhou. Clique para tentar de novo">
          ⚠ tentar de novo
        </button>
      )
    case 'done':
      return status.count != null
        ? <span className="text-xs text-gray-400 tabular-nums">{status.count.toLocaleString('pt-BR')}</span>
        : null
    default:
      return null
  }
}

function LayerRow({
  def, checked, onToggle, status, recorteActive, children,
}: {
  def: LayerDef
  checked: boolean
  onToggle: (v: boolean) => void
  status: LayerStatus
  recorteActive: boolean
  children?: React.ReactNode
}) {
  return (
    <div>
      <div className="flex items-center gap-1.5 py-0.5">
        <label className="flex items-center gap-1.5 cursor-pointer flex-1 min-w-0 text-xs text-gray-700">
          <input type="checkbox" checked={checked} onChange={e => onToggle(e.target.checked)} />
          <Swatch color={def.color} shape={def.shape} />
          <span className="truncate">{def.label}</span>
          {def.recorte && <FunnelIcon active={recorteActive} />}
        </label>
        {checked && <StatusBadge status={status} />}
        {checked && status.download && status.state === 'done' && (
          <button
            onClick={status.download}
            className="p-0.5 text-gray-300 hover:text-gray-600 transition-colors"
            title={`Baixar CSV: ${def.label}`}
          >
            <DownloadIcon />
          </button>
        )}
      </div>
      {checked && children && <div className="pl-5 pb-1 space-y-1">{children}</div>}
    </div>
  )
}

export function LayerPanel({
  state,
  onChange,
  onClose,
  statuses,
  matchedAsns,
  selectedIx,
  date,
}: {
  state: MapState
  onChange: (s: MapState) => void
  onClose: () => void
  statuses: Record<LayerId, LayerStatus>
  matchedAsns?: number | null
  selectedIx: string | null
  date?: string
}) {
  const set = (partial: Partial<MapState>) => onChange({ ...state, ...partial })
  const setOn = (id: LayerId, v: boolean) => set({ on: { ...state.on, [id]: v } })
  const [open, setOpen] = useState({ recorte: true, internet: true, ptt: true, infra: true })
  const toggleSection = (k: keyof typeof open) => setOpen({ ...open, [k]: !open[k] })

  const { data: ixpData } = useQuery({
    queryKey: ['ixps', date],
    queryFn: () => fetchIXPs(date),
    staleTime: Infinity,
    gcTime: Infinity,
  })
  const ixpOptions = useMemo(() =>
    (ixpData?.ixps ?? [])
      .filter(ix => ix.status !== 'missing')
      .sort((a, b) => a.name.localeCompare(b.name, 'pt-BR')),
    [ixpData],
  )

  const recorteActive = hasRecorte(state)
  const recorteLayerOn = LAYERS.some(l => l.recorte && state.on[l.id])
  const pttOn = state.on.prefixos_ix_v4 || state.on.prefixos_ix_v6

  const addGroup = () => {
    const g = makeGroup()
    g.predicates.push(makePredicate())
    set({ groups: [...state.groups, g] })
  }
  const removeGroup = (gid: string) =>
    set({ groups: state.groups.filter(g => g.id !== gid) })
  const updateGroup = (gid: string, partial: Partial<FilterGroup>) =>
    set({ groups: state.groups.map(g => g.id === gid ? { ...g, ...partial } : g) })
  const addPredicate = (gid: string) => {
    const g = state.groups.find(g => g.id === gid)
    if (!g) return
    updateGroup(gid, { predicates: [...g.predicates, makePredicate()] })
  }
  const updatePredicate = (gid: string, pid: string, partial: Partial<Predicate>) => {
    const g = state.groups.find(g => g.id === gid)
    if (!g) return
    updateGroup(gid, { predicates: g.predicates.map(p => p.id === pid ? { ...p, ...partial } : p) })
  }
  const removePredicate = (gid: string, pid: string) => {
    const g = state.groups.find(g => g.id === gid)
    if (!g) return
    const preds = g.predicates.filter(p => p.id !== pid)
    if (preds.length === 0) removeGroup(gid)
    else updateGroup(gid, { predicates: preds })
  }

  const isDirty = JSON.stringify({ ...state, groups: state.groups.length }) !== JSON.stringify({ ...INITIAL, groups: 0 })

  const row = (id: LayerId, children?: React.ReactNode) => (
    <LayerRow
      key={id}
      def={LAYER_BY_ID[id]}
      checked={state.on[id]}
      onToggle={v => setOn(id, v)}
      status={statuses[id]}
      recorteActive={recorteActive}
    >
      {children}
    </LayerRow>
  )

  const pavedToggle = (key: 'roadsFederalPaved' | 'roadsEstadualPaved') => (
    <label className="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer">
      <input type="checkbox" checked={state[key]} onChange={e => set({ [key]: e.target.checked } as Partial<MapState>)} />
      só pavimentadas
    </label>
  )

  const sources = [
    state.on.submarine && 'Cabos: © TeleGeography (CC BY-SA 4.0)',
    state.on.terrestrial && 'Terrestre: ITU BBmaps',
    state.on.power && 'Linhas de transmissão: SIGEL/ANEEL',
    (state.on.roads_federal || state.on.roads_estadual) && 'Rodovias: IBGE/BC250',
    state.on.erbs && 'Antenas: Anatel (estações do SMP licenciadas)',
  ].filter(Boolean) as string[]

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-gray-100 flex-shrink-0">
        <span className="text-sm font-semibold text-gray-800">Mapa</span>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-100 rounded text-gray-400 hover:text-gray-600 transition-colors"
          title="Fechar"
        >
          <CloseIcon className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-1 px-3 py-1.5 border-b border-gray-100 flex-shrink-0" role="group" aria-label="Predefinições de camadas">
        <span className="text-xs text-gray-400 mr-1">Predefinições</span>
        {PREDEFINICOES.map((pd) => {
          const ativa = LAYERS.every((l) => state.on[l.id] === pd.camadas.includes(l.id))
          return (
            <button key={pd.id} type="button" title={pd.dica} aria-pressed={ativa} onClick={() => onChange(aplicarPredefinicao(state, pd.camadas))}
              className={`text-xs px-2 py-0.5 rounded border ${ativa ? 'bg-primario-600 text-white border-primario-600' : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}>{pd.rotulo}</button>
          )
        })}
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* Recorte de ASes */}
        <Section
          title="Recorte de ASes"
          open={open.recorte}
          onToggle={() => toggleSection('recorte')}
          extra={matchedAsns != null && (
            <span className="text-xs text-gray-500 bg-gray-100 rounded px-1.5 py-0.5 tabular-nums">
              {matchedAsns.toLocaleString('pt-BR')} ASes
            </span>
          )}
        >
          <div className="space-y-3">
            <p className="text-xs text-gray-400 leading-snug flex items-start gap-1">
              <FunnelIcon active /> <span>Vale para as camadas marcadas com o funil.</span>
            </p>

            <div>
              <h4 className="text-xs text-gray-500 mb-1">Proximidade de PTT</h4>
              <div className="space-y-1.5">
                <select
                  aria-label="PTT de referência da proximidade"
                  value={state.nearIxp}
                  onChange={e => set({ nearIxp: e.target.value })}
                  className={`w-full ${inp}`}
                  disabled={ixpOptions.length === 0}
                >
                  <option value="">Sem filtro</option>
                  {ixpOptions.map(ix => (
                    <option key={ix.code} value={ix.code}>{ix.name}, {ix.uf}</option>
                  ))}
                </select>
                {state.nearIxp && (
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <input
                      type="number"
                      min={10} max={2000} step={10}
                      value={state.nearRadiusKm}
                      onChange={e => set({ nearRadiusKm: Number(e.target.value) })}
                      className={`w-16 ${inp}`}
                    />
                    <span className="text-xs text-gray-400">km por</span>
                    <button onClick={() => set({ nearMode: 'sede' })} className={opBtn(state.nearMode === 'sede')}>sede</button>
                    <button onClick={() => set({ nearMode: 'prefixos' })} className={opBtn(state.nearMode === 'prefixos')}>prefixos</button>
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-xs text-gray-500">Filtros</h4>
                {state.groups.length > 1 && (
                  <div className="flex items-center gap-1">
                    <span className="text-xs text-gray-400">grupos:</span>
                    <button onClick={() => set({ groupOp: 'and' })} className={opBtn(state.groupOp === 'and')}>AND</button>
                    <button onClick={() => set({ groupOp: 'or' })}  className={opBtn(state.groupOp === 'or')}>OR</button>
                  </div>
                )}
              </div>

              {state.groups.length === 0 && (
                <p className="text-xs text-gray-400">Sem filtros: todos os ASes.</p>
              )}

              {state.groups.map((group, gi) => (
                <div key={group.id} className="border border-gray-200 rounded-lg overflow-hidden">
                  <div className="flex items-center justify-between px-2 py-1.5 bg-gray-50 border-b border-gray-100">
                    <div className="flex items-center gap-1">
                      <span className="text-xs text-gray-400">G{gi + 1}</span>
                      <button onClick={() => updateGroup(group.id, { op: 'and' })} className={opBtn(group.op === 'and')}>AND</button>
                      <button onClick={() => updateGroup(group.id, { op: 'or' })}  className={opBtn(group.op === 'or')}>OR</button>
                    </div>
                    <button
                      onClick={() => removeGroup(group.id)}
                      className="text-gray-300 hover:text-perigo-400 transition-colors p-0.5"
                      title="Remover grupo"
                    >
                      <CloseIcon />
                    </button>
                  </div>
                  <div className="px-2 py-1.5 space-y-1">
                    {group.predicates.map(pred => (
                      <PredicateRow
                        key={pred.id}
                        predicate={pred}
                        onChange={partial => updatePredicate(group.id, pred.id, partial)}
                        onRemove={() => removePredicate(group.id, pred.id)}
                      />
                    ))}
                    <button
                      onClick={() => addPredicate(group.id)}
                      className="text-xs text-primario-500 hover:text-primario-700 transition-colors py-0.5"
                    >
                      + filtro
                    </button>
                  </div>
                </div>
              ))}

              <button
                onClick={addGroup}
                className="w-full text-xs text-primario-600 hover:text-primario-800 py-1.5 border border-dashed border-primario-200 hover:border-primario-400 rounded-lg transition-colors"
              >
                + grupo de filtros
              </button>
            </div>

            {recorteActive && !recorteLayerOn && (
              <p className="text-xs text-aviso-600 bg-aviso-50 rounded px-2 py-1 leading-snug">
                O recorte não afeta nenhuma camada ligada. Ligue uma camada com o funil.
              </p>
            )}
          </div>
        </Section>

        {/* Internet */}
        <Section title="Internet" open={open.internet} onToggle={() => toggleSection('internet')}>
          {row('asns_geo', (
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-gray-400 flex-shrink-0">Colorir por</span>
              <select
                aria-label="Colorir por"
                value={state.colorBy}
                onChange={e => set({ colorBy: e.target.value })}
                className={`flex-1 min-w-0 ${inp}`}
              >
                <option value="solid">Cor única</option>
                <option value="visibility">Visibilidade IPv6/IPv4</option>
                <option value="rpki">RPKI</option>
                <option value="aspa">ASPA</option>
                <option value="porte">Porte da empresa</option>
                <option value="pct_v6">% usuários IPv6</option>
                <option value="outorga">Outorga SCM</option>
              </select>
            </div>
          ))}
          {row('outorgas_scm', (<>
            <div className="flex items-center gap-1">
              <button onClick={() => set({ scmMode: 'todas' })}   className={opBtn(state.scmMode === 'todas')}>todas</button>
              <button onClick={() => set({ scmMode: 'com_asn' })} className={opBtn(state.scmMode === 'com_asn')}>com ASN</button>
              <button onClick={() => set({ scmMode: 'sem_asn' })} className={opBtn(state.scmMode === 'sem_asn')}>sem ASN</button>
            </div>
            <p className="text-xs text-gray-400 leading-snug" data-testid="nota-scm-sici">
              O balão mostra os acessos declarados à Anatel no mês de referência do SICI (sistema Coleta de Dados, Resolução Anatel nº 774/2025). Sem acessos declarados é só um fato sobre a declaração: o mapa não avalia o cumprimento da norma.
            </p>
            {recorteActive && state.scmMode !== 'com_asn' && (
              <p className="text-xs text-gray-400 leading-snug">
                Outorgas sem ASN não são ASes: com filtros elas ficam de fora; só com proximidade, vale a localização da outorga.
              </p>
            )}
          </>))}
          {row('prefixes_v6')}
          {row('prefixes_v4')}
        </Section>

        {/* PTT */}
        <Section
          title="PTT"
          open={open.ptt}
          onToggle={() => toggleSection('ptt')}
          extra={(
            <select
              aria-label="PTT"
              value={state.ixCode}
              onChange={e => set({ ixCode: e.target.value })}
              className={`max-w-[150px] ${inp} text-xs`}
              disabled={ixpOptions.length === 0}
              title="PTT das camadas deste grupo"
            >
              {ixpOptions.length === 0 && <option value="sp">Carregando…</option>}
              {ixpOptions.map(ix => (
                <option key={ix.code} value={ix.code}>{ix.name}, {ix.uf}</option>
              ))}
            </select>
          )}
        >
          {row('prefixos_ix_v6')}
          {row('prefixos_ix_v4')}
          {pttOn && (
            <div className="pl-5 pt-1 space-y-1">
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-gray-400 flex-shrink-0 w-14">excluir AS</span>
                <input
                  type="text"
                  value={state.ixExcludeAsns}
                  onChange={e => set({ ixExcludeAsns: e.target.value })}
                  placeholder="ex: 6939"
                  className={`flex-1 min-w-0 ${inp}`}
                  title="Excluir rotas onde estes ASes aparecem no caminho"
                />
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-gray-400 flex-shrink-0 w-14">apenas AS</span>
                <input
                  type="text"
                  value={state.ixIncludeAsns}
                  onChange={e => set({ ixIncludeAsns: e.target.value })}
                  placeholder="ex: 6939"
                  className={`flex-1 min-w-0 ${inp}`}
                  title="Manter apenas rotas onde estes ASes aparecem no caminho"
                />
              </div>
            </div>
          )}
        </Section>

        {/* Infraestrutura física */}
        <Section title="Infraestrutura física" open={open.infra} onToggle={() => toggleSection('infra')}>
          {row('pix', selectedIx && (
            <label className="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer">
              <input type="checkbox" checked={state.pixOnlySelected} onChange={e => set({ pixOnlySelected: e.target.checked })} />
              só do PTT selecionado ({selectedIx})
            </label>
          ))}
          {row('submarine')}
          {row('terrestrial')}
          {row('power')}
          {row('erbs', (
            <label className="flex items-center gap-1.5 text-xs text-gray-500">
              geração
              <select aria-label="Geração das ERBs" value={state.erbsGeracao} onChange={e => set({ erbsGeracao: e.target.value })} className="border border-gray-200 rounded px-1 py-0.5 text-xs">
                <option value="">todas</option>
                {['2G', '3G', '4G', '5G'].map(g => <option key={g} value={g}>{g}</option>)}
              </select>
            </label>
          ))}
          {row('roads_federal', pavedToggle('roadsFederalPaved'))}
          {row('roads_estadual', pavedToggle('roadsEstadualPaved'))}
        </Section>

        {sources.length > 0 && (
          <p className="px-3 pt-2 text-xs text-gray-400 leading-tight">
            Fontes: {sources.join(' · ')}
          </p>
        )}

        {isDirty && (
          <div className="px-3 py-3">
            <button
              onClick={() => onChange(INITIAL)}
              className="w-full text-xs text-gray-400 hover:text-gray-600 py-1 transition-colors"
            >
              Limpar tudo
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
