// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../../components/layout/LinkDatado'
import { fmtKm } from '../../../lib/geo'
import type { BlocoProps } from '../../entidade/registry'
import { RAIO_PTT_PROXIMO_KM, type MunicipioCtx } from '../contexto'

/** PTTs mais próximos (linha reta do centróide do município); o mapa tem as camadas de infraestrutura física. */
export function InfraBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const maximo = Math.max(RAIO_PTT_PROXIMO_KM, ...dados.proximos.map((p) => p.km))
  return (
    <div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
            <th className="px-2 py-1">PTT</th><th className="px-2 py-1 w-1/2">Distância (a marca é {RAIO_PTT_PROXIMO_KM} km)</th><th className="px-2 py-1 text-right"> </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {dados.proximos.map((p) => (
            <tr key={`${p.codigo}-${p.lonlat.join()}`}>
              <td className="px-2 py-1"><Link to={`/ixp/${p.codigo}`} className="text-primario-600 hover:underline">{p.nome}</Link></td>
              <td className="px-2 py-1">
                <div className="relative h-2 rounded bg-gray-100" aria-hidden>
                  <div className={`h-2 rounded ${p.km <= RAIO_PTT_PROXIMO_KM ? 'bg-primario-500' : 'bg-gray-400'}`} style={{ width: `${(100 * p.km) / maximo}%` }} />
                  <div className="absolute top-[-2px] h-3 w-px bg-gray-500" style={{ left: `${(100 * RAIO_PTT_PROXIMO_KM) / maximo}%` }} />
                </div>
              </td>
              <td className="px-2 py-1 text-right tabular-nums">{fmtKm(p.km)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-gray-500">
        Distância em linha reta até o centróide do município{dados.conjunto ? ' central (não do conjunto)' : ''} — não é o trajeto de fibra. Linhas de transmissão, cabos submarinos e rodovias estão no{' '}
        <Link to="/mapa" className="text-primario-600 hover:underline">mapa</Link>.
      </p>
    </div>
  )
}
