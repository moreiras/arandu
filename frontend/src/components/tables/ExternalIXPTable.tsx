import { useState, useMemo } from 'react'
import { Link } from '../layout/LinkDatado'
import type { ExternalIXPIndexEntry } from '../../types/api'
import { Dica } from '../ui/Dica'

// ── Region mapping ───────────────────────────────────────────────────────────

const COUNTRY_REGION: Record<string, string> = {
  // Brasil
  BR: 'Brasil',
  // América do Norte
  US: 'Am. Norte', CA: 'Am. Norte', MX: 'Am. Norte',
  // América Latina (Sul + Central + Caribe)
  AR: 'Am. Latina', CL: 'Am. Latina', CO: 'Am. Latina', PE: 'Am. Latina',
  UY: 'Am. Latina', PY: 'Am. Latina', EC: 'Am. Latina', BO: 'Am. Latina',
  VE: 'Am. Latina', GT: 'Am. Latina', CR: 'Am. Latina', PA: 'Am. Latina',
  DO: 'Am. Latina', CU: 'Am. Latina', TT: 'Am. Latina', JM: 'Am. Latina',
  // Europa
  DE: 'Europa', NL: 'Europa', GB: 'Europa', PT: 'Europa', ES: 'Europa',
  FR: 'Europa', IT: 'Europa', SE: 'Europa', NO: 'Europa', FI: 'Europa',
  DK: 'Europa', CH: 'Europa', AT: 'Europa', BE: 'Europa', PL: 'Europa',
  CZ: 'Europa', SK: 'Europa', HU: 'Europa', RO: 'Europa', BG: 'Europa',
  GR: 'Europa', HR: 'Europa', SI: 'Europa', RU: 'Europa', UA: 'Europa',
  IE: 'Europa', LU: 'Europa', IS: 'Europa', LT: 'Europa', LV: 'Europa',
  EE: 'Europa', RS: 'Europa', ME: 'Europa', MK: 'Europa',
  // Ásia / Pacífico
  JP: 'Asia', CN: 'Asia', SG: 'Asia', HK: 'Asia', IN: 'Asia',
  AU: 'Asia', NZ: 'Asia', KR: 'Asia', TW: 'Asia', TH: 'Asia',
  MY: 'Asia', ID: 'Asia', PH: 'Asia', VN: 'Asia', BD: 'Asia',
  PK: 'Asia', LK: 'Asia', MM: 'Asia',
  // Oriente Médio (exibido como Ásia)
  AE: 'Asia', SA: 'Asia', IL: 'Asia', TR: 'Asia', IR: 'Asia', QA: 'Asia',
  // África
  ZA: 'Africa', NG: 'Africa', KE: 'Africa', EG: 'Africa', TZ: 'Africa',
  GH: 'Africa', ET: 'Africa', MA: 'Africa', TN: 'Africa', AO: 'Africa',
  MZ: 'Africa', SN: 'Africa',
}

export const REGION_STYLE: Record<string, string> = {
  'Brasil':     'text-ok-700 bg-ok-50',
  'Am. Norte':  'text-primario-700 bg-primario-50',
  'Am. Latina': 'text-alerta-700 bg-alerta-50',
  'Europa':     'text-v6-700 bg-v6-50',
  'Asia':       'text-tecnico-700 bg-tecnico-50',
  'Africa':     'text-perigo-700 bg-perigo-50',
}

export function countryToRegion(country: string): string {
  return COUNTRY_REGION[country.toUpperCase()] ?? country
}

// ── Flags ────────────────────────────────────────────────────────────────────

const FLAG: Record<string, string> = {
  BR: '🇧🇷', AR: '🇦🇷', CL: '🇨🇱', CO: '🇨🇴', PE: '🇵🇪',
  US: '🇺🇸', NL: '🇳🇱', DE: '🇩🇪', GB: '🇬🇧', PT: '🇵🇹',
  FR: '🇫🇷', ES: '🇪🇸', JP: '🇯🇵', SG: '🇸🇬', AU: '🇦🇺',
  ZA: '🇿🇦', AO: '🇦🇴', PY: '🇵🇾', UY: '🇺🇾',
}

// ── Sort types ───────────────────────────────────────────────────────────────

type SortKey = 'name' | 'region' | 'location' | 'member_count' | 'br_member_count' | 'pct_br'
type SortDir = 'asc' | 'desc'

function sortValue(ixp: ExternalIXPIndexEntry, key: SortKey): string | number {
  switch (key) {
    case 'name': return ixp.name
    case 'region': return countryToRegion(ixp.country)
    case 'location': return `${ixp.country} ${ixp.city}`
    case 'member_count': return ixp.member_count
    case 'br_member_count': return ixp.br_member_count
    case 'pct_br': return ixp.member_count > 0 ? ixp.br_member_count / ixp.member_count : 0
  }
}

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <span className="text-gray-300 ml-0.5">↕</span>
  return <span className="text-gray-700 ml-0.5">{dir === 'asc' ? '↑' : '↓'}</span>
}

interface ThProps {
  label: string
  tooltip: string
  sortKey: SortKey
  current: SortKey
  dir: SortDir
  onSort: (k: SortKey) => void
  className?: string
  align?: 'left' | 'right'
}

function Th({ label, tooltip, sortKey, current, dir, onSort, className = '', align = 'right' }: ThProps) {
  // ordenação por botão (teclado) e explicação no ⓘ, não no `title`.
  const isActive = current === sortKey
  return (
    <th scope="col" aria-sort={isActive ? (dir === 'asc' ? 'ascending' : 'descending') : 'none'}
      className={`px-3 py-2 font-medium whitespace-nowrap transition-colors ${align === 'left' ? 'text-left' : 'text-right'} ${isActive ? 'bg-primario-200' : 'bg-gray-50'} ${className}`}>
      <span className="inline-flex items-baseline gap-0.5">
        <button type="button" onClick={() => onSort(sortKey)} className="hover:text-gray-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario-500">
          {label}<SortIcon active={isActive} dir={dir} />
        </button>
        <Dica texto={tooltip} rotulo={label} />
      </span>
    </th>
  )
}

// ── Component ────────────────────────────────────────────────────────────────

interface Props {
  ixps: ExternalIXPIndexEntry[]
}

export function ExternalIXPTable({ ixps }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('br_member_count')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir(key === 'name' || key === 'region' || key === 'location' ? 'asc' : 'desc')
    }
  }

  const sorted = useMemo(() => {
    return [...ixps].sort((a, b) => {
      const va = sortValue(a, sortKey)
      const vb = sortValue(b, sortKey)
      let cmp = 0
      if (typeof va === 'string' && typeof vb === 'string') {
        cmp = va.localeCompare(vb, 'pt-BR')
      } else {
        cmp = (va as number) - (vb as number)
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [ixps, sortKey, sortDir])

  const thProps = { current: sortKey, dir: sortDir, onSort: handleSort }

  return (
    <div className="max-h-[75vh] overflow-auto border border-gray-200 rounded-lg">
      <table className="w-full text-sm min-w-[640px]">
        <thead className="text-xs text-gray-600 sticky top-0 z-20 shadow-sm">
          <tr>
            <th colSpan={3} scope="colgroup" className="px-3 py-1.5 text-left font-semibold text-gray-500 bg-gray-50 border-b border-gray-200">
              PTT
            </th>
            <th colSpan={3} scope="colgroup" className="px-3 py-1.5 text-center font-semibold text-gray-500 border-l border-b border-gray-200 bg-gray-50">
              Redes (PeeringDB)
            </th>
          </tr>
          <tr className="border-b border-gray-200">
            <Th label="PTT" tooltip="Nome do PTT (IXP)" sortKey="name" {...thProps} align="left" className="text-left" />
            <Th label="Localização" tooltip="Cidade e país" sortKey="location" {...thProps} align="left" className="text-left" />
            <Th label="Região" tooltip="Região geográfica" sortKey="region" {...thProps} align="left" className="text-left" />
            <Th label="Total" tooltip="Redes (ASNs distintos) declaradas no PeeringDB; uma rede com duas portas conta uma vez (snapshots anteriores a 2026-11 contavam portas)" sortKey="member_count" {...thProps} className="border-l border-gray-200" />
            <Th label="Do Brasil" tooltip="Redes com ASN delegado pela LACNIC ao Brasil" sortKey="br_member_count" {...thProps} />
            <Th label="% do Brasil" tooltip="Redes brasileiras ÷ redes" sortKey="pct_br" {...thProps} />
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {sorted.map((ixp, i) => {
            const pctBr = ixp.member_count > 0
              ? ((ixp.br_member_count / ixp.member_count) * 100).toFixed(1) + '%'
              : '—'
            const flag = FLAG[ixp.country] ?? ''
            const region = countryToRegion(ixp.country)
            const regionStyle = REGION_STYLE[region] ?? 'text-gray-500 bg-gray-50'
            return (
              <tr key={ixp.code} className={`hover:bg-tecnico-50 ${i % 2 === 1 ? 'bg-gray-50/40' : ''}`}>
                <td className="px-3 py-2 whitespace-nowrap">
                  <Link to={`/ixp-externo/${ixp.code}`} className="text-primario-600 hover:underline font-medium">
                    {ixp.name}
                  </Link>
                </td>
                <td className="px-3 py-2 text-gray-500 whitespace-nowrap">
                  {flag} {ixp.city}{ixp.city && ixp.country ? ', ' : ''}{ixp.country}
                </td>
                <td className="px-3 py-2">
                  <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${regionStyle}`}>
                    {region}
                  </span>
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-gray-700 border-l border-gray-100">
                  {ixp.member_count.toLocaleString('pt-BR')}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-ok-700 font-medium">
                  {ixp.br_member_count.toLocaleString('pt-BR')}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-gray-500">
                  {pctBr}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
