// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'

export function PeeringDbBloco({ dados }: BlocoProps<AsnCtx>) {
  const { doc } = dados
  return (
    <div>
      <h2 className="text-base font-semibold text-gray-800 mb-2 flex items-center gap-2">
        PeeringDB
        {doc.pdb_registered === false && (
          <span className="text-xs font-normal bg-aviso-100 text-aviso-700 border border-aviso-200 rounded px-2 py-0.5">
            não cadastrado
          </span>
        )}
      </h2>
      {doc.pdb_registered === false ? (
        <p className="text-sm text-gray-500 bg-aviso-50 border border-aviso-200 rounded px-4 py-3">
          Esta rede não possui cadastro no PeeringDB. Redes sem cadastro não aparecem nas buscas de peering e podem ter menos parceiros.
        </p>
      ) : doc.pdb ? (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <tbody className="divide-y divide-gray-50">
              {[
                ['Tipo de rede', doc.pdb.network_type],
                ['Tráfego', doc.pdb.traffic_class],
                ['Proporção', doc.pdb.traffic_ratio],
                ['Política de peering', doc.pdb.peering_policy],
                ['IRR AS-SET', doc.pdb.irr_as_set],
                ['Prefixos declarados IPv4', doc.pdb.declared_prefixes_v4?.toLocaleString('pt-BR')],
                ['Prefixos declarados IPv6', doc.pdb.declared_prefixes_v6?.toLocaleString('pt-BR')],
                ['Website', doc.pdb.website],
              ].filter(([, v]) => v != null && v !== '').map(([label, value]) => (
                <tr key={label as string} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-gray-500 w-48 font-medium text-xs">{label}</td>
                  <td className="px-4 py-2 text-gray-800 text-sm">
                    {label === 'Website' ? (
                      <a href={value as string} target="_blank" rel="noopener noreferrer" className="text-primario-600 hover:underline">
                        {value}
                      </a>
                    ) : String(value)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  )
}
