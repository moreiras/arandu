import { VisaoBrasil } from '../features/cdncap/VisaoBrasil'
import { useParams, useNavigate } from 'react-router-dom'
import { Link } from '../components/layout/LinkDatado'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState, useRef, useLayoutEffect } from 'react'
import { fetchCDNPresence, fetchASNsLote, fetchIXPs } from '../services/api'
import { useActiveDate } from '../hooks/useSnapshot'
import { EstadoDados, ehErroDeAcessoOuFalha } from '../components/ui/EstadoDados'
import { cdnSlug } from '../lib/cdn'
import { CDNIXPPresenceGraph } from '../components/graphs/CDNIXPPresenceGraph'
import type { CDNAsnPresenceData } from '../components/graphs/CDNIXPPresenceGraph'
import { CDNRelationsGraph } from '../components/graphs/CDNRelationsGraph'
import type { ASNDocument, ASNPathsResponse, RoaEntry, AspaProviderEntry, AspaCustomerEntry } from '../types/api'
import { ThOrdenavel } from '../components/ui/ThOrdenavel'
import { useOrdenacao } from '../lib/ordenacao'
import { fmtN, RoaTable, AspaProvidersTable, AspaCustomersTable, Kpi, PrefixBox } from '../features/cdncap/componentes'

/** Página de uma CDN/CAP (/cdncap/:slug): a página busca os ASNs do grupo e compõe os componentes de `features/cdncap/`. */
// ─── página ─────────────────────────────────────────────────────────────────

/**
 * Presença de um grupo de ASNs (uma CDN) no IX.br por três critérios: `membro` (cadastro de participantes, a coluna `ixbr` de
 * `cdns.json`), `sessao` (algum ASN com sessão no route server, IPv6 ou IPv4) e `terceiros` (prefixos do grupo vistos no PTT sem
 * nenhum ASN do grupo com sessão: entregues por outro participante).
 */
export function presencaIxbr(docs: Array<Pick<ASNDocument, 'ixp_presence'>>, membro: string[]): { membro: number; sessao: number; terceiros: number } {
  const sessao = new Set<string>()
  const origem = new Set<string>()
  for (const d of docs) {
    for (const [code, p] of Object.entries(d.ixp_presence ?? {})) {
      if (p?.v4?.direct || p?.v6?.direct) sessao.add(code)
      if (p?.v4?.origin || p?.v6?.origin) origem.add(code)
    }
  }
  return { membro: new Set(membro).size, sessao: sessao.size, terceiros: [...origem].filter((c) => !sessao.has(c)).length }
}

export function CDNCapPage() {
  const { slug } = useParams<{ slug: string }>()
  const date = useActiveDate()
  const navigate = useNavigate()

  const { data: presence, isLoading: loadingPresence, error: erroPresence, refetch: refetchPresence } = useQuery({
    queryKey: ['cdns', date],
    queryFn: () => fetchCDNPresence(date ?? undefined),
    staleTime: Infinity, gcTime: Infinity,
  })

  const { data: ixpList } = useQuery({
    queryKey: ['ixps', date],
    queryFn: () => fetchIXPs(date ?? undefined),
    staleTime: Infinity, gcTime: Infinity,
  })
  const ixpNames = useMemo(() => {
    const m: Record<string, string> = {}
    for (const e of ixpList?.ixps ?? []) m[e.code] = e.name
    return m
  }, [ixpList])

  const row = useMemo(
    () => presence?.cdns.find((c) => cdnSlug(c.name) === slug) ?? null,
    [presence, slug],
  )
  const asns = useMemo(() => row?.asns ?? [], [row])

  // Documentos e caminhos de todos os ASNs do grupo em UMA chamada (eram 2 por ASN). Lotes de até 100.
  const loteQ = useQuery({
    queryKey: ['asns-lote-paths', asns.join(','), date],
    queryFn: async () => {
      const partes: number[][] = []
      for (let i = 0; i < asns.length; i += 100) partes.push(asns.slice(i, i + 100))
      const rs = await Promise.all(partes.map((p) => fetchASNsLote(p, { date: date ?? undefined, include: 'paths' })))
      return rs.flatMap((r) => r.items)
    },
    enabled: asns.length > 0,
    staleTime: 5 * 60 * 1000,
  })
  const itens = useMemo(() => loteQ.data ?? [], [loteQ.data])
  const docs = useMemo(() => itens as unknown as ASNDocument[], [itens])
  const loadingDocs = loteQ.isLoading
  const pathsDocs = useMemo(
    () => asns.map((asn) => itens.find((d) => d.asn === asn)?.paths as ASNPathsResponse | undefined),
    [itens, asns],
  )
  const loadingPaths = loteQ.isLoading

  // Lista de CDNAsnPresenceData (um por ASN, para CDNIXPPresenceGraph)
  const asnDataList = useMemo((): CDNAsnPresenceData[] => {
    return docs.map((d, i) => {
      const pd = pathsDocs[asns.indexOf(d.asn)]
      return {
        asn: d.asn,
        ixpPresence: d.ixp_presence,
        ixpPaths: pd?.ixp_paths ?? {},
        pathNodeMeta: pd?.path_node_meta ?? {},
        ixpMemberCodes: d.ixp_member_codes ?? [],
        rirPrefixesV4: d.rir_prefixes_v4,
        rirPrefixesV6: d.rir_prefixes_v6,
      }
    })
  }, [docs, pathsDocs, asns])

  // Três critérios de presença no IX.br, cada um no seu indicador (CDN-E1): nunca a soma de sessão e origem num número só
  const presenca = useMemo(() => presencaIxbr(docs, row?.ixbr ?? []), [docs, row])

  // Agregações sobre os ASNs do grupo
  const agg = useMemo(() => {
    const rirV4 = new Set<string>(), rirV6 = new Set<string>()
    const gV4 = new Set<string>(), gV6 = new Set<string>()
    const external = new Set<string>()
    const roaMap = new Map<string, RoaEntry>()
    const rpki: Record<string, string> = {}
    // ASPA: deduplica por provider+tal e por customer+tal
    const aspaProviderMap = new Map<string, AspaProviderEntry>()
    const aspaCustomerMap = new Map<string, AspaCustomerEntry>()
    let hasIPv6 = false, isBr = false

    for (const d of docs) {
      d.rir_prefixes_v4.forEach((p) => rirV4.add(p))
      d.rir_prefixes_v6.forEach((p) => rirV6.add(p))
      d.global_prefixes_v4.forEach((p) => gV4.add(p))
      d.global_prefixes_v6.forEach((p) => gV6.add(p))
      if (d.has_ipv6) hasIPv6 = true
      if (d.is_br) isBr = true
      for (const c of d.external_ixps ?? []) external.add(c)
      for (const r of d.roa_list ?? []) roaMap.set(`${r.prefix}|${r.maxLength}|${r.ta}`, r)
      for (const [p, status] of Object.entries(d.rpki_validation ?? {})) rpki[p] = status
      for (const a of d.aspa_providers ?? []) {
        const key = `${a.providers.sort().join(',')}|${a.tal}`
        if (!aspaProviderMap.has(key)) aspaProviderMap.set(key, a)
      }
      for (const a of d.aspa_customers ?? []) {
        const key = `${a.customer}|${a.tal}`
        if (!aspaCustomerMap.has(key)) aspaCustomerMap.set(key, a)
      }
    }

    const hasAspaData = aspaProviderMap.size > 0 || aspaCustomerMap.size > 0

    return {
      rirV4: [...rirV4].sort(), rirV6: [...rirV6].sort(),
      gV4: [...gV4].sort(), gV6: [...gV6].sort(),
      external: [...external].sort(),
      hasIPv6, isBr,
      roaList: [...roaMap.values()].sort((a, b) => a.prefix.localeCompare(b.prefix)),
      rpki,
      aspaProviders: [...aspaProviderMap.values()],
      aspaCustomers: [...aspaCustomerMap.values()].sort((a, b) => a.customer - b.customer),
      hasAspaData,
    }
  }, [docs])

  // Dimensionamento responsivo — coluna de grafo de presença
  const presenceColRef = useRef<HTMLDivElement>(null)
  const [presenceColW, setPresenceColW] = useState(560)
  useLayoutEffect(() => {
    const el = presenceColRef.current
    if (!el) return
    const ro = new ResizeObserver((entries) => {
      setPresenceColW(Math.min(Math.floor(entries[0].contentRect.width), 560))
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // Dimensionamento responsivo — coluna de grafo de relações
  const relColRef = useRef<HTMLDivElement>(null)
  const [relColW, setRelColW] = useState(480)
  useLayoutEffect(() => {
    const el = relColRef.current
    if (!el) return
    const ro = new ResizeObserver((entries) => {
      setRelColW(Math.min(Math.floor(entries[0].contentRect.width), 520))
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const pdb = useOrdenacao(useMemo(() => docs.filter((d) => d.pdb), [docs]), {
    asn: { valor: (d) => d.asn, primeiro: 'asc' },
    tipo: (d) => d.pdb!.info_type,
    trafego: (d) => d.pdb!.info_traffic,
    politica: (d) => d.pdb!.policy_general,
    irr: (d) => d.pdb!.irr_as_set,
  })

  if (loadingPresence) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 bg-gray-100 rounded w-1/3" />
        <div className="h-20 bg-gray-100 rounded" />
      </div>
    )
  }

  // Erro de acesso, de taxa ou de rede na lista de CDNs não é "CDN não encontrada".
  if (!presence && ehErroDeAcessoOuFalha(erroPresence)) {
    return <EstadoDados variante="pagina" erro={erroPresence} oQue="a lista de CDNs" aoTentarDeNovo={() => void refetchPresence()} className="mt-8 max-w-2xl mx-auto" />
  }

  if (!row) {
    return (
      <div className="text-center mt-16">
        <div className="text-3xl mb-3">404</div>
        <p className="text-gray-500 text-sm">
          CDN/CAP <code className="font-mono">{slug}</code> não encontrada no snapshot atual.
        </p>
        <Link to="/cdns" className="mt-4 inline-block text-sm text-primario-600 hover:underline">
          ← Voltar à lista de CDNs
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Cabeçalho */}
      <div>
        <div className="flex items-center gap-2 text-sm text-gray-400 mb-1">
          <Link to="/cdns" className="hover:text-gray-600">CDNs</Link>
          <span>/</span>
          <span className="text-gray-600">{row.name}</span>
        </div>
        <h1 className="text-titulo-1 text-gray-900 flex items-center gap-2 flex-wrap">
          {row.name}
          {agg.isBr && <span className="text-sm font-normal bg-ok-100 text-ok-700 rounded px-2 py-0.5">Brasil</span>}
          {agg.hasIPv6 && <span className="text-sm font-normal bg-alerta-100 text-alerta-700 rounded px-2 py-0.5">IPv6</span>}
        </h1>
        <p className="text-gray-500 text-sm mt-1">
          {asns.length} ASN{asns.length !== 1 ? 's' : ''} · Snapshot:{' '}
          <span className="font-mono">{presence?.snapshot_date}</span>
        </p>
        <div className="flex flex-wrap gap-1.5 mt-2">
          {asns.map((asn) => {
            const d = docs.find((x) => x.asn === asn)
            return (
              <Link
                key={asn}
                to={`/asn/${asn}`}
                className="inline-flex items-center gap-1.5 px-2 py-1 rounded border border-gray-200 bg-white text-xs hover:border-primario-300 hover:bg-primario-50 transition-colors"
              >
                <span className="font-mono font-semibold text-primario-700">AS{asn}</span>
                {d?.name && <span className="text-gray-500 truncate max-w-[180px]">{d.name}</span>}
              </Link>
            )
          })}
        </div>
      </div>

      {/* Hero de métricas agregadas */}
      <div className="rounded-xl border border-gray-200 bg-gradient-to-br from-gray-50 to-white px-4 py-3">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-x-3 gap-y-2 divide-x divide-gray-200">
          <Kpi value={fmtN(asns.length)} label="ASNs no grupo" color="#2563eb" />
          <Kpi value={fmtN(agg.gV6.length)} label="prefixos IPv6" sub="na tabela global" color="#8b5cf6" />
          <Kpi value={fmtN(agg.gV4.length)} label="prefixos IPv4" sub="na tabela global" color="#0891b2" />
          <Kpi value={fmtN(presenca.membro)} label="PTTs do IX.br: membro" sub="cadastro de participantes do IX.br" color="#d97706" />
          <Kpi value={fmtN(presenca.sessao)} label="PTTs do IX.br: sessão" sub="com sessão no route server (coleta)" color="#b45309" />
          <Kpi value={fmtN(presenca.terceiros)} label="PTTs do IX.br: só por terceiros" sub={`prefixos vistos sem sessão própria · + ${fmtN(agg.external.length)} IXPs externos (PeeringDB)`} color="#92400e" />
        </div>
      </div>

      {loadingDocs && (
        <div className="text-xs text-gray-400 animate-pulse">carregando dados dos ASNs do grupo…</div>
      )}

      {/* RPKI: ROAs autorizados — agregado de todos os ASNs do grupo, sempre visível */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <RoaTable
          title="RPKI: ROAs autorizados IPv6"
          accent="#dc2626"
          roaList={agg.roaList.filter((r) => r.prefix.includes(':'))}
        />
        <RoaTable
          title="RPKI: ROAs autorizados IPv4"
          accent="#0891b2"
          roaList={agg.roaList.filter((r) => !r.prefix.includes(':'))}
        />
      </div>

      {/* ASPA: provedores declarados e customers — agregado do grupo */}
      {agg.hasAspaData && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <AspaProvidersTable aspaProviders={agg.aspaProviders} />
          <AspaCustomersTable aspaCustomers={agg.aspaCustomers} />
        </div>
      )}

      {/* Prefixos agregados */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <PrefixBox title="IPv6 (tabela global)" accent="#8b5cf6" rirCount={agg.rirV6.length} prefixes={agg.gV6} rpkiValidation={agg.rpki} />
        <PrefixBox title="IPv4 (tabela global)" accent="#0891b2" rirCount={agg.rirV4.length} prefixes={agg.gV4} rpkiValidation={agg.rpki} />
      </div>

      <VisaoBrasil asns={asns} ixbr={row?.ixbr ?? []} ixpNames={ixpNames} date={date} nome={row?.name} />

      {/* Grafo de presença em IXPs — IPv6 e IPv4 lado a lado */}
      <div>
        <h2 className="text-base font-semibold text-gray-800 mb-3 flex items-center gap-2">
          Presença em IXPs do IX.br
          {loadingPaths && <span className="text-xs font-normal text-gray-400 animate-pulse">carregando caminhos…</span>}
        </h2>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
          <div ref={presenceColRef} className="overflow-hidden">
            <h3 className="text-sm font-medium text-alerta-700 mb-2">IPv6</h3>
            {asnDataList.length > 0 ? (
              <CDNIXPPresenceGraph
                afi="v6"
                asnDataList={asnDataList}
                onIxpClick={(code) => navigate(`/ixp/${code}`)}
                onBridgeClick={(asn) => navigate(`/asn/${asn}`)}
                width={presenceColW}
                height={Math.round(presenceColW * 420 / 560)}
              />
            ) : (
              loteQ.isError ? <EstadoDados erro={loteQ.error} oQue="os documentos dos ASNs" /> : <div className="text-sm text-gray-400">{loadingDocs ? 'Carregando…' : 'Sem dados.'}</div>
            )}
          </div>
          <div className="overflow-hidden">
            <h3 className="text-sm font-medium text-primario-700 mb-2">IPv4</h3>
            {asnDataList.length > 0 ? (
              <CDNIXPPresenceGraph
                afi="v4"
                asnDataList={asnDataList}
                onIxpClick={(code) => navigate(`/ixp/${code}`)}
                onBridgeClick={(asn) => navigate(`/asn/${asn}`)}
                width={presenceColW}
                height={Math.round(presenceColW * 420 / 560)}
              />
            ) : (
              loteQ.isError ? <EstadoDados erro={loteQ.error} oQue="os documentos dos ASNs" /> : <div className="text-sm text-gray-400">{loadingDocs ? 'Carregando…' : 'Sem dados.'}</div>
            )}
          </div>
        </div>
      </div>

      {/* IXPs externos — logo após presença nos IXPs */}
      {agg.external.length > 0 && (
        <div>
          <h2 className="text-base font-semibold text-gray-800 mb-2">
            Presença em outros IXPs <span className="text-sm font-normal text-gray-400">({agg.external.length})</span>
          </h2>
          <div className="flex flex-wrap gap-2">
            {agg.external.map((code) => (
              <Link
                key={code}
                to={`/ixp-externo/${code}`}
                className="px-3 py-1.5 rounded border border-primario-200 bg-primario-50 text-primario-700 text-sm hover:bg-primario-100 transition-colors"
              >
                {code}
              </Link>
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-1.5">Fonte: PeeringDB — dados autodeclarados</p>
        </div>
      )}

      {/* Relações inferidas — IPv6 e IPv4 lado a lado */}
      <div>
        <h2 className="text-base font-semibold text-gray-800 mb-1">Relações inferidas</h2>
        <p className="text-xs text-aviso-600 bg-aviso-50 border border-aviso-200 rounded px-3 py-1.5 mb-3 inline-block">
          Inferido do AS_PATH nos LGs dos IXPs e do RouteViews — não representa acordos comerciais verificados
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div ref={relColRef} className="overflow-hidden">
            <h3 className="text-sm font-medium text-alerta-700 mb-2">Relações IPv6</h3>
            {docs.length > 0 ? (
              <CDNRelationsGraph
                cdnAsns={asns}
                docs={docs}
                afi="v6"
                onAsnClick={(id) => navigate(`/asn/${id}`)}
                width={relColW}
                height={Math.round(relColW * 380 / 520)}
              />
            ) : (
              loteQ.isError ? <EstadoDados erro={loteQ.error} oQue="os documentos dos ASNs" /> : <div className="text-sm text-gray-400">{loadingDocs ? 'Carregando…' : 'Sem dados.'}</div>
            )}
          </div>
          <div className="overflow-hidden">
            <h3 className="text-sm font-medium text-primario-700 mb-2">Relações IPv4</h3>
            {docs.length > 0 ? (
              <CDNRelationsGraph
                cdnAsns={asns}
                docs={docs}
                afi="v4"
                onAsnClick={(id) => navigate(`/asn/${id}`)}
                width={relColW}
                height={Math.round(relColW * 380 / 520)}
              />
            ) : (
              loteQ.isError ? <EstadoDados erro={loteQ.error} oQue="os documentos dos ASNs" /> : <div className="text-sm text-gray-400">{loadingDocs ? 'Carregando…' : 'Sem dados.'}</div>
            )}
          </div>
        </div>
      </div>

      {/* PeeringDB por ASN */}
      {docs.some((d) => d.pdb) && (
        <div>
          <h2 className="text-base font-semibold text-gray-800 mb-2">PeeringDB</h2>
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-gray-400 uppercase bg-gray-50">
                <tr>
                  <ThOrdenavel {...pdb.props('asn')} className="px-3 py-2 text-left font-medium">ASN</ThOrdenavel>
                  <ThOrdenavel {...pdb.props('tipo')} className="px-3 py-2 text-left font-medium">Tipo</ThOrdenavel>
                  <ThOrdenavel {...pdb.props('trafego')} className="px-3 py-2 text-left font-medium">Tráfego</ThOrdenavel>
                  <ThOrdenavel {...pdb.props('politica')} className="px-3 py-2 text-left font-medium">Política</ThOrdenavel>
                  <ThOrdenavel {...pdb.props('irr')} className="px-3 py-2 text-left font-medium">IRR AS-SET</ThOrdenavel>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {pdb.ordenados.map((d) => (
                  <tr key={d.asn} className="hover:bg-gray-50">
                    <td className="px-3 py-2">
                      <Link to={`/asn/${d.asn}`} className="font-mono text-primario-700 hover:underline">AS{d.asn}</Link>
                    </td>
                    <td className="px-3 py-2 text-gray-700">{d.pdb!.info_type ?? '—'}</td>
                    <td className="px-3 py-2 text-gray-700">{d.pdb!.info_traffic ?? '—'}</td>
                    <td className="px-3 py-2 text-gray-700">{d.pdb!.policy_general ?? '—'}</td>
                    <td className="px-3 py-2 text-gray-500 font-mono text-xs">{d.pdb!.irr_as_set ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
