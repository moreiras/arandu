// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { STFCRecord, SEACRecord } from '../../types/api'

/**
 * Seção genérica para outorgas sem equivalente de acessos declarados ao SICI
 * (STFC, SeAC) — só a lista de outorgas do CNPJ (pode haver várias, uma por
 * endereço/fistel), sem KPIs de acessos, mapa ou série.
 */
export function OutorgaListSection({
  titulo, fonte, outorgas,
}: {
  titulo: string
  fonte: string
  outorgas: (STFCRecord | SEACRecord)[]
}) {
  return (
    <div>
      <h2 className="text-base font-semibold text-gray-800 mb-1">{titulo}</h2>
      <p className="text-xs text-gray-400 mb-2">
        {outorgas.length} outorga{outorgas.length !== 1 ? 's' : ''} · sem acessos declarados
        ao SICI para este serviço
      </p>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-400 bg-gray-50 border-b border-gray-100">
              <th className="px-4 py-2">Endereço</th>
              <th className="px-4 py-2 w-36">Município / UF</th>
              <th className="px-4 py-2 w-28">Data Outorga</th>
              <th className="px-4 py-2 w-16">Sit.</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {outorgas.map((o, i) => (
              <tr key={`${o.cnpj}-${i}`} className="hover:bg-gray-50">
                <td className="px-4 py-2 text-xs text-gray-500">
                  {o.logradouro
                    ? <>{o.logradouro}{o.numero ? `, ${o.numero}` : ''}{o.bairro ? ` — ${o.bairro}` : ''}{o.cep ? ` · CEP ${o.cep}` : ''}</>
                    : '—'}
                </td>
                <td className="px-4 py-2 text-gray-600 text-sm">
                  {o.municipio}{o.uf ? `/${o.uf}` : ''}
                </td>
                <td className="px-4 py-2 text-xs text-gray-500">{o.data_outorga ?? '—'}</td>
                <td className="px-4 py-2">
                  {o.situacao && (
                    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                      o.situacao === 'ATI' ? 'bg-ok-100 text-ok-800' :
                      o.situacao === 'EXT' ? 'bg-perigo-100 text-perigo-700' :
                      'bg-aviso-100 text-aviso-800'
                    }`}>{o.situacao}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="px-4 py-2 border-t border-gray-50 text-xs text-gray-400">
          Fonte: Anatel — dados abertos de outorgas {fonte}
        </div>
      </div>
    </div>
  )
}
