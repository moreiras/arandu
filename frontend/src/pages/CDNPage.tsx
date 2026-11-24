import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useActiveDate } from '../hooks/useSnapshot'
import { fetchCDNPresence, fetchExternalIXPs } from '../services/api'
import { countryToRegion, REGION_STYLE } from '../components/tables/ExternalIXPTable'
import { cdnSlug } from '../lib/cdn'
import type { CDNRow, CDNMatrixColumn } from '../types/api'
import { useOrdenacao } from '../lib/ordenacao'
import { ThOrdenavel } from '../components/ui/ThOrdenavel'
import { EstadoDados } from '../components/ui/EstadoDados'

// ─── CDN categories ───────────────────────────────────────────────────────────

type CDNCategory = 'CDN' | 'Cloud' | 'Streaming' | 'Social' | 'Games' | 'Segurança'

// Categorias vêm do `config/cdns.yaml` via `cdns.json` (campo `categorias`). Este mapa é só o plano B para snapshots publicados
// antes do campo existir (published/ é imutável); não acrescente CDN novo aqui.
// First entry = primary category (shown first, defines sort grouping if needed)
const CDN_CATEGORIES_LEGADO: Record<string, CDNCategory[]> = {
  'Cloudflare':            ['CDN', 'Segurança'],
  'Akamai':                ['CDN'],
  'Fastly':                ['CDN'],
  'Edgecast / Edgio':      ['CDN'],
  'CDN77':                 ['CDN'],
  'Gcore':                 ['CDN', 'Cloud'],
  'CDNetworks':            ['CDN'],
  'Bunny.net':             ['CDN'],
  'CacheFly':              ['CDN'],
  'GoCache':               ['CDN'],
  'CentralServer':         ['CDN'],
  'SingularCDN':           ['CDN'],
  'UPX':                   ['CDN', 'Segurança'],
  'Azion':                 ['CDN', 'Segurança'],
  'EdgeUno':               ['CDN'],
  'Google / YouTube':      ['Cloud', 'Streaming'],
  'Microsoft / Azure':     ['Cloud', 'Streaming'],
  'Amazon / AWS':          ['Cloud', 'Streaming'],
  'Alibaba Cloud CDN':     ['Cloud'],
  'IBM Cloud / SoftLayer': ['Cloud'],
  'Huawei Cloud CDN':      ['Cloud'],
  'Baidu Cloud':           ['Cloud'],
  'Yandex':                ['Cloud', 'Social'],
  'Netflix':               ['Streaming'],
  'Twitch / Amazon IVS':   ['Streaming', 'Games'],
  'Globo / GloboCDN':      ['Streaming'],
  'Apple':                 ['Streaming', 'Social'],
  'Yahoo / Oath':          ['Streaming', 'Social'],
  'Qwilt':                 ['Streaming', 'CDN'],
  'Meta / Facebook':       ['Social', 'Streaming'],
  'X / Twitter':           ['Social', 'Streaming'],
  'ByteDance / TikTok':    ['Social', 'Streaming'],
  'Tencent':               ['Social', 'Games', 'Streaming'],
  'Riot Games':            ['Games'],
  'Valve / Steam':         ['Games', 'CDN'],
  'i3D.net / Ubisoft':     ['Games', 'CDN'],
  'Epic Games':            ['Games'],
  'Imperva / Incapsula':   ['Segurança', 'CDN'],
  'Sucuri':                ['Segurança', 'CDN'],
  'Zscaler':               ['Segurança'],
  'Disney Streaming':      ['Streaming'],
  'Max / HBO Max':         ['Streaming'],
  'Roblox':                ['Games'],
  'MainStreaming':          ['CDN', 'Streaming'],
  'WordPress.com':         ['CDN', 'Social'],
  'Zoom':                  ['Streaming'],
  'CDNTV':                 ['CDN', 'Streaming'],
  'Huge Networks':         ['CDN'],
  'Sage Networks':         ['CDN'],
  'CORIX':                 ['CDN'],
  'OpenCDN':               ['CDN'],
  'EdgeNext':              ['CDN'],
  'Telegram':              ['Social'],
  'Wikimedia':             ['CDN'],
  'PlayStation / Sony':    ['Games'],
  'Garena':                ['Games'],
  'Oracle Cloud':          ['Cloud'],
  'TIVIT':                 ['Cloud'],
  'Cisco Umbrella':        ['Segurança'],
  'Netskope':              ['Segurança'],
  'Nexusguard':            ['Segurança'],
}

const CATEGORY_STYLE: Record<CDNCategory, { label: string; cls: string }> = {
  CDN:       { label: 'CDN',       cls: 'bg-primario-100 text-primario-700' },
  Cloud:     { label: 'Cloud',     cls: 'bg-estimado-100 text-estimado-700' },
  Streaming: { label: 'Streaming', cls: 'bg-perigo-100 text-perigo-700' },
  Social:    { label: 'Social',    cls: 'bg-v6-100 text-v6-700' },
  Games:     { label: 'Games',     cls: 'bg-mercado-100 text-mercado-700' },
  Segurança: { label: 'Segurança', cls: 'bg-aviso-100 text-aviso-700' },
}

/** Categorias do CDN: as do snapshot (`categorias`) ou, em snapshot anterior ao campo, o mapa legado. */
function categoriasDe(cdn: { name: string; categorias?: string[] }): CDNCategory[] | undefined {
  return cdn.categorias?.length ? (cdn.categorias as CDNCategory[]) : CDN_CATEGORIES_LEGADO[cdn.name]
}

function CategoryBadges({ cdn }: { cdn: { name: string; categorias?: string[] } }) {
  const cats = categoriasDe(cdn)
  if (!cats?.length) return null
  return (
    <span className="flex flex-wrap gap-0.5 mt-0.5">
      {cats.map(cat => {
        const { label, cls } = CATEGORY_STYLE[cat]
        return (
          <span key={cat} className={`text-xs font-semibold px-1 py-0.5 rounded leading-none ${cls}`}>
            {label}
          </span>
        )
      })}
    </span>
  )
}

// ─── Region stripe color for column headers ───────────────────────────────────

/** As colunas do IX.br ganham cor própria (amarelo, com contorno escuro para o contraste de 3:1 da NBR 17225 5.11.5). */
const IXBR_STRIPE = 'bg-ixbr-400 ring-1 ring-inset ring-ixbr-700'
const IXBR_ROTULO = 'IX.br (Brasil)'

const REGION_STRIPE: Record<string, string> = {
  'Brasil':     'bg-ok-400',
  'Am. Norte':  'bg-primario-400',
  'Am. Latina': 'bg-alerta-400',
  'Europa':     'bg-v6-400',
  'Asia':       'bg-tecnico-400',
  'Africa':     'bg-perigo-400',
}

// ─── Presence Matrix ─────────────────────────────────────────────────────────

function PresenceMatrix({
  cdns,
  columns,
  getPresence,
}: {
  cdns: CDNRow[]
  columns: CDNMatrixColumn[]
  getPresence: (cdn: CDNRow) => string[]
}) {
  const columnCodes = useMemo(() => new Set(columns.map(c => c.code)), [columns])
  // As colunas de PTT são entidades (presença sim/não); ordenam só o nome e o total, sobre todas as linhas.
  const { ordenados, props } = useOrdenacao(cdns, {
    nome: (c) => c.name,
    total: (c) => getPresence(c).filter(code => columnCodes.has(code)).length,
  })
  if (columns.length === 0) {
    return <p className="text-sm text-gray-400 py-4">Nenhuma fonte/coluna selecionada.</p>
  }

  return (
    <div className="overflow-x-auto border border-gray-200 rounded-lg">
      <table className="text-xs border-collapse" style={{ minWidth: columns.length * 28 + 240 }}>
        <caption className="sr-only">Presença de cada CDN ou CAP (linhas) em cada PTT (colunas)</caption>
        <thead>
          <tr>
            <ThOrdenavel {...props('nome')} className="sticky left-0 z-10 bg-gray-50 border-b border-r border-gray-200 px-3 py-2 text-left font-medium text-gray-600 min-w-[220px]">
              CDN / Provedor
            </ThOrdenavel>
            {columns.map(col => {
              const region = col.region
              const stripeCls = col.origin === 'ixbr' ? IXBR_STRIPE : region ? REGION_STRIPE[region] : undefined
              const linkPrefix = col.origin === 'external' ? 'ixp-externo' : 'ixp'
              return (
                <th
                  key={col.code}
                  scope="col"
                  className="border-b border-r border-gray-100 bg-gray-50 p-0"
                  style={{ width: 28, minWidth: 28 }}
                  title={col.origin === 'ixbr'
                    ? `${col.name} · ${IXBR_ROTULO} · ${col.cdn_count} CDNs`
                    : region
                    ? `${col.name} · ${region} · ${col.cdn_count} CDNs`
                    : `${col.name} · ${col.cdn_count} CDNs`
                  }
                >
                  {/* Vertical IXP name */}
                  <div className="flex items-end justify-center" style={{ height: 120, paddingBottom: stripeCls ? 2 : 6 }}>
                    <Link
                      to={`/${linkPrefix}/${col.code}`}
                      className="text-primario-600 hover:text-primario-800 hover:underline"
                      style={{
                        writingMode: 'vertical-rl',
                        transform: 'rotate(180deg)',
                        whiteSpace: 'nowrap',
                        fontSize: 11,
                        fontWeight: 500,
                      }}
                    >
                      {col.name}
                    </Link>
                    {/* região e contagem também fora do title (teclado e toque não o alcançam) */}
                    <span className="sr-only">{` · ${col.origin === 'ixbr' ? IXBR_ROTULO : region ?? ''} · ${col.cdn_count} CDNs`}</span>
                  </div>
                  {/* Region stripe at BOTTOM of header cell */}
                  {stripeCls && (
                    <div className={`w-full h-1.5 ${stripeCls}`} />
                  )}
                </th>
              )
            })}
            <ThOrdenavel {...props('total')} alinhar="right" className="border-b border-gray-200 bg-gray-50 px-2 text-right font-medium text-gray-500 whitespace-nowrap">
              Total
            </ThOrdenavel>
          </tr>
        </thead>
        <tbody>
          {ordenados.map((cdn, i) => {
            const presence = new Set(getPresence(cdn).filter(code => columnCodes.has(code)))
            const count = presence.size
            if (count === 0) return null
            // Solid background for even/odd rows — NO opacity so sticky left column is opaque
            const rowBg = i % 2 === 0 ? 'bg-white' : 'bg-gray-50'
            return (
              <tr key={cdn.name} className={rowBg}>
                {/* Sticky left cell: explicit solid bg matching the row, never transparent */}
                <th scope="row" className={`sticky left-0 z-10 border-r border-b border-gray-100 px-3 py-1.5 whitespace-nowrap text-left font-normal ${rowBg}`}>
                  <Link to={`/cdncap/${cdnSlug(cdn.name)}`} className="font-medium text-primario-700 hover:underline">
                    {cdn.name}
                  </Link>
                  <CategoryBadges cdn={cdn} />
                  <div className="text-gray-400 font-normal text-xs mt-0.5">
                    {cdn.asns.map(a => `AS${a}`).join(' · ')}
                  </div>
                </th>
                {columns.map(col => (
                  <td
                    key={col.code}
                    className="border-r border-b border-gray-100 text-center p-0"
                    style={{ width: 28 }}
                  >
                    {/* estado em texto para o leitor de tela; "●" e "·" são só reforço visual */}
                    {presence.has(col.code) ? (
                      <><span className="text-ok-600 text-base leading-none" aria-hidden="true">●</span><span className="sr-only">{`${cdn.name} em ${col.name}: presente`}</span></>
                    ) : (
                      <><span className="text-gray-400 text-base leading-none" aria-hidden="true">·</span><span className="sr-only">{`${cdn.name} em ${col.name}: ausente`}</span></>
                    )}
                  </td>
                ))}
                <td className="border-b border-gray-100 px-2 py-1.5 text-right tabular-nums font-semibold text-gray-700">
                  {count}
                </td>
              </tr>
            )
          })}
        </tbody>
        <tfoot>
          <tr className="bg-gray-50 border-t border-gray-200">
            <th scope="row" className="sticky left-0 bg-gray-50 border-r border-gray-200 px-3 py-1.5 text-left text-xs font-semibold text-gray-600">
              CDNs presentes
            </th>
            {columns.map(col => (
              <td key={col.code} className="border-r border-gray-100 text-center py-1.5">
                <span className="text-xs font-semibold text-gray-600">{col.cdn_count}</span>
              </td>
            ))}
            <td />
          </tr>
        </tfoot>
      </table>
    </div>
  )
}

// ─── Legends ─────────────────────────────────────────────────────────────────

function CategoryLegend({
  active,
  onToggle,
}: {
  active: Set<CDNCategory>
  onToggle: (cat: CDNCategory) => void
}) {
  return (
    <div className="flex flex-wrap gap-2 items-center">
      <span className="text-xs text-gray-500 mr-1">Categoria:</span>
      {(Object.entries(CATEGORY_STYLE) as [CDNCategory, { label: string; cls: string }][]).map(([cat, { label, cls }]) => (
        <button
          key={label}
          type="button"
          onClick={() => onToggle(cat)}
          aria-pressed={active.has(cat)}
          className={`text-xs font-semibold px-1.5 py-0.5 rounded transition-opacity ${cls} ${active.has(cat) ? '' : 'opacity-30 line-through'}`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

function RegionLegend({
  active,
  onToggle,
}: {
  active: Set<string>
  onToggle: (region: string) => void
}) {
  return (
    <div className="flex flex-wrap gap-3 items-center">
      <span className="text-xs text-gray-500 mr-1">Região (PTT):</span>
      <span className="flex items-center gap-1 text-xs">
        <span className={`inline-block w-4 h-1.5 rounded-sm ${IXBR_STRIPE}`} aria-hidden="true" />
        <span className="text-ixbr-800">{IXBR_ROTULO}</span>
      </span>
      {Object.entries(REGION_STRIPE).map(([region, stripeCls]) => {
        const textCls = (REGION_STYLE[region] ?? '').split(' ').find(c => c.startsWith('text-')) ?? 'text-gray-600'
        return (
          <button
            key={region}
            type="button"
            onClick={() => onToggle(region)}
            aria-pressed={active.has(region)}
            className={`flex items-center gap-1 text-xs transition-opacity ${active.has(region) ? '' : 'opacity-30 line-through'}`}
          >
            <span className={`inline-block w-4 h-1.5 rounded-sm ${stripeCls}`} aria-hidden="true" />
            <span className={textCls}>{region}</span>
          </button>
        )
      })}
    </div>
  )
}

// ─── CDNPage ──────────────────────────────────────────────────────────────────

const ALL_CATEGORIES = Object.keys(CATEGORY_STYLE) as CDNCategory[]
const ALL_REGIONS = Object.keys(REGION_STRIPE)

export function CDNPage() {
  const date = useActiveDate()
  const [showIxbr, setShowIxbr] = useState(true)
  const [showExternal, setShowExternal] = useState(true)
  const [activeCategories, setActiveCategories] = useState<Set<CDNCategory>>(new Set(ALL_CATEGORIES))
  const [activeRegions, setActiveRegions] = useState<Set<string>>(new Set(ALL_REGIONS))

  const { data, isLoading, error } = useQuery({
    queryKey: ['cdn-presence', date],
    queryFn: () => fetchCDNPresence(date ?? undefined),
    staleTime: Infinity, gcTime: Infinity,
  })

  const { data: extData } = useQuery({
    queryKey: ['external-ixps', date],
    queryFn: () => fetchExternalIXPs(date ?? undefined),
    staleTime: Infinity, gcTime: Infinity,
  })

  const extColRegion = useMemo(() => {
    const map: Record<string, string> = {}
    for (const ixp of extData?.ixps ?? []) {
      map[ixp.code] = countryToRegion(ixp.country)
    }
    return map
  }, [extData])

  const toggleCategory = (cat: CDNCategory) => {
    setActiveCategories(prev => {
      const next = new Set(prev)
      if (next.has(cat)) next.delete(cat)
      else next.add(cat)
      return next
    })
  }

  const toggleRegion = (region: string) => {
    setActiveRegions(prev => {
      const next = new Set(prev)
      if (next.has(region)) next.delete(region)
      else next.add(region)
      return next
    })
  }

  const columns: CDNMatrixColumn[] = useMemo(() => {
    if (!data) return []
    const cols: CDNMatrixColumn[] = []
    if (showIxbr) {
      for (const c of data.ixbr_columns) cols.push({ ...c, origin: 'ixbr' })
    }
    if (showExternal) {
      for (const c of data.external_columns) {
        const region = extColRegion[c.code]
        if (region && !activeRegions.has(region)) continue
        cols.push({ ...c, origin: 'external', region })
      }
    }
    // Single ordered set: IX.br and external IXPs are ranked together
    return cols.sort((a, b) => b.cdn_count - a.cdn_count || a.code.localeCompare(b.code))
  }, [data, showIxbr, showExternal, activeRegions, extColRegion])

  const columnCodes = useMemo(() => new Set(columns.map(c => c.code)), [columns])

  const visibleCdns = useMemo(() => {
    if (!data) return []
    return data.cdns
      .filter(cdn => {
        const cats = categoriasDe(cdn)
        if (cats?.length && !cats.some(c => activeCategories.has(c))) return false
        return true
      })
      .map(cdn => ({
        cdn,
        count: [...cdn.ixbr, ...cdn.external].filter(code => columnCodes.has(code)).length,
      }))
      .filter(({ count }) => count > 0)
      .sort((a, b) => b.count - a.count || a.cdn.name.localeCompare(b.cdn.name))
      .map(({ cdn }) => cdn)
  }, [data, activeCategories, columnCodes])

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-titulo-1 text-gray-900">Presença de CDNs e CAPs nos IXPs</h1>
        <p className="text-sm text-gray-500">
          Matriz de presença de CDNs e provedores de aplicações de conteúdo (CAPs) nos pontos de troca.
          IX.br: membros declarados via dashboard.ix.br. Outros IXPs: membros autodeclarados no PeeringDB.
        </p>
        {data && (
          <p className="text-xs text-gray-400">
            Snapshot: <span className="font-mono">{data.snapshot_date}</span> ·{' '}
            {visibleCdns.length} provedores ·{' '}
            {data.ixbr_columns.length} IXPs IX.br · {data.external_columns.length} outros IXPs
          </p>
        )}
      </div>

      {/* Source toggles */}
      <div className="flex flex-wrap gap-1 border-b border-gray-200 pb-3">
        <button
          type="button"
          onClick={() => setShowIxbr(v => !v)}
          aria-pressed={showIxbr}
          className={`px-4 py-1.5 text-sm font-medium rounded-full border transition-colors ${
            showIxbr
              ? 'bg-primario-50 border-primario-300 text-primario-700'
              : 'bg-white border-gray-200 text-gray-400 hover:text-gray-600'
          }`}
        >
          IX.br
          {data && <span className="ml-1.5 text-xs">({data.ixbr_columns.length})</span>}
        </button>
        <button
          type="button"
          onClick={() => setShowExternal(v => !v)}
          aria-pressed={showExternal}
          className={`px-4 py-1.5 text-sm font-medium rounded-full border transition-colors ${
            showExternal
              ? 'bg-primario-50 border-primario-300 text-primario-700'
              : 'bg-white border-gray-200 text-gray-400 hover:text-gray-600'
          }`}
        >
          Outros IXPs
          {data && <span className="ml-1.5 text-xs">({data.external_columns.length})</span>}
        </button>
      </div>

      {isLoading && <div className="h-64 bg-gray-100 rounded-lg animate-pulse" />}

      {error && <EstadoDados erro={error} oQue="os dados de CDNs" mensagem="Dados de CDNs não disponíveis neste snapshot." className="my-6" />}

      {data && (
        <div className="space-y-3">
          <p className="text-xs text-aviso-700 bg-aviso-50 border border-aviso-200 rounded px-3 py-2">
            Fonte: dashboard.ix.br para IX.br (membros registrados) e PeeringDB para outros IXPs
            (autodeclarado pelo ASN, pode subestimar a presença real).
            Ordenação: CDN presente em mais colunas visíveis no topo.
          </p>
          <div className="flex flex-wrap gap-4">
            <CategoryLegend active={activeCategories} onToggle={toggleCategory} />
            {showExternal && <RegionLegend active={activeRegions} onToggle={toggleRegion} />}
          </div>
          <PresenceMatrix
            cdns={visibleCdns}
            columns={columns}
            getPresence={cdn => [...cdn.ixbr, ...cdn.external]}
          />
        </div>
      )}
    </div>
  )
}
