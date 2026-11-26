import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { AsPathStats } from '../../types/routingAnalysis'
import { Tip, SortIcon, type SortDir } from './BgpShared'

interface Props {
  stats: AsPathStats
  date?: string
}

function fmt(n: number) { return n.toLocaleString('pt-BR') }

function StatCard({ label, value, sub, tooltip }: {
  label: string; value: string | number; sub?: string; tooltip: string
}) {
  return (
    <div className="bg-gray-50 rounded border border-gray-200 p-3">
      <div className="text-xs text-gray-500 mb-0.5 flex items-start gap-0.5">
        <span>{label}</span>
        <Tip text={tooltip} />
      </div>
      <div className="text-lg font-semibold text-gray-900">{value}</div>
      {sub && <div className="text-xs text-gray-400">{sub}</div>}
    </div>
  )
}

type PrepSortKey = 'routes' | 'routes_with_prepend' | 'prepend_pct' | 'avg_excess'
type UpstSortKey = 'routes' | 'upstream_count' | 'main_upstream_pct'

export function AsPathSection({ stats, date }: Props) {
  const navigate = useNavigate()

  const [prepSortKey, setPrepSortKey] = useState<PrepSortKey>('avg_excess')
  const [prepSortDir, setPrepSortDir] = useState<SortDir>('desc')
  const [upstSortKey, setUpstSortKey] = useState<UpstSortKey>('routes')
  const [upstSortDir, setUpstSortDir] = useState<SortDir>('desc')

  // Seletor de família (IPv6 primeiro). Vale para todos os quadros da aba: estatísticas, prepending, upstreams,
  // higiene e communities; a análise traz as duas famílias.
  const [afi, setAfi] = useState<'v6' | 'v4'>('v6')
  const temV6 = (stats.v6?.unique_paths_raw ?? 0) > 0
  const familia = afi === 'v6' && !temV6 ? 'v4' : afi
  const fam = stats[familia]
  const comm = stats.community_stats[familia]
  const nomeFamilia = familia === 'v6' ? 'IPv6' : 'IPv4'

  const issueLabels: Record<string, string> = {
    private_as_origin: 'Private AS como origem',
    private_as_path:   'Private AS no caminho',
    as_loop:           'Loop de AS',
    as_trans:          'AS_TRANS no caminho',
  }

  function renderPath(path: number[], issue: string) {
    if (issue !== 'as_loop') {
      return <span>{path.join(' → ')}</span>
    }
    const seen = new Set<number>()
    const repeated = new Set<number>()
    for (const asn of path) {
      if (seen.has(asn)) repeated.add(asn)
      seen.add(asn)
    }
    return (
      <span>
        {path.map((asn, idx) => (
          <span key={idx}>
            {idx > 0 && <span className="text-gray-400"> → </span>}
            <span className={repeated.has(asn) ? 'text-perigo-600 font-semibold' : ''}>
              {asn}
            </span>
          </span>
        ))}
      </span>
    )
  }

  function handlePrepSort(key: PrepSortKey) {
    if (prepSortKey === key) setPrepSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setPrepSortKey(key); setPrepSortDir('desc') }
  }

  function handleUpstSort(key: UpstSortKey) {
    if (upstSortKey === key) setUpstSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setUpstSortKey(key); setUpstSortDir('desc') }
  }

  function PrepSortTh({ k, label, tooltip }: { k: PrepSortKey; label: string; tooltip: string }) {
    const active = prepSortKey === k
    return (
      <th scope="col" aria-sort={active ? (prepSortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
        className={`text-xs font-medium pb-1.5 px-1 text-right whitespace-nowrap ${active ? 'text-primario-600' : 'text-gray-500'}`}>
        <span className="inline-flex items-center gap-0.5 justify-end">
          <button type="button" onClick={() => handlePrepSort(k)} className="hover:text-gray-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario-500">{label}<SortIcon active={active} dir={prepSortDir} /></button>
          <Tip text={tooltip} />
        </span>
      </th>
    )
  }

  function UpstSortTh({ k, label, tooltip }: { k: UpstSortKey; label: string; tooltip: string }) {
    const active = upstSortKey === k
    return (
      <th scope="col" aria-sort={active ? (upstSortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
        className={`text-xs font-medium pb-1.5 px-1 text-right whitespace-nowrap ${active ? 'text-primario-600' : 'text-gray-500'}`}>
        <span className="inline-flex items-center gap-0.5 justify-end">
          <button type="button" onClick={() => handleUpstSort(k)} className="hover:text-gray-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario-500">{label}<SortIcon active={active} dir={upstSortDir} /></button>
          <Tip text={tooltip} />
        </span>
      </th>
    )
  }

  const sortedPrependers = [...stats.top_prependers]
    .filter((r) => r.afi === familia)
    .sort((a, b) => {
      const aVal = a[prepSortKey] as number
      const bVal = b[prepSortKey] as number
      return prepSortDir === 'desc' ? bVal - aVal : aVal - bVal
    })

  const sortedUpstream = [...stats.upstream_diversity]
    .filter((r) => r.afi === familia)
    .sort((a, b) => {
      const aVal = a[upstSortKey] as number
      const bVal = b[upstSortKey] as number
      return upstSortDir === 'desc' ? bVal - aVal : aVal - bVal
    })

  return (
    <div className="space-y-4">

      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-gray-500">Todos os quadros abaixo mostram a família escolhida.</p>
        <div className="flex text-xs rounded border border-gray-200 overflow-hidden" role="group" aria-label="Família de endereços">
          {(['v6', 'v4'] as const).map((a) => (
            <button key={a} type="button" aria-pressed={familia === a} disabled={a === 'v6' && !temV6} onClick={() => setAfi(a)}
              className={`min-h-6 px-2.5 py-1 disabled:opacity-40 ${familia === a ? 'bg-primario-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}>
              {a === 'v6' ? 'IPv6' : 'IPv4'}
            </button>
          ))}
        </div>
      </div>

      {/* Estatísticas de AS_PATH */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-medium text-gray-700 mb-3">
          Estatísticas de AS_PATH ({nomeFamilia})
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard
            label="Comprimento médio (normalizado)"
            value={fam.avg_len_norm}
            tooltip="Comprimento médio do AS_PATH após remoção de repetições (prepending). Indica quantos saltos de AS separam os coletores dos ASNs brasileiros em média."
          />
          <StatCard
            label="Mediana do comprimento"
            value={fam.median_norm}
            tooltip="Metade das rotas brasileiras tem AS_PATH com comprimento menor ou igual a este valor. Menos sensível a outliers do que a média."
          />
          <StatCard
            label="Percentil 95 (P95)"
            value={fam.p95_norm}
            tooltip="95% das rotas brasileiras têm AS_PATH com comprimento até este valor. Indica o limite superior típico de profundidade na topologia."
          />
          <StatCard
            label="Rotas com prepending"
            value={`${fam.prepend_pct}%`}
            sub={fmt(fam.routes_with_prepend) + ' rotas'}
            tooltip="Percentual de rotas onde o AS de origem repete seu próprio número mais de uma vez no AS_PATH. Prepending é uma técnica para desincentivar o uso de determinado caminho de entrada."
          />
        </div>
      </div>

      {/* Top prependers */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-medium text-gray-700 mb-3">Top prependers ({nomeFamilia})</h3>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[480px]">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-xs font-medium text-gray-500 text-left pb-1.5 px-1">ASN</th>
                <th className="text-xs font-medium text-gray-500 text-left pb-1.5 px-1">Organização</th>
                <PrepSortTh k="routes"              label="Rotas"             tooltip="Total de rotas do ASN vistas pelos coletores." />
                <PrepSortTh k="routes_with_prepend" label="Com prepend"       tooltip="Número de rotas onde o ASN repete seu número no AS_PATH para influenciar a seleção de caminho de entrada." />
                <PrepSortTh k="prepend_pct"         label="%"                 tooltip="Percentual das rotas do ASN que usam prepending." />
                <PrepSortTh k="avg_excess"          label="Repetições médias" tooltip="Média de vezes que o ASN de origem repete seu número no AS_PATH nas rotas com prepending. Ex: 2x significa que o ASN aparece 3 vezes no total." />
              </tr>
            </thead>
            <tbody>
              {sortedPrependers.slice(0, 20).map((r, i) => (
                <tr key={i} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="py-1.5 px-1">
                    <button
                      className="text-xs text-primario-600 hover:underline font-mono"
                      onClick={() => navigate(`/asn/${r.asn}${date ? `?date=${date}` : ''}`)}
                    >
                      {r.asn}
                    </button>
                  </td>
                  <td className="py-1.5 px-1 text-xs text-gray-700 max-w-[140px] truncate">{r.name || '—'}</td>
                  <td className="py-1.5 px-1 text-xs text-right font-mono">{fmt(r.routes)}</td>
                  <td className="py-1.5 px-1 text-xs text-right font-mono text-alerta-600">{fmt(r.routes_with_prepend)}</td>
                  <td className="py-1.5 px-1 text-xs text-right font-mono text-alerta-600">{r.prepend_pct}%</td>
                  <td className="py-1.5 px-1 text-xs text-right font-mono">{r.avg_excess}×</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Upstream e diversidade */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-medium text-gray-700 mb-3">Upstream e diversidade ({nomeFamilia})</h3>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[480px]">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-xs font-medium text-gray-500 text-left pb-1.5 px-1">ASN</th>
                <th className="text-xs font-medium text-gray-500 text-left pb-1.5 px-1">Organização</th>
                <UpstSortTh k="routes"           label="Rotas"       tooltip="Total de rotas do ASN visíveis nos coletores." />
                <UpstSortTh k="upstream_count"   label="Upstreams"   tooltip="Número de ASNs distintos que aparecem como penúltimo salto no AS_PATH, indicando a diversidade de provedores de trânsito." />
                <th className="text-xs font-medium text-gray-500 text-right pb-1.5 px-1">
                  <span className="inline-flex items-center gap-0.5 justify-end">
                    Upstream principal
                    <Tip text="O ASN que mais aparece como penúltimo salto no AS_PATH, o que sugere (por inferência) que seja o principal provedor de trânsito." />
                  </span>
                </th>
                <UpstSortTh k="main_upstream_pct" label="% via principal" tooltip="Percentual das rotas roteadas exclusivamente via o upstream principal. 100% indica dependência total de um único provedor." />
              </tr>
            </thead>
            <tbody>
              {sortedUpstream.slice(0, 30).map((r, i) => (
                <tr key={i} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="py-1.5 px-1">
                    <button className="text-xs text-primario-600 hover:underline font-mono"
                      onClick={() => navigate(`/asn/${r.asn}${date ? `?date=${date}` : ''}`)}>
                      {r.asn}
                    </button>
                  </td>
                  <td className="py-1.5 px-1 text-xs text-gray-700 max-w-[140px] truncate">{r.name || '—'}</td>
                  <td className="py-1.5 px-1 text-xs text-right font-mono">{fmt(r.routes)}</td>
                  <td className="py-1.5 px-1 text-xs text-right font-mono">{r.upstream_count}</td>
                  <td className="py-1.5 px-1 text-right">
                    <button className="text-xs text-primario-600 hover:underline font-mono"
                      onClick={() => navigate(`/asn/${r.main_upstream}${date ? `?date=${date}` : ''}`)}>
                      {r.main_upstream}
                    </button>
                  </td>
                  <td className="py-1.5 px-1 text-xs text-right font-mono">{r.main_upstream_pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Higiene de AS_PATH */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-medium text-gray-700 mb-3">Higiene de AS_PATH ({nomeFamilia})</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <StatCard
            label="Private AS como origem"
            value={fmt(fam.private_as_as_origin)}
            tooltip="Rotas com número de ASN privado (de 64512 a 65535 ou de 4200000000 a 4294967295) como ASN de origem. Esses ASNs não deveriam ser visíveis na Internet pública."
          />
          <StatCard
            label="Private AS no caminho"
            value={fmt(fam.private_as_in_path)}
            tooltip="Rotas onde um ASN privado aparece no meio do AS_PATH (mas não como origem). Indica vazamento de configuração interna."
          />
          <StatCard
            label="Loops de AS"
            value={fmt(fam.as_loops)}
            tooltip="Rotas onde o mesmo ASN aparece mais de uma vez no AS_PATH em posições não contíguas, indicando anomalia de roteamento ou erro de configuração."
          />
          <StatCard
            label="AS_TRANS (AS 23456)"
            value={fmt(fam.as_trans_present)}
            tooltip="AS 23456 é um placeholder usado durante a migração para ASNs de 4 bytes. A presença indica que algum ponto do caminho não suporta 4-byte ASNs corretamente."
          />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[480px]">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-xs font-medium text-gray-500 text-left pb-1.5 px-1">Prefixo</th>
                <th className="text-xs font-medium text-gray-500 text-left pb-1.5 px-1">Tipo de problema</th>
                <th className="text-xs font-medium text-gray-500 text-left pb-1.5 px-1">ASN de origem</th>
                <th className="text-xs font-medium text-gray-500 text-left pb-1.5 px-1">AS_PATH</th>
              </tr>
            </thead>
            <tbody>
              {stats.hygiene_issues.filter((r) => r.afi === familia).slice(0, 30).map((r, i) => (
                <tr key={i} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="py-1.5 px-1 text-xs font-mono text-gray-800">{r.prefix}</td>
                  <td className="py-1.5 px-1">
                    <span className="text-xs bg-perigo-50 text-perigo-700 px-1.5 py-0.5 rounded">
                      {issueLabels[r.issue] ?? r.issue}
                    </span>
                  </td>
                  <td className="py-1.5 px-1">
                    <button className="text-xs text-primario-600 hover:underline font-mono"
                      onClick={() => navigate(`/asn/${r.origin_as}${date ? `?date=${date}` : ''}`)}>
                      {r.origin_as}
                    </button>
                  </td>
                  <td className="py-1.5 px-1 text-xs font-mono text-gray-500 max-w-[260px] truncate">
                    {renderPath(r.as_path, r.issue)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Communities BGP */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-medium text-gray-700 mb-3">Communities BGP ({nomeFamilia})</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <StatCard
            label="Rotas com communities"
            value={`${comm.community_pct}%`}
            sub={fmt(comm.routes_with_communities)}
            tooltip="Percentual das rotas brasileiras que carregam ao menos uma community BGP. Communities são atributos opcionais usados para sinalizar políticas de roteamento."
          />
          <StatCard
            label="NO_EXPORT"
            value={fmt(comm.no_export_count)}
            tooltip="Rotas com a community well-known NO_EXPORT (65535:65281), que instrui o receptor a não propagar o prefixo para seus peers externos."
          />
          <StatCard
            label="Candidatos a blackhole"
            value={fmt(comm.blackhole_candidates)}
            tooltip="Rotas com communities típicas de blackholing (ex: 65535:666, RTBH). Blackhole é uma técnica usada para descartar tráfego indesejado, normalmente em resposta a ataques DDoS."
          />
          <StatCard
            label="Vazamento de community privada"
            value={fmt(comm.private_community_leak_count)}
            tooltip="Rotas com communities de uso interno (ASN:valor onde o ASN é privado ou não corresponde a nenhum AS no caminho). Pode indicar vazamento de políticas internas."
          />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px]">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-xs font-medium text-gray-500 text-left pb-1.5 px-1">
                  <span className="inline-flex items-center gap-0.5">
                    Community
                    <Tip text="Valor da community BGP no formato ASN:valor (standard) ou ASN:valor:valor (large community). O ASN antes dos dois-pontos indica o operador que definiu a community." />
                  </span>
                </th>
                <th className="text-xs font-medium text-gray-500 text-left pb-1.5 px-1">
                  <span className="inline-flex items-center gap-0.5">
                    Significado
                    <Tip text="Operador responsável e descrição da semântica desta community conforme documentação pública (BPF wiki, documentação IX.br)." />
                  </span>
                </th>
                <th className="text-xs font-medium text-gray-500 text-right pb-1.5 px-1">
                  <span className="inline-flex items-center gap-0.5 justify-end">
                    Frequência
                    <Tip text="Número de rotas brasileiras que carregam esta community." />
                  </span>
                </th>
                <th className="text-xs font-medium text-gray-500 text-left pb-1.5 px-1">
                  <span className="inline-flex items-center gap-0.5">
                    ASNs com esta community
                    <Tip text="ASNs de origem cujas rotas carregam esta community. A community pode ter sido adicionada por qualquer ASN no caminho, não necessariamente pelo originador." />
                  </span>
                </th>
              </tr>
            </thead>
            <tbody>
              {comm.top_communities.map((c, i) => (
                <tr key={i} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="py-1.5 px-1 text-xs font-mono text-gray-800 whitespace-nowrap">{c.community}</td>
                  <td className="py-1.5 px-1 text-xs text-gray-600 max-w-[260px]">
                    {c.description ? (
                      <span title={c.description}>
                        {c.operator && (
                          <span className="font-medium text-gray-800">{c.operator}: </span>
                        )}
                        <span className="truncate">{c.description}</span>
                      </span>
                    ) : (
                      <span className="text-gray-300">—</span>
                    )}
                  </td>
                  <td className="py-1.5 px-1 text-xs text-right font-mono">{fmt(c.count)}</td>
                  <td className="py-1.5 px-1">
                    <div className="flex gap-1 flex-wrap">
                      {c.asns.slice(0, 5).map((asn) => (
                        <button key={asn} className="text-xs text-primario-600 hover:underline font-mono"
                          onClick={() => navigate(`/asn/${asn}${date ? `?date=${date}` : ''}`)}>
                          {asn}
                        </button>
                      ))}
                      {c.asns.length > 5 && <span className="text-xs text-gray-400">+{c.asns.length - 5}</span>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <p className="text-xs text-gray-400">
        Dados de AS_PATH e communities dependem dos peers dos coletores RouteViews/RIPE RIS utilizados.
        Ausência de community não implica ausência operacional; muitos operadores filtram communities na exportação para peers externos.
      </p>
    </div>
  )
}
