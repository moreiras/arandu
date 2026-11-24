// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'

const n = (v: number | null | undefined) => (v == null ? null : v.toLocaleString('pt-BR'))

/** Prefixos declarados no PeeringDB ao lado dos vistos na tabela global (o declarado é um teto configurado, não o anunciado). */
function prefixos(declarado: number | undefined, observado: number | null | undefined): string | null {
  if (declarado == null) return null
  return `${n(declarado)} declarados${observado != null ? ` · ${n(observado)} na tabela global` : ''}`
}

/** Cadastro do AS no PeeringDB: campos como a API os entrega (`info_*`, `policy_general`, do `/api/net`), autodeclarados. */
export function PeeringDbBloco({ dados }: BlocoProps<AsnCtx>) {
  const { doc } = dados
  const linhas = doc.pdb ? ([
    ['Tipo de rede', doc.pdb.info_type],
    ['Tráfego', doc.pdb.info_traffic],
    ['Proporção', doc.pdb.info_ratio],
    ['Política de peering', doc.pdb.policy_general],
    ['IRR AS-SET', doc.pdb.irr_as_set],
    ['Prefixos IPv6', prefixos(doc.pdb.info_prefixes6, doc.global_prefixes_v6_count)],
    ['Prefixos IPv4', prefixos(doc.pdb.info_prefixes4, doc.global_prefixes_v4_count)],
    ['Website', doc.pdb.website],
  ] as const).filter(([, v]) => v != null && v !== '') : []
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
        linhas.length > 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <table className="w-full text-sm" data-testid="peeringdb-cadastro">
              <tbody className="divide-y divide-gray-50">
                {linhas.map(([label, value]) => (
                  <tr key={label} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-gray-500 w-48 font-medium text-xs">{label}</td>
                    <td className="px-4 py-2 text-gray-800 text-sm">
                      {label === 'Website' ? (
                        <a href={String(value)} target="_blank" rel="noopener noreferrer" className="text-primario-600 hover:underline">
                          {value}
                        </a>
                      ) : String(value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <p className="text-sm text-gray-500">Cadastrado no PeeringDB, sem tipo, política nem prefixos preenchidos.</p>
      ) : null}
    </div>
  )
}
