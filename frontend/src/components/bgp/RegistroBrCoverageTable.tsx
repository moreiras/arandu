import { useState, useMemo, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import type { RegistroBrCoverage, OriginDetail } from '../../types/routingAnalysis'
import { Tip, SortIcon, type SortDir } from './BgpShared'
import { ordenar } from '../../lib/ordenacao'

interface Props {
  data: RegistroBrCoverage[]
  date?: string
}

const CATEGORY_BADGE: Record<string, { label: string; cls: string; tooltip: string }> = {
  not_announced:    {
    label: 'Não anunciado',
    cls: 'bg-perigo-100 text-perigo-700',
    tooltip: 'Nenhuma rota cobre este bloco na tabela global. Pode indicar recurso não utilizado ou anunciado por caminho não visível nestes coletores.',
  },
  partial:          {
    label: 'Parcial',
    cls: 'bg-alerta-100 text-alerta-700',
    tooltip: 'Apenas parte do espaço alocado ao Registro.br está sendo roteada. O restante não está visível na tabela global.',
  },
  full_with_agg:    {
    label: 'Completo + agregado',
    cls: 'bg-ok-100 text-ok-700',
    tooltip: 'O bloco completo está coberto na tabela global e há um prefixo agregado (menos específico) abrangendo todo o espaço. Configuração ideal.',
  },
  full_without_agg: {
    label: 'Completo sem agregado',
    cls: 'bg-aviso-100 text-aviso-700',
    tooltip: 'O espaço total está coberto, mas por múltiplos prefixos mais específicos sem um agregado único. Poderia ser simplificado.',
  },
  multi_origin:     {
    label: 'Várias origens, sem agregado',
    cls: 'bg-v6-100 text-v6-700',
    tooltip: 'O bloco está todo coberto por rotas mais específicas de origens diferentes e nenhuma rota cobre o bloco inteiro.',
  },
}

const RPKI_CLS: Record<string, string> = {
  valid:     'text-ok-600',
  invalid:   'text-perigo-600',
  not_found: 'text-gray-400',
}
const RPKI_LABEL: Record<string, string> = {
  valid:     'válido',
  invalid:   'inválido',
  not_found: 'desconhecido',
}

function fmtCnpj(cnpj: string): string {
  if (!cnpj || cnpj.length !== 14) return cnpj || '—'
  return `${cnpj.slice(0, 2)}.${cnpj.slice(2, 5)}.${cnpj.slice(5, 8)}/${cnpj.slice(8, 12)}-${cnpj.slice(12)}`
}

type Category = keyof typeof CATEGORY_BADGE | 'all'
type AfiFilter = 'all' | 'v6' | 'v4'
type SortKey = 'block' | 'afi' | 'asn' | 'name' | 'cnpj' | 'coverage_pct' | 'routes_inside' | 'category'

function fmt(n: number) { return n.toLocaleString('pt-BR') }

function OriginTip({ detail, isOwner, date }: { detail: OriginDetail; isOwner: boolean; date?: string }) {
  const navigate = useNavigate()
  const [tipRect, setTipRect] = useState<DOMRect | null>(null)
  const btnRef = useRef<HTMLButtonElement>(null)

  const tip = tipRect ? createPortal(
    (() => {
      const GAP = 6
      const TIP_W = 288
      const above = tipRect.top > 220
      const top = above ? tipRect.top - GAP : tipRect.bottom + GAP
      const left = Math.min(tipRect.left, window.innerWidth - TIP_W - 8)
      return (
        <div
          style={{
            position: 'fixed',
            top,
            left,
            transform: above ? 'translateY(-100%)' : 'none',
            zIndex: 9999,
            width: TIP_W,
          }}
          className="rounded bg-white border border-gray-200 text-gray-800 text-xs px-2.5 py-2 leading-relaxed whitespace-normal shadow-lg pointer-events-none"
        >
          <div className="font-mono font-semibold mb-0.5 text-gray-900">AS{detail.asn}</div>
          {detail.name && <div className="text-gray-700 text-xs mb-0.5">{detail.name}</div>}
          {detail.cnpj
            ? <div className="text-gray-500">CNPJ {fmtCnpj(detail.cnpj)}</div>
            : <div className="text-gray-400 italic">CNPJ não disponível</div>}
          {isOwner && <div className="text-primario-600 text-xs mt-0.5">Titular do bloco no Registro.br</div>}
          {detail.routes.length > 0 && (
            <div className="mt-1.5 border-t border-gray-100 pt-1.5 space-y-0.5">
              {detail.routes.map((r) => (
                <div key={r.prefix} className="flex justify-between gap-3">
                  <span className="font-mono">{r.prefix}</span>
                  <span className={RPKI_CLS[r.rpki] ?? 'text-gray-400'}>
                    {RPKI_LABEL[r.rpki] ?? r.rpki}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )
    })(),
    document.body
  ) : null

  return (
    <span
      className="inline-block"
      onMouseEnter={() => setTipRect(btnRef.current?.getBoundingClientRect() ?? null)}
      onMouseLeave={() => setTipRect(null)}
    >
      <button
        ref={btnRef}
        onClick={() => navigate(`/asn/${detail.asn}${date ? `?date=${date}` : ''}`)}
        className={`text-xs font-mono hover:underline ${isOwner ? 'text-primario-600' : 'text-alerta-600'}`}
      >
        {detail.asn}
      </button>
      {tip}
    </span>
  )
}

export function RegistroBrCoverageTable({ data, date }: Props) {
  const navigate = useNavigate()
  const [cat, setCat]         = useState<Category>('all')
  const [afi, setAfi]         = useState<AfiFilter>('all')
  const [page, setPage]       = useState(0)
  const [sortKey, setSortKey] = useState<SortKey>('coverage_pct')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const PAGE = 25

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      // Texto e ASN começam de A a Z / do menor; cobertura, do menor (o que falta anunciar); rotas, do maior.
      setSortDir(key === 'routes_inside' ? 'desc' : 'asc')
    }
    setPage(0)
  }

  const filtered = useMemo(() => {
    const rows = data.filter(
      (r) => (cat === 'all' || r.category === cat) && (afi === 'all' || r.afi === afi),
    )
    // Vazios (sem nome, sem CNPJ) no fim nos dois sentidos; prefixos comparados com os números (`numeric`).
    return ordenar(rows, (r) => r[sortKey], sortDir)
  }, [data, cat, afi, sortKey, sortDir])

  const visible = filtered.slice(page * PAGE, (page + 1) * PAGE)

  function SortTh({ k, label, right, tooltip }: {
    k: SortKey; label: string; right?: boolean; tooltip?: string
  }) {
    const active = sortKey === k
    return (
      <th
        scope="col"
        aria-sort={active ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
        className={[
          'text-xs font-medium pb-1.5 px-1 whitespace-nowrap',
          right ? 'text-right' : 'text-left',
          active ? 'text-primario-600' : 'text-gray-500',
        ].join(' ')}
      >
        <span className={`inline-flex items-center gap-0.5${right ? ' justify-end' : ''}`}>
          <button type="button" onClick={() => handleSort(k)}
            className="hover:text-gray-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario-500">
            {label}<SortIcon active={active} dir={sortDir} />
          </button>
          {tooltip && <Tip text={tooltip} />}
        </span>
      </th>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h3 className="text-sm font-medium text-gray-700">Cobertura dos blocos alocados pelo Registro.br</h3>
        <div className="flex gap-1 flex-wrap">
          {(['all', 'v6', 'v4'] as AfiFilter[]).map((a) => (
            <button
              key={a}
              onClick={() => { setAfi(a); setPage(0) }}
              className={`text-xs px-2 py-0.5 rounded ${
                afi === a ? 'bg-primario-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {a === 'all' ? 'Todos' : a.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-1 flex-wrap mb-3">
        <button
          onClick={() => { setCat('all'); setPage(0) }}
          className={`text-xs px-2 py-0.5 rounded ${cat === 'all' ? 'bg-gray-700 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
        >
          Todos
        </button>
        {(Object.keys(CATEGORY_BADGE) as (keyof typeof CATEGORY_BADGE)[]).map((c) => {
          const { label, cls } = CATEGORY_BADGE[c]
          return (
            <button
              key={c}
              onClick={() => { setCat(c); setPage(0) }}
              className={`text-xs px-2 py-0.5 rounded ${cat === c ? cls + ' ring-1 ring-current' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
            >
              {label}
            </button>
          )
        })}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px]">
          <thead>
            <tr className="border-b border-gray-200">
              <SortTh k="block" label="Bloco" tooltip="Prefixo IP alocado pelo Registro.br ao ASN brasileiro correspondente." />
              <SortTh k="afi" label="Fam." />
              <SortTh k="asn" label="Titular — ASN"
                tooltip="Número do sistema autônomo titular do bloco conforme alocação do Registro.br." />
              <SortTh k="name" label="Nome" tooltip="Nome da organização titular do bloco conforme Registro.br." />
              <SortTh k="cnpj" label="CNPJ" tooltip="CNPJ da organização titular conforme Registro.br." />
              <th scope="col" className="text-xs font-medium text-gray-500 text-left pb-1.5 px-1">
                <span className="inline-flex items-center gap-0.5">
                  Anuncia na tabela
                  <Tip text="ASN(s) que originam rotas cobrindo este bloco na tabela global. Passe o mouse sobre cada ASN para ver CNPJ, rotas anunciadas e status RPKI de cada uma. ASNs em laranja diferem do titular." />
                </span>
              </th>
              <SortTh k="routes_inside" label="Rotas" right
                tooltip="Número de rotas na tabela global que cobrem total ou parcialmente este bloco." />
              <SortTh k="coverage_pct" label="Cobertura" right
                tooltip="Percentual do espaço de endereços do bloco que está efetivamente anunciado na tabela global." />
              <SortTh k="category" label="Status"
                tooltip="Classificação da cobertura do bloco. Passe o mouse sobre cada status no filtro acima para ver a descrição." />
            </tr>
          </thead>
          <tbody>
            {visible.map((r, i) => {
              const badge = CATEGORY_BADGE[r.category]
              const detail = r.origins_detail ?? []
              return (
                <tr key={i} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="py-1.5 px-1 text-xs font-mono text-gray-800">{r.block}</td>
                  <td className="py-1.5 px-1 text-xs text-gray-500 uppercase">{r.afi}</td>
                  <td className="py-1.5 px-1 text-xs">
                    <button
                      className="text-primario-600 hover:underline font-mono"
                      onClick={() => navigate(`/asn/${r.asn}${date ? `?date=${date}` : ''}`)}
                    >
                      AS{r.asn}
                    </button>
                  </td>
                  <td className="py-1.5 px-1 text-xs text-gray-700 max-w-[140px] truncate" title={r.name}>
                    {r.name || '—'}
                  </td>
                  <td className="py-1.5 px-1 text-xs font-mono text-gray-500 whitespace-nowrap">
                    {r.cnpj
                      ? <button className="hover:text-primario-600 hover:underline"
                                onClick={() => navigate(`/operadora/${r.cnpj}`)}>
                          {fmtCnpj(r.cnpj)}
                        </button>
                      : '—'}
                  </td>
                  <td className="py-1.5 px-1">
                    {detail.length === 0 ? (
                      <span className="text-xs text-gray-400">—</span>
                    ) : (
                      <div className="flex gap-1 flex-wrap">
                        {detail.slice(0, 10).map((d) => (
                          <OriginTip key={d.asn} detail={d} isOwner={d.asn === r.asn} date={date} />
                        ))}
                        {detail.length > 10 && (
                          <span className="text-xs text-gray-400">+{detail.length - 10}</span>
                        )}
                      </div>
                    )}
                  </td>
                  <td className="py-1.5 px-1 text-xs text-right font-mono text-gray-700">{fmt(r.routes_inside)}</td>
                  <td className="py-1.5 px-1 text-xs text-right font-mono text-gray-700">
                    {r.coverage_pct.toFixed(1)}%
                  </td>
                  <td className="py-1.5 px-1">
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded ${badge.cls}`}
                      title={badge.tooltip}
                    >
                      {badge.label}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {filtered.length > PAGE && (
        <div className="flex justify-between items-center mt-3">
          <span className="text-xs text-gray-400">{fmt(filtered.length)} blocos</span>
          <div className="flex gap-1">
            <button disabled={page === 0} onClick={() => setPage((p) => p - 1)}
              className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600 disabled:opacity-40">
              ← anterior
            </button>
            <button disabled={(page + 1) * PAGE >= filtered.length} onClick={() => setPage((p) => p + 1)}
              className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600 disabled:opacity-40">
              próxima →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
