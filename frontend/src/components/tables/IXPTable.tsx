import { useState, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Link } from '../layout/LinkDatado'
import { BarraDeAbas } from '../../features/entidade/EntityPage'
import { coletaDaFamilia, type IXPIndexEntry, type IXPIndexAfi } from '../../types/api'
import { Dica } from '../ui/Dica'

interface IXPTableProps {
  ixps: IXPIndexEntry[]
  totalBrASNs?: number
  totalGlobalASNs?: number
  /** Usuários finais BR estimados visíveis por IXP, por código. */
  estUsers?: Record<string, number>
}

type SortKey =
  | 'name' | 'uf' | 'region' | 'code'
  | 'asn_members' | 'asn_direct' | 'asn_dif' | 'asn_origin' | 'asn_br_coverage' | 'asn_ft_coverage' | 'asn_est_users'
  | 'v6_prefixes' | 'v6_space' | 'v6_ft_coverage' | 'v6_reg_coverage'
  | 'v4_prefixes' | 'v4_space' | 'v4_ft_coverage' | 'v4_reg_coverage'

// Brazilian macroregion by UF
const UF_REGION: Record<string, string> = {
  AM: 'Norte', PA: 'Norte', AC: 'Norte', RO: 'Norte', RR: 'Norte', TO: 'Norte', AP: 'Norte',
  BA: 'Nordeste', SE: 'Nordeste', AL: 'Nordeste', PE: 'Nordeste', PB: 'Nordeste',
  RN: 'Nordeste', CE: 'Nordeste', PI: 'Nordeste', MA: 'Nordeste',
  MT: 'Centro-Oeste', MS: 'Centro-Oeste', GO: 'Centro-Oeste', DF: 'Centro-Oeste',
  SP: 'Sudeste', RJ: 'Sudeste', MG: 'Sudeste', ES: 'Sudeste',
  PR: 'Sul', SC: 'Sul', RS: 'Sul',
}

const REGION_STYLE: Record<string, string> = {
  Norte:         'text-mercado-700 bg-mercado-50',
  Nordeste:      'text-alerta-700 bg-alerta-50',
  'Centro-Oeste':'text-aviso-700 bg-aviso-50',
  Sudeste:       'text-primario-700 bg-primario-50',
  Sul:           'text-v6-700 bg-v6-50',
}

type SortDir = 'asc' | 'desc'

/**
 * Grupos de colunas: com as 19 colunas juntas a tabela passa da largura da tela e, de `lg` para cima (sem rolagem
 * lateral, por causa do cabeçalho fixo), as últimas colunas ficam inacessíveis. As colunas do PTT ficam sempre; o resto vem por grupo,
 * IPv6 antes de IPv4. Estado em `?colunas=`.
 */
const GRUPOS = [
  { id: 'ases', rotulo: 'Sistemas autônomos', descricao: 'Participantes, route server, originadores, coberturas e usuários estimados' },
  { id: 'ipv6', rotulo: 'IPv6', descricao: 'Prefixos, espaço e coberturas em IPv6' },
  { id: 'ipv4', rotulo: 'IPv4', descricao: 'Prefixos, espaço e coberturas em IPv4' },
] as const
type Grupo = (typeof GRUPOS)[number]['id']

function getAfi(entry: IXPIndexEntry, afi: 'v4' | 'v6'): IXPIndexAfi | null {
  const a = entry[afi]
  if (!a || !('total_routes' in a)) return null
  return a as IXPIndexAfi
}

/** Família com dado medido: sem bruto ou com a tabela vazia do looking glass, as medidas da família são "n/d", não zero. */
function medida(entry: IXPIndexEntry, afi: 'v4' | 'v6'): IXPIndexAfi | null {
  const a = getAfi(entry, afi)
  return a && coletaDaFamilia(a) === 'ok' ? a : null
}

const DICA_VAZIA = 'Coleta feita, mas o looking glass respondeu com a tabela vazia nesta família: zero rotas coletadas, sem medida de cobertura.'

function CelulaVazia() {
  return <span className="text-gray-500" title={DICA_VAZIA}>zero rotas<span className="sr-only">: {DICA_VAZIA}</span></span>
}

function num(v: number | undefined | null, decimals = 0): string {
  if (v == null) return '—'
  return v.toLocaleString('pt-BR', { maximumFractionDigits: decimals })
}

function pct(v: number | undefined | null, decimals = 1): string {
  if (v == null) return '—'
  return `${v.toFixed(decimals)}%`
}

function sortValue(
  ixp: IXPIndexEntry,
  key: SortKey,
  totalBrASNs?: number,
  totalGlobalASNs?: number,
  estUsers?: Record<string, number>,
): number | string | null {
  const v4 = medida(ixp, 'v4')
  const v6 = medida(ixp, 'v6')
  switch (key) {
    case 'name': return ixp.name
    case 'uf': return ixp.uf
    case 'region': return UF_REGION[ixp.uf.toUpperCase()] ?? 'ZZ'
    case 'code': return ixp.code
    case 'asn_members': return ixp.ixbr_members_count ?? 0
    case 'asn_direct': return ixp.asn_direct_union_count ?? 0
    case 'asn_dif': return foraDoRouteServer(ixp)?.n ?? 0
    case 'asn_origin': return ixp.asn_origin_union_count ?? 0
    case 'asn_br_coverage':
      return totalBrASNs
        ? (ixp.br_asns_origin_union_count ?? 0) / totalBrASNs
        : (ixp.br_asns_origin_union_count ?? 0)
    case 'asn_ft_coverage':
      return totalGlobalASNs
        ? (ixp.asn_origin_union_count ?? 0) / totalGlobalASNs
        : (ixp.asn_origin_union_count ?? 0)
    case 'asn_est_users': return estUsers?.[ixp.code] ?? 0
    case 'v6_prefixes': return v6?.unique_prefixes ?? null
    case 'v6_space': return v6?.ixp_space_units ?? null
    case 'v6_ft_coverage': return v6?.ixp_vs_fulltable_space_pct ?? null
    case 'v6_reg_coverage': return v6?.br_prefix_coverage_pct ?? null
    case 'v4_prefixes': return v4?.unique_prefixes ?? null
    case 'v4_space': return v4?.ixp_space_units ?? null
    case 'v4_ft_coverage': return v4?.ixp_vs_fulltable_space_pct ?? null
    case 'v4_reg_coverage': return v4?.br_prefix_coverage_pct ?? null
  }
}

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <span className="text-gray-300 ml-0.5">↕</span>
  return <span className="text-gray-700 ml-0.5">{dir === 'asc' ? '↑' : '↓'}</span>
}

function Th({
  label,
  tooltip,
  sortKey,
  current,
  dir,
  onSort,
  className = '',
  align = 'right',
}: {
  label: string
  tooltip: string
  sortKey: SortKey
  current: SortKey
  dir: SortDir
  onSort: (k: SortKey) => void
  className?: string
  align?: 'left' | 'right'
}) {
  // rótulo por extenso (sem siglas), explicação no ⓘ e ordenação por botão (teclado; NBR 17225 5.1.13).
  const isActive = current === sortKey
  return (
    <th
      scope="col"
      aria-sort={isActive ? (dir === 'asc' ? 'ascending' : 'descending') : 'none'}
      className={`px-2 py-1.5 align-bottom font-medium transition-colors ${align === 'left' ? 'text-left' : 'text-right'} ${isActive ? 'bg-primario-200' : 'bg-gray-50'} ${className}`}
    >
      <span className={`inline-flex items-end gap-0.5 ${align === 'left' ? '' : 'justify-end'}`}>
        <button type="button" onClick={() => onSort(sortKey)}
          className={`max-w-[7.5rem] leading-tight hover:text-gray-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario-500 ${align === 'left' ? 'text-left' : 'text-right'}`}>
          {label}<SortIcon active={isActive} dir={dir} />
        </button>
        <Dica texto={tooltip} rotulo={label} />
      </span>
    </th>
  )
}

/**
 * Participantes do cadastro sem sessão com o route server (IXPS-E3): número absoluto e % dos participantes, nunca dos diretos.
 * `null` sem as duas contagens ou sem participantes.
 */
export function foraDoRouteServer(ixp: Pick<IXPIndexEntry, 'ixbr_members_count' | 'asn_direct_union_count'>): { n: number; pct: number } | null {
  const membros = ixp.ixbr_members_count
  const diretos = ixp.asn_direct_union_count
  if (membros == null || diretos == null || membros <= 0) return null
  const n = Math.max(0, membros - diretos)
  return { n, pct: (n / membros) * 100 }
}

export function IXPTable({ ixps, totalBrASNs, totalGlobalASNs, estUsers }: IXPTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('name')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [params, setParams] = useSearchParams()
  const grupo: Grupo = GRUPOS.find((g) => g.id === params.get('colunas'))?.id ?? 'ases'
  const escolherGrupo = (id: string) => setParams((ant) => { const n = new URLSearchParams(ant); if (id === 'ases') n.delete('colunas'); else n.set('colunas', id); return n }, { replace: true })

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const sorted = useMemo(() => {
    return [...ixps].sort((a, b) => {
      const va = sortValue(a, sortKey, totalBrASNs, totalGlobalASNs, estUsers)
      const vb = sortValue(b, sortKey, totalBrASNs, totalGlobalASNs, estUsers)
      if (va == null || vb == null) return va == null ? (vb == null ? 0 : 1) : -1      // n/d no fim, em qualquer direção
      let cmp = 0
      if (typeof va === 'string' && typeof vb === 'string') {
        cmp = va.localeCompare(vb, 'pt-BR')
      } else {
        cmp = (va as number) - (vb as number)
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [ixps, sortKey, sortDir, totalBrASNs, totalGlobalASNs, estUsers])

  // Top 5 IXPs por DIR (calculado sempre sobre os dados originais, independente da ordenação)
  const top5DirCodes = useMemo(() => {
    const withDir = [...ixps].sort(
      (a, b) => (b.asn_direct_union_count ?? 0) - (a.asn_direct_union_count ?? 0)
    )
    return new Set(withDir.slice(0, 5).map((i) => i.code))
  }, [ixps])

  const thProps = { current: sortKey, dir: sortDir, onSort: handleSort }

  // Retorna classe de destaque da coluna ativa nas células de dados
  const colBg = (key: SortKey) => (sortKey === key ? 'bg-primario-100' : '')

  return (
    <div className="space-y-2">
    <BarraDeAbas abas={GRUPOS} ativa={grupo} aoEscolher={escolherGrupo} rotulo="Grupos de colunas da tabela de PTTs" />
    <div role="tabpanel" id={`painel-${grupo}`} aria-labelledby={`aba-${grupo}`} className="max-h-[75vh] overflow-auto rounded border border-gray-200">
      <table className={`w-full text-xs ${grupo === 'ases' ? 'min-w-[900px]' : 'min-w-[680px]'}`}>
        {/* Rolagem nos dois sentidos dentro da caixa (até 75% da tela): o <thead> fica fixo no topo dela e a coluna Cidade à esquerda. Com overflow-x-clip, de lg para cima, a caixa cortaria as colunas que não cabem. */}
        <thead className="text-xs text-gray-600 sticky top-0 z-20 shadow-sm">
          <tr className="border-b border-gray-200">
            <th colSpan={4} scope="colgroup" className="sticky left-0 z-30 px-2 py-1.5 text-left font-semibold text-gray-500 bg-gray-50">
              PTT
            </th>
            {grupo === 'ases' && <th colSpan={7} scope="colgroup" className="px-2 py-1.5 text-center font-semibold text-gray-500 border-l border-gray-200 bg-gray-50">
              Sistemas autônomos
            </th>}
            {grupo === 'ipv6' && <th colSpan={4} scope="colgroup" className="px-2 py-1.5 text-center font-semibold text-v6-700 border-l border-gray-200 bg-gray-50">
              IPv6
            </th>}
            {grupo === 'ipv4' && <th colSpan={4} scope="colgroup" className="px-2 py-1.5 text-center font-semibold text-primario-700 border-l border-gray-200 bg-gray-50">
              IPv4
            </th>}
          </tr>
          <tr className="border-b border-gray-200">
            <Th label="Cidade" tooltip="Cidade sede do PTT" sortKey="name" {...thProps} align="left" className="sticky left-0 z-30" />
            <Th label="UF" tooltip="Unidade da Federação" sortKey="uf" {...thProps} align="left" />
            <Th label="Região" tooltip="Grande região do Brasil" sortKey="region" {...thProps} align="left" />
            <Th label="Código" tooltip="Código do PTT no IX.br" sortKey="code" {...thProps} align="left" />
            {grupo === 'ases' && <>
            <Th label="Participantes" tooltip="Membros registrados neste PTT no dashboard do IX.br, incluindo os que não usam os route servers" sortKey="asn_members" {...thProps} className="border-l border-gray-200" />
            <Th label="Diretos no route server" tooltip="ASNs com sessão direta com o route server (RS) deste PTT, união de IPv6 e IPv4" sortKey="asn_direct" {...thProps} />
            <Th label="Fora do route server" tooltip="Participantes do cadastro do IX.br sem sessão com o route server nesta coleta, e a % dos participantes. Pode ser peering só bilateral ou porta sem sessão; o dado não distingue." sortKey="asn_dif" {...thProps} />
            <Th label="Originadores" tooltip="ASNs de todos os países que originam (são o último AS do AS_PATH) algum prefixo visível neste PTT, união IPv6 ∪ IPv4 (snapshots anteriores a 2026-11: o maior entre IPv6 e IPv4)" sortKey="asn_origin" {...thProps} />
            <Th label="Cobertura Registro.br" tooltip="% dos ASNs brasileiros cadastrados no Registro.br que aparecem como originadores neste PTT (união IPv6 ∪ IPv4)" sortKey="asn_br_coverage" {...thProps} />
            <Th label="Cobertura tabela global" tooltip="% dos ASNs presentes na tabela global (RouteViews) que aparecem como originadores neste PTT" sortKey="asn_ft_coverage" {...thProps} />
            <Th label="Usuários (estimados)" tooltip="Usuários finais brasileiros estimados visíveis por este PTT (IPv4): soma dos usuários do APNIC × fração do espaço IPv4 do AS visível no PTT, sobre os ASes BR originadores" sortKey="asn_est_users" {...thProps} />
            </>}
            {grupo === 'ipv6' && <>
            <Th label="Prefixos" tooltip="Prefixos IPv6 únicos visíveis neste PTT" sortKey="v6_prefixes" {...thProps} className="border-l border-gray-200" />
            <Th label="/48s" tooltip="Espaço IPv6 visível neste PTT, em blocos equivalentes a /48" sortKey="v6_space" {...thProps} />
            <Th label="Cobertura tabela global" tooltip="% do espaço IPv6 da tabela global coberto pelos prefixos deste PTT (comparação por espaço)" sortKey="v6_ft_coverage" {...thProps} />
            <Th label="Cobertura Registro.br" tooltip="% do espaço IPv6 do Registro.br para ASNs brasileiros que é visível neste PTT (comparação por espaço)" sortKey="v6_reg_coverage" {...thProps} />
            </>}
            {grupo === 'ipv4' && <>
            <Th label="Prefixos" tooltip="Prefixos IPv4 únicos visíveis neste PTT" sortKey="v4_prefixes" {...thProps} className="border-l border-gray-200" />
            <Th label="/24s" tooltip="Espaço IPv4 visível neste PTT, em blocos equivalentes a /24" sortKey="v4_space" {...thProps} />
            <Th label="Cobertura tabela global" tooltip="% do espaço IPv4 da tabela global coberto pelos prefixos deste PTT (comparação por espaço)" sortKey="v4_ft_coverage" {...thProps} />
            <Th label="Cobertura Registro.br" tooltip="% do espaço IPv4 do Registro.br para ASNs brasileiros que é visível neste PTT (comparação por espaço)" sortKey="v4_reg_coverage" {...thProps} />
            </>}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 text-sm">
          {sorted.map((ixp) => {
            const v4 = getAfi(ixp, 'v4')
            const v6 = getAfi(ixp, 'v6')
            const brCovPct =
              totalBrASNs && ixp.br_asns_origin_union_count != null
                ? (ixp.br_asns_origin_union_count / totalBrASNs) * 100
                : null
            const ftAsnCovPct =
              totalGlobalASNs && ixp.asn_origin_union_count != null
                ? (ixp.asn_origin_union_count / totalGlobalASNs) * 100
                : null

            const isTop5 = top5DirCodes.has(ixp.code)

            // Classes de fundo: top5 tem destaque âmbar permanente, hover muda em ambos os casos
            const rowBase = isTop5 ? 'bg-aviso-100' : ''
            const stickyBg = isTop5 ? 'bg-aviso-100 group-hover:bg-aviso-200' : 'bg-white group-hover:bg-tecnico-100'
            const hoverBg = isTop5 ? 'group-hover:bg-aviso-200' : 'group-hover:bg-tecnico-100'

            return (
              <tr key={ixp.code} className={`group ${rowBase}`}>
                {/* IXP group */}
                <td className={`px-2 py-2 whitespace-nowrap sticky left-0 transition-colors ${stickyBg}`}>
                  <Link to={`/ixp/${ixp.code}`} className="text-primario-600 hover:underline">
                    {ixp.name}
                  </Link>
                </td>
                <td className={`px-2 py-2 transition-colors ${hoverBg} ${colBg('uf')}`}>
                  <Link to={`/ixp/${ixp.code}`} className="text-primario-600 hover:underline">
                    {ixp.uf}
                  </Link>
                </td>
                <td className={`px-2 py-2 transition-colors ${hoverBg} ${colBg('region')}`}>
                  {(() => {
                    const r = UF_REGION[ixp.uf.toUpperCase()]
                    if (!r) return <span className="text-gray-400">—</span>
                    return (
                      <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${REGION_STYLE[r] ?? ''}`}>
                        {r}
                      </span>
                    )
                  })()}
                </td>
                <td className={`px-2 py-2 transition-colors ${hoverBg} ${colBg('code')}`}>
                  <Link to={`/ixp/${ixp.code}`} className="font-mono font-semibold text-primario-600 hover:underline">
                    {ixp.code.toUpperCase()}
                  </Link>
                </td>
                {grupo === 'ases' && <>
                {/* AS group */}
                <td className={`px-2 py-2 text-right tabular-nums text-gray-700 border-l border-gray-100 transition-colors ${hoverBg} ${colBg('asn_members')}`}>
                  {num(ixp.ixbr_members_count)}
                </td>
                <td className={`px-2 py-2 text-right tabular-nums text-gray-700 transition-colors ${hoverBg} ${colBg('asn_direct')}`}>
                  {num(ixp.asn_direct_union_count)}
                </td>
                <td className={`px-2 py-2 text-right tabular-nums text-gray-700 transition-colors ${hoverBg} ${colBg('asn_dif')}`}>
                  {(() => { const f = foraDoRouteServer(ixp); return f ? `${num(f.n)} (${pct(f.pct)})` : '—' })()}
                </td>
                <td className={`px-2 py-2 text-right tabular-nums text-gray-700 transition-colors ${hoverBg} ${colBg('asn_origin')}`}>
                  {num(ixp.asn_origin_union_count)}
                </td>
                <td className={`px-2 py-2 text-right tabular-nums text-gray-700 transition-colors ${hoverBg} ${colBg('asn_br_coverage')}`}>
                  {brCovPct != null ? pct(brCovPct) : '—'}
                </td>
                <td className={`px-2 py-2 text-right tabular-nums text-gray-700 transition-colors ${hoverBg} ${colBg('asn_ft_coverage')}`}>
                  {ftAsnCovPct != null ? pct(ftAsnCovPct) : '—'}
                </td>
                <td className={`px-2 py-2 text-right tabular-nums text-gray-700 transition-colors ${hoverBg} ${colBg('asn_est_users')}`}>
                  {estUsers?.[ixp.code] != null ? num(estUsers[ixp.code]) : '—'}
                </td>
                </>}
                {grupo === 'ipv6' && <>
                {/* IPv6 group */}
                <td className={`px-2 py-2 text-right tabular-nums text-gray-700 border-l border-gray-100 transition-colors ${hoverBg} ${colBg('v6_prefixes')}`}>
                  {v6 && coletaDaFamilia(v6) === 'vazia' ? <CelulaVazia /> : num(v6?.unique_prefixes)}
                </td>
                <td className={`px-2 py-2 text-right tabular-nums text-gray-700 transition-colors ${hoverBg} ${colBg('v6_space')}`}>
                  {v6?.ixp_space_units != null ? num(v6.ixp_space_units, 0) : '—'}
                </td>
                <td className={`px-2 py-2 text-right tabular-nums text-gray-700 transition-colors ${hoverBg} ${colBg('v6_ft_coverage')}`}>
                  {pct(v6?.ixp_vs_fulltable_space_pct)}
                </td>
                <td className={`px-2 py-2 text-right tabular-nums text-gray-700 transition-colors ${hoverBg} ${colBg('v6_reg_coverage')}`}>
                  {pct(v6?.br_prefix_coverage_pct)}
                </td>
                </>}
                {grupo === 'ipv4' && <>
                {/* IPv4 group */}
                <td className={`px-2 py-2 text-right tabular-nums text-gray-700 border-l border-gray-100 transition-colors ${hoverBg} ${colBg('v4_prefixes')}`}>
                  {v4 && coletaDaFamilia(v4) === 'vazia' ? <CelulaVazia /> : num(v4?.unique_prefixes)}
                </td>
                <td className={`px-2 py-2 text-right tabular-nums text-gray-700 transition-colors ${hoverBg} ${colBg('v4_space')}`}>
                  {v4?.ixp_space_units != null ? num(v4.ixp_space_units) : '—'}
                </td>
                <td className={`px-2 py-2 text-right tabular-nums text-gray-700 transition-colors ${hoverBg} ${colBg('v4_ft_coverage')}`}>
                  {pct(v4?.ixp_vs_fulltable_space_pct)}
                </td>
                <td className={`px-2 py-2 text-right tabular-nums text-gray-700 transition-colors ${hoverBg} ${colBg('v4_reg_coverage')}`}>
                  {pct(v4?.br_prefix_coverage_pct)}
                </td>
                </>}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
    </div>
  )
}
