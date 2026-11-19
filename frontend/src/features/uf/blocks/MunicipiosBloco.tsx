// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import { fmtKm } from '../../../lib/geo'
import type { BlocoProps } from '../../entidade/registry'
import type { UfCtx } from '../contexto'
import { fmt } from '../../municipio/ui'

/** Maiores municípios em acessos (até 15), com o mercado local (operadoras e HHI) e a distância ao PTT. */
export function MunicipiosBloco({ dados }: BlocoProps<UfCtx>) {
  const lista = [...dados.municipios].sort((a, b) => b.acessos - a.acessos).slice(0, 15)
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
          <th className="px-2 py-1">Município</th><th className="px-2 py-1 text-right">Acessos</th><th className="px-2 py-1 text-right">Operadoras</th>
          <th className="px-2 py-1 text-right">HHI</th><th className="px-2 py-1 text-right">PTT mais próximo</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-50">
        {lista.map((m) => (
          <tr key={m.ibge}>
            <td className="px-2 py-1"><Link to={`/municipio/${m.ibge}`} className="text-primario-600 hover:underline">{m.nome}</Link></td>
            <td className="px-2 py-1 text-right tabular-nums">{fmt(m.acessos)}</td>
            <td className="px-2 py-1 text-right tabular-nums">{fmt(m.operadores)}</td>
            <td className="px-2 py-1 text-right tabular-nums">{fmt(m.hhi)}</td>
            <td className="px-2 py-1 text-right tabular-nums">{m.ptt ? `${m.ptt} · ${fmtKm(m.kmPtt)}` : '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
