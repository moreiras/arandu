import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchEconomicGroups } from '../../services/api'
import type { EconomicGroup, EconomicGroupsResponse } from '../../types/api'

const SECTION_COLOR = '#0e7490'

function fmtN(n: number | null | undefined): string {
  return n == null ? '—' : n.toLocaleString('pt-BR')
}
function fmtPct(n: number | null | undefined): string {
  return n == null ? '—' : `${n.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`
}
function fmtCnpj(c: string): string {
  const d = (c ?? '').replace(/\D/g, '')
  if (d.length !== 14) return c
  return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8,12)}-${d.slice(12)}`
}

function YesNo({ v }: { v: boolean | null }) {
  if (v == null) return <span className="text-gray-300">—</span>
  return v
    ? <span className="inline-block px-1.5 py-0.5 rounded text-xs font-semibold bg-ok-100 text-ok-700">sim</span>
    : <span className="inline-block px-1.5 py-0.5 rounded text-xs bg-gray-100 text-gray-400">não</span>
}

function GroupRow({ group, rank }: { group: EconomicGroup; rank: number }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <tr
        onClick={() => setOpen(o => !o)}
        className="hover:bg-tecnico-100 transition-colors cursor-pointer border-t border-gray-100"
      >
        <td className="px-3 py-1.5 text-gray-400 tabular-nums w-8 text-right">{rank}</td>
        <td className="px-3 py-1.5">
          <div className="flex items-center gap-1.5">
            <span className={`text-gray-400 transition-transform ${open ? 'rotate-90' : ''}`}>▸</span>
            <div className="min-w-0">
              <div className="font-medium text-gray-900 truncate">{group.razao_social || '—'}</div>
              <div className="text-xs text-gray-400 font-mono">
                <Link to={`/operadora/${group.cnpj}`} className="hover:text-primario-600 hover:underline"
                      onClick={e => e.stopPropagation()}>
                  {fmtCnpj(group.cnpj)}
                </Link>
                {group.uf ? ` · ${group.uf}` : ''}
              </div>
            </div>
          </div>
        </td>
        <td className="px-3 py-1.5 text-right tabular-nums font-semibold" style={{ color: SECTION_COLOR }}>{group.asn_count}</td>
        <td className="px-3 py-1.5 text-right tabular-nums text-gray-700">{fmtN(group.total_apnic_users)}</td>
        <td className="px-3 py-1.5 text-right tabular-nums text-gray-600">{fmtN(group.total_v6_blocks)}</td>
        <td className="px-3 py-1.5 text-right tabular-nums text-gray-600">{fmtN(group.total_v4_blocks)}</td>
      </tr>
      {open && (
        <tr className="bg-gray-50/60">
          <td />
          <td colSpan={5} className="px-3 py-2">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-400">
                  <th className="text-left font-medium py-1 pr-2">ASN</th>
                  <th className="text-left font-medium py-1 pr-2">Nome</th>
                  <th className="text-right font-medium py-1 px-2">Usuários</th>
                  <th className="text-right font-medium py-1 px-2">%IPv6</th>
                  <th className="text-right font-medium py-1 px-2">Blocos v6</th>
                  <th className="text-right font-medium py-1 px-2">Blocos v4</th>
                  <th className="text-center font-medium py-1 px-2">RPKI</th>
                  <th className="text-center font-medium py-1 px-2">ASPA</th>
                  <th className="text-right font-medium py-1 pl-2">IXes</th>
                </tr>
              </thead>
              <tbody>
                {group.asns.map(a => (
                  <tr key={a.asn} className="border-t border-gray-100">
                    <td className="py-1 pr-2 font-mono whitespace-nowrap">
                      <Link to={`/asn/${a.asn}`} className="text-primario-600 hover:underline" onClick={e => e.stopPropagation()}>
                        AS{a.asn}
                      </Link>
                    </td>
                    <td className="py-1 pr-2 text-gray-700 truncate max-w-[260px]" title={a.name}>{a.name || '—'}</td>
                    <td className="py-1 px-2 text-right tabular-nums text-gray-700">{fmtN(a.apnic_users)}</td>
                    <td className="py-1 px-2 text-right tabular-nums text-gray-600">{fmtPct(a.pct_v6)}</td>
                    <td className="py-1 px-2 text-right tabular-nums text-gray-600">{fmtN(a.rir_prefixes_v6_count)}</td>
                    <td className="py-1 px-2 text-right tabular-nums text-gray-600">{fmtN(a.rir_prefixes_v4_count)}</td>
                    <td className="py-1 px-2 text-center"><YesNo v={a.has_rpki} /></td>
                    <td className="py-1 px-2 text-center"><YesNo v={a.has_aspa} /></td>
                    <td className="py-1 pl-2 text-right tabular-nums text-gray-600">{a.ixps_direct_count || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </td>
        </tr>
      )}
    </>
  )
}

export function EconomicGroupsTable({ date }: { date?: string }) {
  const { data, isError } = useQuery<EconomicGroupsResponse>({
    queryKey: ['economic-groups', date],
    queryFn: () => fetchEconomicGroups(date, 50),
    staleTime: 10 * 60 * 1000,
  })

  if (isError || !data || data.groups.length === 0) return null

  return (
    <section className="space-y-3">
      <h2 className="text-sm font-semibold uppercase tracking-widest border-t border-gray-100 pt-8" style={{ color: SECTION_COLOR }}>
        Entidades com múltiplos ASN
      </h2>
      <p className="text-xs text-gray-500">
        Organizações (CNPJ do Registro.br) que operam 2 ou mais ASNs — as 50 maiores por número de ASNs.
        Clique numa linha para ver os ASNs do grupo.
      </p>
      <div className="overflow-x-auto lg:overflow-x-clip rounded-lg border border-gray-200 bg-white">
        <table className="w-full table-fixed text-xs min-w-[680px]">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-gray-500">
              <th className="px-3 py-1.5 text-right font-medium w-8">#</th>
              <th className="px-3 py-1.5 text-left font-medium">Grupo (CNPJ)</th>
              <th className="px-3 py-1.5 text-right font-medium w-20">ASNs</th>
              <th className="px-3 py-1.5 text-right font-medium w-28">Usuários</th>
              <th className="px-3 py-1.5 text-right font-medium w-24">Blocos v6</th>
              <th className="px-3 py-1.5 text-right font-medium w-24">Blocos v4</th>
            </tr>
          </thead>
          <tbody>
            {data.groups.map((g, i) => <GroupRow key={g.cnpj} group={g} rank={i + 1} />)}
          </tbody>
        </table>
      </div>
    </section>
  )
}
