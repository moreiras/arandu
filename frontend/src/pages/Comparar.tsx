import { useState, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Link } from '../components/layout/LinkDatado'
import { useQuery } from '@tanstack/react-query'
import { fetchIXPs, fetchExternalIXPs, fetchIXP, fetchSnapshot, fetchIXPCompareMembers, AccessError } from '../services/api'
import { useActiveDate } from '../hooks/useSnapshot'
import { ComparaDatas } from '../features/comparar/ComparaDatas'
import { AccessPanel } from '../components/AccessPanel'
import { isIXPAfiFull } from '../types/api'
import type { IXPAfiFull } from '../types/api'
import { MIN_SETS, MAX_SETS, parseVal, makeVal, IXPSelect } from '../features/comparar/IXPSelect'
import type { SelType, IXPOption } from '../features/comparar/IXPSelect'
import { AfiMetricsTable } from '../features/comparar/MetricasAfi'
import { CompararEntidades } from '../features/comparar/CompararEntidades'
import { tipoEIds, TIPOS, urlComparar } from '../features/comparar/entidades'
import { comboKey, allCombos, VennDiagram, UpSetPlot, ParticipantsTable } from '../features/comparar/Conjuntos'

/** Comparar IXPs (/comparar): a página seleciona os IXPs e compõe os componentes de `features/comparar/`. */
function CompararPtts({ inicial = [] }: { inicial?: string[] }) {
  const date = useActiveDate()
  // `?tipo=ixp&ids=sp,rj` abre a comparação já montada; sem ids, dois espaços vazios como sempre.
  const [vals, setVals] = useState<string[]>(() => { const v = inicial.map((c) => makeVal('ixbr', c)); while (v.length < MIN_SETS) v.push(''); return v })
  const [selectedCombos, setSelectedCombos] = useState<Set<string>>(new Set())

  function setVal(i: number, v: string) {
    setVals(prev => prev.map((old, idx) => (idx === i ? v : old)))
    setSelectedCombos(new Set())
  }

  function addSlot() {
    if (vals.length >= MAX_SETS) return
    setVals(prev => [...prev, ''])
  }

  function removeSlot(i: number) {
    if (vals.length <= MIN_SETS) return
    setVals(prev => prev.filter((_, idx) => idx !== i))
    setSelectedCombos(new Set())
  }

  const sels = vals.map(parseVal)
  const filledSels = sels.filter((s): s is { type: SelType; code: string } => s !== null)
  const allFilled = filledSels.length === sels.length && sels.length >= MIN_SETS

  // ── Data lists ─────────────────────────────────────────────────────────────

  const { data: ixpList } = useQuery({
    queryKey: ['ixps', date],
    queryFn: () => fetchIXPs(date ?? undefined),
    staleTime: Infinity, gcTime: Infinity,
  })

  const { data: extList } = useQuery({
    queryKey: ['external-ixps', date],
    queryFn: () => fetchExternalIXPs(date ?? undefined),
    staleTime: Infinity, gcTime: Infinity,
  })

  const options = useMemo<IXPOption[]>(() => {
    const ixbr = [...(ixpList?.ixps ?? [])]
      .sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'))
      .map(ixp => ({
        val: makeVal('ixbr', ixp.code),
        label: `IX.br ${ixp.name}, ${ixp.uf} (${ixp.code.toUpperCase()})`,
        type: 'ixbr' as SelType,
        code: ixp.code,
      }))
    const ext = [...(extList?.ixps ?? [])]
      .sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'))
      .map(ixp => ({
        val: makeVal('ext', ixp.code),
        label: `${ixp.name} (${ixp.city}, ${ixp.country})`,
        type: 'ext' as SelType,
        code: ixp.code,
      }))
    return [...ixbr, ...ext]
  }, [ixpList, extList])

  function displayName(sel: { type: SelType; code: string } | null): string {
    if (!sel) return '?'
    const opt = options.find(o => o.val === makeVal(sel.type, sel.code))
    if (opt) return opt.label
    return sel.code.toUpperCase()
  }

  const labels = sels.map(displayName)
  const compareKeys = vals // já no formato "ixbr:sp" / "ext:code", exigido pela API

  // ── Comparação N-way (endpoint enriquecido) ─────────────────────────────────

  const { data: compareData, isLoading: loadingCompare, isError: errorCompare, error: compareErr } = useQuery({
    queryKey: ['ixp-compare-members', compareKeys, date],
    queryFn: () => fetchIXPCompareMembers(compareKeys, date ?? undefined),
    enabled: allFilled,
    staleTime: 5 * 60 * 1000,
  })

  const hasExternal = filledSels.some(s => s.type === 'ext')

  // Combinações e contagens
  const combosWithCounts = useMemo(() => {
    if (!compareData) return []
    const n = sels.length
    const combos = allCombos(n)
    const countByKey = new Map<string, number>()
    for (const p of compareData.participants) {
      const idx = p.member_of.map(k => compareKeys.indexOf(k)).filter(i => i >= 0)
      const key = comboKey(idx)
      countByKey.set(key, (countByKey.get(key) ?? 0) + 1)
    }
    return combos
      .map(combo => ({ key: comboKey(combo), combo, count: countByKey.get(comboKey(combo)) ?? 0 }))
      .sort((a, b) => b.count - a.count)
  }, [compareData, sels.length, compareKeys])

  const vennCounts = useMemo(() => {
    const out: Record<string, number> = {}
    for (const c of combosWithCounts) out[c.key] = c.count
    return out
  }, [combosWithCounts])

  const labelByKey = useMemo(() => {
    const out: Record<string, string> = {}
    compareKeys.forEach((k, i) => { out[k] = labels[i] })
    return out
  }, [compareKeys, labels])

  const visibleParticipants = useMemo(() => {
    if (!compareData) return []
    if (selectedCombos.size === 0) return compareData.participants
    return compareData.participants.filter(p => {
      const idx = p.member_of.map(k => compareKeys.indexOf(k)).filter(i => i >= 0)
      return selectedCombos.has(comboKey(idx))
    })
  }, [compareData, selectedCombos, compareKeys])

  function toggleCombo(key: string) {
    setSelectedCombos(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  // ── Métricas BGP clássicas (só quando exatamente 2 IX.br são comparados) ────

  const twoIxbr = sels.length === 2 && sels[0]?.type === 'ixbr' && sels[1]?.type === 'ixbr'

  const { data: ixpAData } = useQuery({
    queryKey: ['ixp-sel', sels[0]?.code, date],
    queryFn: () => fetchIXP(sels[0]!.code, date ?? undefined),
    enabled: twoIxbr,
    staleTime: Infinity, gcTime: Infinity,
  })
  const { data: ixpBData } = useQuery({
    queryKey: ['ixp-sel', sels[1]?.code, date],
    queryFn: () => fetchIXP(sels[1]!.code, date ?? undefined),
    enabled: twoIxbr,
    staleTime: Infinity, gcTime: Infinity,
  })

  const { data: snapshotDetails } = useQuery({
    queryKey: ['snapshot-details', date],
    queryFn: () => fetchSnapshot(date!),
    enabled: !!date && twoIxbr,
    staleTime: Infinity, gcTime: Infinity,
  })
  const globalTable = snapshotDetails?.summary?.global_table

  const v4A = twoIxbr && ixpAData && isIXPAfiFull(ixpAData.v4 as Parameters<typeof isIXPAfiFull>[0]) ? ixpAData.v4 as IXPAfiFull : null
  const v4B = twoIxbr && ixpBData && isIXPAfiFull(ixpBData.v4 as Parameters<typeof isIXPAfiFull>[0]) ? ixpBData.v4 as IXPAfiFull : null
  const v6A = twoIxbr && ixpAData && isIXPAfiFull(ixpAData.v6 as Parameters<typeof isIXPAfiFull>[0]) ? ixpAData.v6 as IXPAfiFull : null
  const v6B = twoIxbr && ixpBData && isIXPAfiFull(ixpBData.v6 as Parameters<typeof isIXPAfiFull>[0]) ? ixpBData.v6 as IXPAfiFull : null

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Comparar PTTs</h1>
        <p className="text-sm text-gray-500 mt-1">
          Compare a sobreposição de membros entre 2 e 4 PTTs. Os PTTs do IX.br usam membros
          registrados no IX.br; os externos usam membros declarados no PeeringDB.
        </p>
      </div>

      {/* Seleção */}
      <div className="space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {vals.map((v, i) => (
            <IXPSelect
              key={i}
              id={`ixp-${i}`}
              label={`PTT ${String.fromCharCode(65 + i)}`}
              value={v}
              onChange={nv => setVal(i, nv)}
              options={options}
              disabledVals={vals.filter((_, idx) => idx !== i)}
              onRemove={vals.length > MIN_SETS ? () => removeSlot(i) : undefined}
            />
          ))}
        </div>
        {vals.length < MAX_SETS && (
          <button
            type="button"
            onClick={addSlot}
            className="text-xs px-3 py-1.5 rounded border border-dashed border-gray-300 text-gray-500 hover:border-primario-400 hover:text-primario-600"
          >
            + adicionar PTT ({vals.length}/{MAX_SETS})
          </button>
        )}
      </div>

      {allFilled && hasExternal && (
        <div className="text-xs text-aviso-700 bg-aviso-50 border border-aviso-200 rounded px-3 py-2">
          A comparação envolve ao menos um IXP externo (PeeringDB): os dados de membros são autodeclarados e
          exigem autenticação. Se você não estiver logado, a comparação abaixo não vai carregar.
        </div>
      )}

      {allFilled && loadingCompare && (
        <div className="text-center py-12 text-gray-400 text-sm animate-pulse">Carregando participantes…</div>
      )}

      {allFilled && errorCompare && compareErr instanceof AccessError && (
        <AccessPanel compact reason={compareErr.kind === 'limit' ? 'esgotado' : 'geral'} />
      )}

      {allFilled && errorCompare && !(compareErr instanceof AccessError) && (
        <div className="text-center py-12 text-perigo-500 text-sm">
          Erro ao carregar comparação{compareErr instanceof Error ? `: ${compareErr.message}` : ''}.
        </div>
      )}

      {allFilled && compareData && (
        <div className="space-y-6">
          <p className="text-xs text-gray-500">
            Participantes pelo cadastro de cada PTT (IX.br: dashboard.ix.br; externos: PeeringDB), snapshot de {compareData.snapshot_date}.
            O cadastro inclui quem troca tráfego só por acordos bilaterais, sem sessão com os route servers; a página de cada AS
            mostra a presença observada no BGP, que pode ser diferente.
          </p>
          {/* Venn (≤3) */}
          {sels.length <= 3 && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Diagrama de Venn</h3>
              <VennDiagram labels={labels} counts={vennCounts} />
            </div>
          )}

          {/* UpSet (2–4, interativo) */}
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">
              Combinações (UpSet): clique numa coluna para filtrar a lista abaixo
            </h3>
            <UpSetPlot
              labels={labels}
              counts={combosWithCounts}
              selected={selectedCombos}
              onToggle={toggleCombo}
            />
            {selectedCombos.size > 0 && (
              <button
                type="button"
                onClick={() => setSelectedCombos(new Set())}
                className="mt-2 text-xs text-primario-600 hover:underline"
              >
                limpar seleção
              </button>
            )}
          </div>

          {/* Tabela de participantes */}
          <ParticipantsTable participants={visibleParticipants} labelByKey={labelByKey} />

          {/* Métricas comparativas clássicas — só para exatamente 2 IX.br */}
          {twoIxbr && (v4A || v4B || v6A || v6B) && (
            <div className="space-y-4">
              <h3 className="text-sm font-medium text-gray-700">Métricas BGP (IX.br)</h3>
              <AfiMetricsTable title="IPv6" afiA={v6A} afiB={v6B} labelA={labels[0]} labelB={labels[1]} brCovInFT={globalTable?.v6_br_coverage_pct} />
              <AfiMetricsTable title="IPv4" afiA={v4A} afiB={v4B} labelA={labels[0]} labelB={labels[1]} brCovInFT={globalTable?.v4_br_coverage_pct} />
            </div>
          )}
        </div>
      )}

      {!allFilled && options.length > 0 && (
        <div className="text-center py-12 text-gray-400 text-sm">
          Selecione pelo menos dois PTTs acima para comparar.
        </div>
      )}
    </div>
  )
}

/**
 * `/comparar`: PTTs (padrão, o comparador de antes), ASes, operadoras e municípios (2 a 4 lado a lado, escolha na URL `?tipo=…&ids=…`) e, com `?modo=datas`,
 * dois snapshots. Aliases: `?asn=`, `?operadora=` e `?municipio=` valem como `?tipo=…&ids=…`.
 */
import { EntradaComparador } from '../features/comparar/EntradaComparador'

export function Comparar() {
  const [params] = useSearchParams()
  const datas = params.get('modo') === 'datas'
  const { tipo, ids } = tipoEIds(params)
  const aba = (ativa: boolean) => `px-3 py-1.5 text-sm rounded ${ativa ? 'bg-primario-100 text-primario-800' : 'text-gray-600 hover:bg-gray-100'}`
  return (
    <div className="space-y-6">
      <nav className="flex flex-wrap gap-2" aria-label="Tipo de comparação">
        {TIPOS.map((t) => <Link key={t.id} to={t.id === 'ixp' ? '/comparar' : urlComparar(t.id, [])} className={aba(!datas && tipo === t.id)} aria-current={!datas && tipo === t.id ? 'page' : undefined}>{t.rotulo}</Link>)}
        <Link to="/comparar?modo=datas" className={aba(datas)} aria-current={datas ? 'page' : undefined}>Datas</Link>
      </nav>
      {!datas && ids.length === 0 && <EntradaComparador />}
      {datas ? (
        <div className="space-y-5">
          <h1 className="text-titulo-1 text-gray-900">Comparar datas</h1>
          <ComparaDatas />
        </div>
      ) : tipo === 'ixp' ? <CompararPtts key={ids.join(',')} inicial={ids} /> : (
        <div className="space-y-4">
          <h1 className="text-titulo-1 text-gray-900">Comparar {TIPOS.find((t) => t.id === tipo)!.rotulo.toLowerCase()}</h1>
          <CompararEntidades key={tipo} tipo={tipo} />
        </div>
      )}
    </div>
  )
}
