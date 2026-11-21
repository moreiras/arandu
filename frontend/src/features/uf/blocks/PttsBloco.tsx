// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import type { BlocoProps } from '../../entidade/registry'
import type { UfCtx } from '../contexto'
import { fmt } from '../../municipio/ui'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'
import { useOrdenacao } from '../../../lib/ordenacao'

export function PttsBloco({ dados }: BlocoProps<UfCtx>) {
  const { ordenados, props } = useOrdenacao(dados.ixps, {
    code: (i) => i.code,
    cidade: (i) => i.name,
    diretos: (i) => i.asn_direct_union_count,
    participantes: (i) => i.ixbr_members_count,
  })
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
          <ThOrdenavel {...props('code')} className="px-2 py-1">PTT</ThOrdenavel><ThOrdenavel {...props('cidade')} className="px-2 py-1">Cidade</ThOrdenavel>
          <ThOrdenavel {...props('diretos')} alinhar="right" className="px-2 py-1 text-right">ASNs diretos</ThOrdenavel><ThOrdenavel {...props('participantes')} alinhar="right" className="px-2 py-1 text-right">Participantes</ThOrdenavel>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-50">
        {ordenados.map((i) => (
          <tr key={i.code}>
            <td className="px-2 py-1"><Link to={`/ixp/${i.code}`} className="text-primario-600 hover:underline font-mono">{i.code.toUpperCase()}</Link></td>
            <td className="px-2 py-1 text-gray-700">{i.name}</td>
            <td className="px-2 py-1 text-right tabular-nums">{fmt(i.asn_direct_union_count)}</td>
            <td className="px-2 py-1 text-right tabular-nums">{fmt(i.ixbr_members_count)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
