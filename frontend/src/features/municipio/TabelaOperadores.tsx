// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../components/layout/LinkDatado'
import type { SiciOperador } from '../../types/api'
import { fmt, fmtCnpj } from './ui'
import { useOrdenacao } from '../../lib/ordenacao'
import { ThOrdenavel } from '../../components/ui/ThOrdenavel'

/** Quem atende o município, com ASN e participação (a tabela da página de antes; serve ao fixo e ao móvel). */
export function TabelaOperadores({ titulo, operadores }: { titulo: string; operadores: SiciOperador[] }) {
  const { ordenados, props } = useOrdenacao(operadores, {
    empresa: (o) => o.empresa || fmtCnpj(o.cnpj), asn: { valor: (o) => o.asns[0], primeiro: 'asc' }, acessos: (o) => o.acessos, share: (o) => o.share,
  })
  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="px-4 py-2 text-sm font-semibold text-gray-700 border-b border-gray-100">{titulo}</div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-400 bg-gray-50 border-b border-gray-100">
            <th scope="col" className="px-4 py-2 w-8 text-right">#</th>
            <ThOrdenavel {...props('empresa')} className="px-4 py-2">Operadora</ThOrdenavel>
            <ThOrdenavel {...props('asn')} className="px-4 py-2 w-40">ASN</ThOrdenavel>
            <ThOrdenavel {...props('acessos')} alinhar="right" className="px-4 py-2 w-28 text-right">Acessos</ThOrdenavel>
            <ThOrdenavel {...props('share')} alinhar="right" className="px-4 py-2 w-32 text-right">Participação</ThOrdenavel>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {ordenados.map((o, i) => (
            <tr key={o.cnpj} className="hover:bg-gray-50">
              <td className="px-4 py-1.5 text-right text-gray-400 tabular-nums">{i + 1}</td>
              <td className="px-4 py-1.5">
                <Link to={`/operadora/${o.cnpj}`} className="text-primario-600 hover:underline font-medium">{o.empresa || fmtCnpj(o.cnpj)}</Link>
                <div className="text-xs text-gray-400 font-mono">{fmtCnpj(o.cnpj)}</div>
              </td>
              <td className="px-4 py-1.5">
                {o.asns.length ? (
                  <div className="flex flex-wrap gap-1">
                    {o.asns.slice(0, 3).map((a) => (
                      <Link key={a} to={`/asn/${a}`} className="text-xs px-1.5 py-0.5 rounded bg-primario-50 text-primario-700 border border-primario-100">AS{a}</Link>
                    ))}
                    {o.asns.length > 3 && <span className="text-xs text-gray-400">+{o.asns.length - 3}</span>}
                  </div>
                ) : <span className="text-xs text-gray-300">—</span>}
              </td>
              <td className="px-4 py-1.5 text-right tabular-nums">{fmt(o.acessos)}</td>
              <td className="px-4 py-1.5 text-right">
                <div className="flex items-center gap-2 justify-end">
                  <span className="w-16 h-2 bg-gray-100 rounded-sm overflow-hidden"><span className="block h-full bg-primario-500/70" style={{ width: `${o.share}%` }} /></span>
                  <span className="w-14 tabular-nums text-gray-600">{o.share.toLocaleString('pt-BR')}%</span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
