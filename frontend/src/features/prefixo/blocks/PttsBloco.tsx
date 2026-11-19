// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import type { BlocoProps } from '../../entidade/registry'
import type { PrefixoCtx } from '../contexto'

/** PTTs em cujos route servers o prefixo aparece (documento do AS de origem), com o papel do AS em cada um. */
export function PttsBloco({ dados }: BlocoProps<PrefixoCtx>) {
  const { prefix, asn } = dados
  const linhas = Object.entries(asn?.ixp_presence ?? {}).flatMap(([code, p]) =>
    (['v6', 'v4'] as const).flatMap((afi) => {   // D6: IPv6 antes de IPv4
      const x = p[afi]
      return x && (x.prefixes ?? []).includes(prefix) ? [{ code, afi, direto: !!x.direct, origem: !!x.origin }] : []
    }))
  return linhas.length === 0 ? <p className="text-sm text-gray-500">O prefixo não aparece nos route servers dos PTTs coletados.</p> : (
    <table className="w-full text-sm">
      <thead><tr className="text-left text-xs text-gray-400 border-b border-gray-100"><th className="py-1">PTT</th><th>Família</th><th>AS de origem é</th></tr></thead>
      <tbody className="divide-y divide-gray-50">
        {linhas.map((l) => (
          <tr key={`${l.code}-${l.afi}`}>
            <td className="py-1"><Link to={`/ixp/${l.code}`} className="text-primario-600 hover:underline font-mono">{l.code.toUpperCase()}</Link></td>
            <td>IP{l.afi}</td><td className="text-gray-600">{[l.direto && 'peer direto', l.origem && 'originador'].filter(Boolean).join(' e ') || '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
