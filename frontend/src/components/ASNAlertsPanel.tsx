import { useState } from 'react'
import { Link } from './layout/LinkDatado'
import type { ASNAlert, AlertSeverity, AlertCategory } from '../types/api'

const SEVERITY_STYLE: Record<AlertSeverity, { border: string; bg: string; badge: string; label: string }> = {
  critico: { border: 'border-perigo-400', bg: 'bg-perigo-50', badge: 'bg-perigo-100 text-perigo-700', label: 'Crítico' },
  aviso: { border: 'border-aviso-400', bg: 'bg-aviso-50', badge: 'bg-aviso-100 text-aviso-700', label: 'Aviso' },
  info: { border: 'border-primario-300', bg: 'bg-primario-50', badge: 'bg-primario-100 text-primario-700', label: 'Info' },
}

const CATEGORY_LABEL: Record<AlertCategory, string> = {
  roteamento: 'Roteamento',
  rpki: 'RPKI',
  v4v6: 'IPv6/IPv4',
  presenca: 'Presença',
  geo: 'Geografia',
}

const SEVERITY_ORDER: AlertSeverity[] = ['critico', 'aviso', 'info']

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-block font-mono text-xs bg-white/70 border border-gray-200 rounded px-1.5 py-0.5">
      {children}
    </span>
  )
}

/** Renderiza os dados de apoio (refs) de um alerta de forma legível. */
function AlertRefs({ refs }: { refs: Record<string, unknown> }) {
  const blocks: React.ReactNode[] = []

  const prefixes = refs.prefixes as string[] | undefined
  if (Array.isArray(prefixes) && prefixes.length) {
    blocks.push(
      <div key="prefixes" className="flex flex-wrap gap-1">
        {prefixes.map(p => <Chip key={p}>{p}</Chip>)}
      </div>
    )
  }

  const items = refs.items as Array<Record<string, unknown>> | undefined
  if (Array.isArray(items) && items.length) {
    blocks.push(
      <div key="items" className="flex flex-wrap gap-1">
        {items.map((it, i) => {
          if (it.origin_asn != null) {
            return (
              <Chip key={i}>
                {String(it.prefix)} →{' '}
                <Link to={`/asn/${it.origin_asn}`} className="text-primario-600 hover:underline">
                  AS{String(it.origin_asn)}
                </Link>
              </Chip>
            )
          }
          if (it.maxLength != null) {
            return <Chip key={i}>{String(it.prefix)} (maxLength /{String(it.maxLength)})</Chip>
          }
          return <Chip key={i}>{JSON.stringify(it)}</Chip>
        })}
      </div>
    )
  }

  const ixps = refs.ixps as unknown[] | undefined
  if (Array.isArray(ixps) && ixps.length) {
    blocks.push(
      <div key="ixps" className="flex flex-wrap gap-1">
        {ixps.map((x, i) => {
          if (typeof x === 'string') {
            return (
              <Link key={x} to={`/ixp/${x}`} className="text-xs text-primario-600 hover:underline">
                <Chip>{x}</Chip>
              </Link>
            )
          }
          const o = x as { code?: string; name?: string; dist_km?: number }
          return (
            <Link key={o.code ?? i} to={`/ixp/${o.code}`} className="hover:underline">
              <Chip>
                {o.name ?? o.code}
                {o.dist_km != null && <span className="text-gray-500"> · {o.dist_km} km</span>}
              </Chip>
            </Link>
          )
        })}
      </div>
    )
  }

  const v4only = refs.v4_only as string[] | undefined
  const v6only = refs.v6_only as string[] | undefined
  if ((v4only?.length ?? 0) + (v6only?.length ?? 0) > 0) {
    blocks.push(
      <div key="v4v6" className="space-y-1">
        {!!v6only?.length && (
          <div className="flex flex-wrap items-center gap-1">
            <span className="text-xs text-gray-500">Só IPv6:</span>
            {v6only.map(c => <Link key={c} to={`/ixp/${c}`}><Chip>{c}</Chip></Link>)}
          </div>
        )}
        {!!v4only?.length && (
          <div className="flex flex-wrap items-center gap-1">
            <span className="text-xs text-gray-500">Só IPv4:</span>
            {v4only.map(c => <Link key={c} to={`/ixp/${c}`}><Chip>{c}</Chip></Link>)}
          </div>
        )}
      </div>
    )
  }

  return blocks.length ? <div className="mt-2 space-y-1.5">{blocks}</div> : null
}

function AlertItem({ alert }: { alert: ASNAlert }) {
  const style = SEVERITY_STYLE[alert.severity]
  const hasRefs = Object.keys(alert.refs ?? {}).length > 0
  const [open, setOpen] = useState(false)

  return (
    <div className={`border-l-4 ${style.border} ${style.bg} rounded-r px-3 py-2`}>
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`text-xs font-semibold uppercase tracking-wide rounded px-1.5 py-0.5 ${style.badge}`}>
          {style.label}
        </span>
        <span className="text-xs text-gray-500 uppercase tracking-wide">
          {CATEGORY_LABEL[alert.category]}
        </span>
        <span className="font-medium text-gray-900 text-sm">{alert.title}</span>
      </div>
      <p className="text-sm text-gray-600 mt-1">{alert.detail}</p>
      {hasRefs && (
        <>
          <button
            onClick={() => setOpen(o => !o)}
            className="text-xs text-primario-600 hover:underline mt-1"
          >
            {open ? 'Ocultar detalhes' : 'Ver detalhes'}
          </button>
          {open && <AlertRefs refs={alert.refs} />}
        </>
      )}
    </div>
  )
}

/**
 * D6 (IPv6 antes de IPv4): o pipeline gera os alertas por família na ordem v4, v6 (ex.: `desagregacao_ipv4` e `desagregacao_ipv6`).
 * Aqui o alerta IPv6 toma o lugar do seu par IPv4; o resto da ordem (severidade, regra) não muda.
 */
export function ipv6Primeiro(alerts: ASNAlert[]): ASNAlert[] {
  const familia = (id: string) => (/(ipv6|_v6)$/.test(id) ? 6 : /(ipv4|_v4)$/.test(id) ? 4 : 0)
  const base = (id: string) => id.replace(/_?(ipv4|ipv6|v4|v6)$/, '')
  const out = [...alerts]
  for (let i = 0; i < out.length; i++) {
    if (familia(out[i].id ?? '') !== 4) continue
    const j = out.findIndex((a, k) => k > i && familia(a.id ?? '') === 6 && base(a.id ?? '') === base(out[i].id ?? ''))
    if (j > i) [out[i], out[j]] = [out[j], out[i]]
  }
  return out
}

export function ASNAlertsPanel({ alerts: brutos }: { alerts?: ASNAlert[] }) {
  if (!brutos || brutos.length === 0) return null
  const alerts = ipv6Primeiro(brutos)

  const counts = SEVERITY_ORDER.map(sev => ({
    sev,
    n: alerts.filter(a => a.severity === sev).length,
  })).filter(c => c.n > 0)

  return (
    <div>
      <h2 className="text-base font-semibold text-gray-800 mb-2 flex items-center gap-2 flex-wrap">
        Pontos de Atenção
        <span className="text-xs font-normal text-gray-400">
          cruzando Registro.br, tabela global, RPKI, PeeringDB, IX.br e geo
        </span>
        <span className="flex items-center gap-1 ml-auto">
          {counts.map(({ sev, n }) => (
            <span
              key={sev}
              className={`text-xs font-semibold rounded px-1.5 py-0.5 ${SEVERITY_STYLE[sev].badge}`}
            >
              {n} {SEVERITY_STYLE[sev].label.toLowerCase()}
            </span>
          ))}
        </span>
      </h2>
      <div className="space-y-2">
        {alerts.map((a, i) => <AlertItem key={`${a.id}-${i}`} alert={a} />)}
      </div>
    </div>
  )
}
