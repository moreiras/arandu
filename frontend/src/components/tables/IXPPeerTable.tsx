import { useState, useMemo } from 'react'
import { Link } from '../layout/LinkDatado'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  type SortingState,
  type ColumnDef,
  flexRender,
} from '@tanstack/react-table'
import type { IXPPeerStats } from '../../types/api'
import type { IXPAssinantes, IXPAssinantesAsn } from '../../services/api'
import { OutorgaBadges } from '../OutorgaBadge'
import { Dica } from '../ui/Dica'
import type { PeeringDbPeers } from '../../types/api'

interface PeerRow {
  asn: number
  isStub: boolean
  isBr: boolean
  stats: IXPPeerStats
  empresa: IXPAssinantesAsn | null
  assinantesTotal: number | null
}

interface IXPPeerTableProps {
  /** Lista de ASNs em peering direto */
  asnDirect: number[]
  /** Subconjunto: stubs */
  asnStub: number[]
  /** Subconjunto: ASNs BR diretos */
  brAsnsDirect: number[]
  /** Mapa ASN → stats por peer (do endpoint /peers) */
  peerStats: Record<string, IXPPeerStats> | null
  afi: 'v4' | 'v6'
  /** ASN selecionado no Hilbert (highlight) */
  selectedPeer?: number | null
  onSelectPeer?: (asn: number | null) => void
  /** Empresa/outorgas/APNIC/SICI por ASN (endpoint /assinantes); undefined = carregando */
  assinantes?: IXPAssinantes | null
  /** Portas declaradas e instalações inferidas do PeeringDB. */
  peeringdb?: PeeringDbPeers
}

/** 100000 → "100G", 10000 → "10G", 1000 → "1G", 100 → "100M"; repetidas viram "2× 10G". 0 = não informada. */
export function fmtPortas(v: number[] | undefined): string | null {
  if (!v?.length) return null
  const rot = (m: number) => (m <= 0 ? 'não informada' : m >= 1000 ? `${(m / 1000).toLocaleString('pt-BR')}G` : `${m}M`)
  const cont = new Map<string, number>()
  for (const m of v) cont.set(rot(m), (cont.get(rot(m)) ?? 0) + 1)
  return [...cont].map(([r, q]) => (q > 1 ? `${q}× ${r}` : r)).join(' + ')
}

const PAGE_SIZE = 50

function n(v: number) {
  return v.toLocaleString('pt-BR')
}

function fmtCnpj(c: string): string {
  const d = (c ?? '').replace(/\D/g, '')
  if (d.length !== 14) return c
  return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8,12)}-${d.slice(12)}`
}

/** Número ou traço — null/0 viram "—" para não confundir "sem dado" com zero. */
function nOrDash(v: number | null | undefined) {
  return v ? n(v) : <span className="text-gray-300">—</span>
}

export function IXPPeerTable({
  asnDirect,
  asnStub,
  brAsnsDirect,
  peerStats,
  afi,
  selectedPeer,
  onSelectPeer,
  assinantes,
  peeringdb,
}: IXPPeerTableProps) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'total_prefixes', desc: true },
  ])

  const stubSet = useMemo(() => new Set(asnStub), [asnStub])
  const brSet = useMemo(() => new Set(brAsnsDirect), [brAsnsDirect])

  const rows: PeerRow[] = useMemo(() => {
    return asnDirect.map((asn) => ({
      asn,
      isStub: stubSet.has(asn),
      isBr: brSet.has(asn),
      stats: peerStats?.[String(asn)] ?? {
        total_prefixes: 0,
        own_prefixes: 0,
        third_prefixes: 0,
        origin_asns: 0,
        own_space_24: 0,
        third_space_24: 0,
      },
      empresa: assinantes?.asns[String(asn)] ?? null,
      assinantesTotal: assinantes ? (assinantes.peers?.[afi]?.[String(asn)] ?? 0) : null,
    }))
  }, [asnDirect, stubSet, brSet, peerStats, assinantes, afi])

  const spaceLabel = afi === 'v4' ? '/24s' : '/48s'

  const columns: ColumnDef<PeerRow>[] = [
    {
      id: 'asn',
      accessorFn: (r) => r.asn,
      header: 'ASN',
      cell: ({ row }) => (
        <Link
          to={`/asn/${row.original.asn}`}
          className="font-mono text-primario-600 hover:underline text-xs"
        >
          AS{row.original.asn}
        </Link>
      ),
      size: 90,
    },
    {
      id: 'flags',
      header: '',
      cell: ({ row }) => (
        <div className="flex gap-1">
          {row.original.isBr && (
            <span className="text-xs bg-ok-100 text-ok-700 rounded px-1 py-0.5">BR</span>
          )}
          {row.original.isStub && (
            <span className="text-xs bg-gray-100 text-gray-500 rounded px-1 py-0.5">stub</span>
          )}
        </div>
      ),
      size: 70,
      enableSorting: false,
    },
    {
      id: 'empresa',
      accessorFn: (r) => r.empresa?.empresa ?? '',
      header: 'Empresa',
      cell: ({ row }) => {
        const e = row.original.empresa
        if (!e?.cnpj) return <span className="text-gray-300 text-xs">—</span>
        return (
          <div className="min-w-0">
            <Link
              to={`/operadora/${e.cnpj}`}
              className="text-xs text-gray-800 hover:underline truncate block max-w-[220px]"
              title={e.empresa ?? undefined}
            >
              {e.empresa}
            </Link>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="font-mono text-xs text-gray-400">{fmtCnpj(e.cnpj)}</span>
              <OutorgaBadges flags={e} />
            </div>
          </div>
        )
      },
      sortingFn: 'text',
      size: 260,
    },
    {
      id: 'usuarios_apnic',
      accessorFn: (r) => r.empresa?.usuarios_apnic ?? 0,
      header: 'Usuários (APNIC)',
      cell: ({ row }) => (
        <span className="tabular-nums text-tecnico-700">{nOrDash(row.original.empresa?.usuarios_apnic)}</span>
      ),
      size: 120,
    },
    {
      id: 'assinantes_diretos',
      accessorFn: (r) => r.empresa?.assinantes_diretos ?? 0,
      header: () => (
        <span title="Acessos SCM (B2C + B2B) informados ao SICI pelo CNPJ deste AS">
          Assinantes (diretos)
        </span>
      ),
      cell: ({ row }) => (
        <span className="tabular-nums">{nOrDash(row.original.empresa?.assinantes_diretos)}</span>
      ),
      size: 130,
    },
    {
      id: 'assinantes_total',
      accessorFn: (r) => r.assinantesTotal ?? 0,
      header: () => (
        <span title="Acessos SCM (B2C + B2B) informados ao SICI pelos CNPJs deste AS e de todos os ASes nos AS-paths que ele anuncia no IXP (clientes) — deduplicado por CNPJ">
          Assinantes (total, c/ clientes)
        </span>
      ),
      cell: ({ row }) => (
        <span className="tabular-nums font-medium">{nOrDash(row.original.assinantesTotal)}</span>
      ),
      size: 150,
    },
    {
      id: 'porta_pdb',
      accessorFn: (r) => (peeringdb?.portas[String(r.asn)] ?? []).reduce((s, v) => s + v, 0),
      header: 'Porta (PeeringDB)',
      meta: { dica: 'Velocidade de porta que o próprio participante declarou no PeeringDB para este PTT (netixlan). Autodeclarado: pode estar desatualizado; não é a porta contratada no IX.br nem tráfego.' },
      cell: ({ row }) => {
        const f = fmtPortas(peeringdb?.portas[String(row.original.asn)])
        return f ? <span className="whitespace-nowrap">{f}</span> : <span className="text-gray-300">—</span>
      },
      size: 120,
    },
    {
      id: 'instalacao_pdb',
      accessorFn: (r) => peeringdb?.instalacoes[String(r.asn)]?.[0]?.nome ?? '',
      header: 'Instalação (inferida)',
      meta: { dica: 'Inferida do PeeringDB: as instalações (datacenters) onde a rede declara presença e que também abrigam este PTT. O PeeringDB não diz em qual delas fica cada porta.' },
      cell: ({ row }) => {
        const l = peeringdb?.instalacoes[String(row.original.asn)]
        if (!l?.length) return <span className="text-gray-300">—</span>
        return (
          <span className="block max-w-[14rem] truncate" title={l.map((x) => x.nome).join('; ')}>
            <Link to={`/instalacao/${l[0].id}`} className="text-primario-600 hover:underline">{l[0].nome}</Link>
            {l.length > 1 && <span className="text-gray-500"> e mais {l.length - 1}</span>}
          </span>
        )
      },
      size: 180,
    },
    {
      id: 'total_prefixes',
      accessorFn: (r) => r.stats.total_prefixes,
      header: 'Total prefixos',
      cell: ({ row }) => (
        <span className="tabular-nums">
          {n(row.original.stats.total_prefixes)}
        </span>
      ),
      size: 110,
    },
    {
      id: 'total_space',
      accessorFn: (r) => r.stats.own_space_24 + r.stats.third_space_24,
      header: spaceLabel,
      cell: ({ row }) => (
        <span className="tabular-nums text-gray-600">
          {n(row.original.stats.own_space_24 + row.original.stats.third_space_24)}
        </span>
      ),
      size: 90,
    },
    {
      id: 'own_prefixes',
      accessorFn: (r) => r.stats.own_prefixes,
      header: 'Próprios',
      cell: ({ row }) => (
        <span className="tabular-nums text-primario-700">
          {n(row.original.stats.own_prefixes)}
          {row.original.stats.own_space_24 > 0 && (
            <span className="text-gray-400 ml-1 text-xs">
              ({n(row.original.stats.own_space_24)} {spaceLabel})
            </span>
          )}
        </span>
      ),
      size: 160,
    },
    {
      id: 'third_prefixes',
      accessorFn: (r) => r.stats.third_prefixes,
      header: 'Terceiros',
      cell: ({ row }) => (
        <span className="tabular-nums text-alerta-600">
          {n(row.original.stats.third_prefixes)}
          {row.original.stats.third_space_24 > 0 && (
            <span className="text-gray-400 ml-1 text-xs">
              ({n(row.original.stats.third_space_24)} {spaceLabel})
            </span>
          )}
        </span>
      ),
      size: 160,
    },
    {
      id: 'origin_asns',
      accessorFn: (r) => r.stats.origin_asns,
      header: 'ASNs originadores',
      cell: ({ row }) => (
        <span className="tabular-nums">{n(row.original.stats.origin_asns)}</span>
      ),
      size: 130,
    },
  ]

  if (onSelectPeer) {
    columns.unshift({
      id: 'select',
      header: '',
      cell: ({ row }) => {
        const asn = row.original.asn
        const active = selectedPeer === asn
        return (
          <button
            onClick={() => onSelectPeer(active ? null : asn)}
            className={`w-4 h-4 rounded-full border-2 transition-colors ${
              active
                ? 'bg-primario-600 border-primario-600'
                : 'border-gray-300 hover:border-primario-400'
            }`}
            title={active ? 'Limpar seleção' : `Ver prefixos do AS${asn} no Hilbert`}
          />
        )
      },
      size: 36,
      enableSorting: false,
    })
  }

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    // Paginação no cliente: o IX.br SP tem ~1,8 mil peers por AFI e renderizar todos daria 229 mil px.
    getPaginationRowModel: getPaginationRowModel(),
    autoResetPageIndex: true,
    initialState: { pagination: { pageIndex: 0, pageSize: PAGE_SIZE } },
  })

  const loading = peerStats === null

  return (
    // a caixa rola por dentro (até 75% da tela) para o cabeçalho ficar fixo; ordenação por botão; ⓘ por coluna (`meta.dica`).
    <div className="max-h-[75vh] overflow-auto rounded border border-gray-200">
      <table className="w-full text-sm" aria-label="Participantes do PTT">
        <thead className="bg-gray-50 text-xs text-gray-600 sticky top-0 z-10 shadow-[0_1px_0_0_#e5e7eb]">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((h) => {
                const sentido = h.column.getIsSorted()
                const dica = (h.column.columnDef.meta as { dica?: string } | undefined)?.dica
                const rot = flexRender(h.column.columnDef.header, h.getContext())
                return (
                  <th key={h.id} scope="col" className="px-3 py-2 text-left font-medium" style={{ width: h.getSize() }}
                    aria-sort={sentido === 'asc' ? 'ascending' : sentido === 'desc' ? 'descending' : 'none'}>
                    <span className="inline-flex items-baseline gap-0.5">
                      {h.column.getCanSort() ? (
                        <button type="button" onClick={h.column.getToggleSortingHandler()} className="text-left hover:text-gray-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario-500">
                          {rot}{sentido === 'asc' ? ' ↑' : sentido === 'desc' ? ' ↓' : ''}
                        </button>
                      ) : rot}
                      {dica && <Dica texto={dica} rotulo={typeof h.column.columnDef.header === 'string' ? h.column.columnDef.header : h.column.id} />}
                    </span>
                  </th>
                )
              })}
            </tr>
          ))}
        </thead>
        <tbody className="divide-y divide-gray-100">
          {loading ? (
            <tr>
              <td colSpan={columns.length} className="px-3 py-6 text-center text-gray-400 text-xs">
                Carregando estatísticas por peer…
              </td>
            </tr>
          ) : rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-3 py-6 text-center text-gray-400 text-xs">
                Nenhum peer encontrado.
              </td>
            </tr>
          ) : (
            table.getRowModel().rows.map((row) => {
              const active = selectedPeer === row.original.asn
              return (
                <tr
                  key={row.id}
                  className={`hover:bg-gray-50 ${active ? 'bg-primario-50' : ''}`}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-3 py-1.5">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              )
            })
          )}
        </tbody>
      </table>
      {!loading && rows.length > PAGE_SIZE && (
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-gray-100 bg-gray-50 px-3 py-2 text-xs text-gray-600">
          <span>
            {n(table.getState().pagination.pageIndex * PAGE_SIZE + 1)}–
            {n(Math.min((table.getState().pagination.pageIndex + 1) * PAGE_SIZE, rows.length))} de {n(rows.length)}
          </span>
          <span className="flex items-center gap-2">
            <button
              type="button"
              className="rounded border border-gray-300 px-2 py-1 disabled:opacity-40"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
            >
              ← Anterior
            </button>
            <span>
              página {table.getState().pagination.pageIndex + 1} de {table.getPageCount()}
            </span>
            <button
              type="button"
              className="rounded border border-gray-300 px-2 py-1 disabled:opacity-40"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
            >
              Próxima →
            </button>
          </span>
        </div>
      )}
    </div>
  )
}
