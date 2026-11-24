// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { TA_COLORS, ACCENT, type Accent } from './ui'
import type { RoaEntry, AspaProviderEntry, AspaCustomerEntry } from '../../types/api'
import { Link } from '../../components/layout/LinkDatado'

export function RoaTable({ title, accent, roaList }: { title: string; accent: Accent; roaList: RoaEntry[] }) {
  const { dot, text } = ACCENT[accent]
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-800 mb-1.5 flex items-center gap-2">
        <span className={`inline-block w-3 h-3 rounded-sm ${dot}`} />
        {title} ({roaList.length})
      </h3>
      {roaList.length === 0 ? (
        <div className="bg-gray-50 rounded border border-gray-200 p-4 flex items-center justify-center text-sm text-gray-400">
          Nenhum ROA encontrado
        </div>
      ) : (
        <div className="bg-gray-50 rounded border border-gray-200 overflow-hidden max-h-56 overflow-y-auto font-mono text-xs">
          <div className="flex items-center gap-2 px-3 py-1 bg-white border-b border-gray-200 text-gray-400 font-sans font-medium sticky top-0">
            <span className="flex-1">Prefixo</span>
            <span className="w-14 text-right">maxLen</span>
            <span className="w-14">TA</span>
          </div>
          <div className="grid grid-cols-1 gap-y-0.5 p-3">
            {roaList.map((roa) => (
              <div key={`${roa.prefix}-${roa.ta}`} className="flex items-center gap-2">
                <span className={`${text} flex-1`}>{roa.prefix}</span>
                <span className="text-gray-500 w-14 text-right">/{roa.maxLength}</span>
                <span className={`inline-block px-1 rounded font-sans font-medium uppercase leading-4 ${TA_COLORS[roa.ta.toLowerCase()] ?? 'bg-gray-100 text-gray-600'}`}>
                  {roa.ta}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// RPKI / ASPA
// ---------------------------------------------------------------------------

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
                <Link
                  to={`/asn/${asn}`}
                  className="text-primario-700 hover:underline flex-1"
                >
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
          Nenhum AS declarou este AS como provedor
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
                <Link
                  to={`/asn/${customer}`}
                  className="text-v6-700 hover:underline flex-1"
                >
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
