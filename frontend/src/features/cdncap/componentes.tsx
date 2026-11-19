// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Tabelas de ROA e ASPA, KPI e caixa de prefixos da página de CDN/CAP. */
import { Link } from 'react-router-dom'
import { useState } from 'react'
import type { RoaEntry, AspaProviderEntry, AspaCustomerEntry } from '../../types/api'
import { corLegivel } from '../../lib/contraste'

export function fmtN(n: number | null | undefined): string {
  return n == null ? '—' : n.toLocaleString('pt-BR')
}

export const TA_COLORS: Record<string, string> = {
  lacnic:  'bg-ok-100 text-ok-800',
  ripe:    'bg-primario-100 text-primario-800',
  arin:    'bg-alerta-100 text-alerta-800',
  apnic:   'bg-v6-100 text-v6-800',
  afrinic: 'bg-aviso-100 text-aviso-800',
}

export const RPKI_DOT: Record<string, string> = {
  valid:     'bg-ok-500',
  invalid:   'bg-perigo-500',
  not_found: 'bg-gray-300',
}

export const RPKI_LABEL: Record<string, string> = {
  valid:     'válido',
  invalid:   'inválido',
  not_found: 'sem ROA',
}

// ─── ROAs autorizados (agregado de todos os ASNs do grupo) ────────────────────

/** Resumo agregado dos ROAs: quantos, por trust anchor e por maxLength; a lista fica recolhida (a de uma CDN grande passa de mil linhas). */
function RoaAgregado({ roaList }: { roaList: RoaEntry[] }) {
  const porTa = new Map<string, number>()
  const folga = { exato: 0, maior: 0 }
  for (const r of roaList) {
    porTa.set(r.ta.toLowerCase(), (porTa.get(r.ta.toLowerCase()) ?? 0) + 1)
    const base = Number(r.prefix.split('/')[1])
    if (Number.isFinite(base) && r.maxLength > base) folga.maior++; else folga.exato++
  }
  return (
    <p className="text-xs text-gray-600" data-testid="roa-agregado">
      {[...porTa.entries()].sort((a, b) => b[1] - a[1]).map(([ta, n]) => `${ta.toUpperCase()}: ${fmtN(n)}`).join(' · ')}
      {' · '}maxLength igual ao prefixo: {fmtN(folga.exato)} · maxLength maior que o prefixo: {fmtN(folga.maior)}
    </p>
  )
}

export function RoaTable({ title, accent, roaList }: { title: string; accent: string; roaList: RoaEntry[] }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-800 mb-1.5 flex items-center gap-2">
        <span className="inline-block w-3 h-3 rounded-sm" style={{ background: accent }} />
        {title} ({roaList.length})
      </h3>
      {roaList.length === 0 ? (
        <div className="bg-gray-50 rounded border border-gray-200 p-4 flex items-center justify-center text-sm text-gray-400">
          Nenhum ROA encontrado
        </div>
      ) : (
        <div className="space-y-2">
          <RoaAgregado roaList={roaList} />
          <details className="text-xs">
            <summary className="cursor-pointer text-primario-600 hover:underline">Ver a lista dos {fmtN(roaList.length)} ROAs</summary>
            <div className="mt-2">
        <div className="bg-gray-50 rounded border border-gray-200 overflow-hidden max-h-56 overflow-y-auto font-mono text-xs">
          <div className="flex items-center gap-2 px-3 py-1 bg-white border-b border-gray-200 text-gray-400 font-sans font-medium sticky top-0">
            <span className="flex-1">Prefixo</span>
            <span className="w-14 text-right">maxLen</span>
            <span className="w-14">TA</span>
          </div>
          <div className="grid grid-cols-1 gap-y-0.5 p-3">
            {roaList.map((roa) => (
              <div key={`${roa.prefix}-${roa.maxLength}-${roa.ta}`} className="flex items-center gap-2">
                <span style={{ color: accent }} className="flex-1">{roa.prefix}</span>
                <span className="text-gray-500 w-14 text-right">/{roa.maxLength}</span>
                <span className={`inline-block px-1 rounded font-sans font-medium uppercase leading-4 ${TA_COLORS[roa.ta.toLowerCase()] ?? 'bg-gray-100 text-gray-600'}`}>
                  {roa.ta}
                </span>
              </div>
            ))}
          </div>
        </div>
            </div>
          </details>
        </div>
      )}
    </div>
  )
}

// ─── ASPA ─────────────────────────────────────────────────────────────────────

export function AspaProvidersTable({ aspaProviders }: { aspaProviders: AspaProviderEntry[] }) {
  const allProviders = aspaProviders.flatMap((e) =>
    e.providers.map((asn) => ({ asn, tal: e.tal }))
  )
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-800 mb-1.5 flex items-center gap-2">
        <span className="inline-block w-3 h-3 rounded-sm bg-primario-400" />
        ASPA: provedores declarados ({allProviders.length})
      </h3>
      {allProviders.length === 0 ? (
        <div className="bg-gray-50 rounded border border-gray-200 p-4 flex items-center justify-center text-sm text-gray-400">
          Nenhum objeto ASPA publicado
        </div>
      ) : (
        <div className="bg-gray-50 rounded border border-gray-200 overflow-hidden max-h-56 overflow-y-auto font-mono text-xs">
          <div className="flex items-center gap-2 px-3 py-1 bg-white border-b border-gray-200 text-gray-400 font-sans font-medium sticky top-0">
            <span className="flex-1">Provider AS</span>
            <span className="w-14">TAL</span>
          </div>
          <div className="grid grid-cols-1 gap-y-0.5 p-3">
            {allProviders.map(({ asn, tal }, i) => (
              <div key={`${asn}-${i}`} className="flex items-center gap-2">
                <Link to={`/asn/${asn}`} className="text-primario-700 hover:underline flex-1">
                  AS{asn}
                </Link>
                <span className={`inline-block px-1 rounded font-sans font-medium uppercase leading-4 ${TA_COLORS[tal.toLowerCase()] ?? 'bg-gray-100 text-gray-600'}`}>
                  {tal}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export function AspaCustomersTable({ aspaCustomers }: { aspaCustomers: AspaCustomerEntry[] }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-800 mb-1.5 flex items-center gap-2">
        <span className="inline-block w-3 h-3 rounded-sm bg-v6-400" />
        ASPA: declarado como provedor por ({aspaCustomers.length})
      </h3>
      {aspaCustomers.length === 0 ? (
        <div className="bg-gray-50 rounded border border-gray-200 p-4 flex items-center justify-center text-sm text-gray-400">
          Nenhum AS declarou este grupo como provedor
        </div>
      ) : (
        <div className="bg-gray-50 rounded border border-gray-200 overflow-hidden max-h-56 overflow-y-auto font-mono text-xs">
          <div className="flex items-center gap-2 px-3 py-1 bg-white border-b border-gray-200 text-gray-400 font-sans font-medium sticky top-0">
            <span className="flex-1">Customer AS</span>
            <span className="w-14">TAL</span>
          </div>
          <div className="grid grid-cols-1 gap-y-0.5 p-3">
            {aspaCustomers.map(({ customer, tal }) => (
              <div key={`${customer}-${tal}`} className="flex items-center gap-2">
                <Link to={`/asn/${customer}`} className="text-v6-700 hover:underline flex-1">
                  AS{customer}
                </Link>
                <span className={`inline-block px-1 rounded font-sans font-medium uppercase leading-4 ${TA_COLORS[tal.toLowerCase()] ?? 'bg-gray-100 text-gray-600'}`}>
                  {tal}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── KPI ──────────────────────────────────────────────────────────────────────

export function Kpi({ value, label, sub, color }: { value: string; label: string; sub?: string; color: string }) {
  return (
    <div className="px-3 py-1">
      <div className="text-2xl sm:text-3xl font-extrabold tabular-nums leading-none" style={{ color: corLegivel(color) }}>{value}</div>
      <div className="text-xs sm:text-xs text-gray-700 mt-1 leading-tight font-medium">{label}</div>
      {sub && <div className="text-xs text-gray-400 leading-tight">{sub}</div>}
    </div>
  )
}

// ─── caixa de prefixos ──────────────────────────────────────────────────────

export function PrefixBox({
  title, accent, rirCount, prefixes, rpkiValidation,
}: {
  title: string
  accent: string
  rirCount: number
  prefixes: string[]
  rpkiValidation?: Record<string, string>
}) {
  const [showAll, setShowAll] = useState(false)
  const shown = showAll ? prefixes : prefixes.slice(0, 60)
  // Validação RPKI sempre exibida para todo prefixo — sem ROA cobrindo conta como "sem ROA".
  const counts = { valid: 0, invalid: 0, not_found: 0 }
  for (const p of prefixes) {
    const s = (rpkiValidation?.[p] ?? 'not_found') as keyof typeof counts
    if (s in counts) counts[s]++
  }

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-800 mb-1.5 flex items-center gap-2 flex-wrap">
        <span className="inline-block w-3 h-3 rounded-sm" style={{ background: accent }} />
        {title} ({fmtN(prefixes.length)})
        <span className="text-xs font-normal text-gray-400">· {fmtN(rirCount)} no Registro.br</span>
        {prefixes.length > 0 && (
          <span className="flex items-center gap-2 ml-auto">
            {counts.valid > 0 && (
              <span className="inline-flex items-center gap-1 text-xs font-normal text-ok-700">
                <span className="w-1.5 h-1.5 rounded-full bg-ok-500" />{counts.valid} válido{counts.valid !== 1 ? 's' : ''}
              </span>
            )}
            {counts.invalid > 0 && (
              <span className="inline-flex items-center gap-1 text-xs font-normal text-perigo-700">
                <span className="w-1.5 h-1.5 rounded-full bg-perigo-500" />{counts.invalid} inválido{counts.invalid !== 1 ? 's' : ''}
              </span>
            )}
            {counts.not_found > 0 && (
              <span className="inline-flex items-center gap-1 text-xs font-normal text-gray-500">
                <span className="w-1.5 h-1.5 rounded-full bg-gray-300" />{counts.not_found} sem ROA
              </span>
            )}
          </span>
        )}
      </h3>
      {prefixes.length === 0 ? (
        <div className="bg-gray-50 rounded border border-gray-200 p-3 text-xs text-gray-400">Nenhum prefixo</div>
      ) : (
        <div className="bg-gray-50 rounded border border-gray-200 p-3 max-h-48 overflow-y-auto font-mono text-xs">
          <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
            {shown.map((p) => {
              const rpkiStatus = rpkiValidation?.[p] ?? 'not_found'
              return (
                <div key={p} className="flex items-center gap-1.5">
                  <span style={{ color: accent }}>{p}</span>
                  <span
                    title={RPKI_LABEL[rpkiStatus]}
                    className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${RPKI_DOT[rpkiStatus] ?? 'bg-gray-300'}`}
                  />
                </div>
              )
            })}
          </div>
        </div>
      )}
      {prefixes.length > 60 && !showAll && (
        <button onClick={() => setShowAll(true)} className="mt-1.5 text-xs text-primario-600 hover:underline">
          Ver todos os {fmtN(prefixes.length)} prefixos
        </button>
      )}
      {prefixes.length > 0 && (
        <p className="text-xs text-gray-400 mt-1">Ponto = status RPKI (verde = válido, vermelho = inválido, cinza = sem ROA cobrindo)</p>
      )}
    </div>
  )
}
