// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import type { BlocoProps } from '../../entidade/registry'
import type { UfCtx } from '../contexto'
import { fmt, fmtCnpj } from '../../municipio/ui'

export function OperadorasBloco({ dados }: BlocoProps<UfCtx>) {
  return (
    <div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
            <th className="px-2 py-1">Operadora</th><th className="px-2 py-1 text-right">Acessos</th><th className="px-2 py-1 text-right">Municípios</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {dados.operadoras.map((o) => (
            <tr key={o.cnpj}>
              <td className="px-2 py-1"><Link to={`/operadora/${o.cnpj}`} className="text-primario-600 hover:underline">{o.empresa || o.razao_social}</Link>
                <div className="text-xs text-gray-400 font-mono">{fmtCnpj(o.cnpj)}</div></td>
              <td className="px-2 py-1 text-right tabular-nums">{fmt(o.acessos)}</td>
              <td className="px-2 py-1 text-right tabular-nums">{fmt(o.municipios)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-gray-500">Operadoras com sede na UF; os acessos são os declarados em todo o país (não só na UF). {dados.operadorasTotal > dados.operadoras.length ? `Mostrando as ${dados.operadoras.length} maiores de ${fmt(dados.operadorasTotal)}.` : ''}</p>
    </div>
  )
}
