// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../../components/layout/LinkDatado'
import { fmtKm } from '../../../lib/geo'
import type { BlocoProps } from '../../entidade/registry'
import type { UfCtx } from '../contexto'
import { fmt } from '../../municipio/ui'
import { RAIO_SEM_PTT_KM } from '../contexto'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'
import { useOrdenacao } from '../../../lib/ordenacao'

/** Municípios com banda larga declarada a mais de 100 km do PTT mais próximo, do maior para o menor em acessos (até 20). */
export function SemPttBloco({ dados }: BlocoProps<UfCtx>) {
  const filtrados = dados.municipios.filter((m) => m.kmPtt != null && m.kmPtt > RAIO_SEM_PTT_KM).sort((a, b) => b.acessos - a.acessos)
  // Ordena-se a lista inteira e só depois se corta nos 20 primeiros.
  const { ordenados: lista, props } = useOrdenacao(filtrados, { nome: (m) => m.nome, ptt: (m) => m.ptt, km: (m) => m.kmPtt, acessos: (m) => m.acessos })
  return (
    <div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
            <ThOrdenavel {...props('nome')} className="px-2 py-1">Município</ThOrdenavel><ThOrdenavel {...props('ptt')} className="px-2 py-1">PTT mais próximo</ThOrdenavel>
            <ThOrdenavel {...props('km')} alinhar="right" className="px-2 py-1 text-right">Distância</ThOrdenavel><ThOrdenavel {...props('acessos')} alinhar="right" className="px-2 py-1 text-right">Acessos</ThOrdenavel>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {lista.slice(0, 20).map((m) => (
            <tr key={m.ibge}>
              <td className="px-2 py-1"><Link to={`/municipio/${m.ibge}`} className="text-primario-600 hover:underline">{m.nome}</Link></td>
              <td className="px-2 py-1 text-gray-600">{m.ptt ?? '—'}</td>
              <td className="px-2 py-1 text-right tabular-nums">{fmtKm(m.kmPtt)}</td>
              <td className="px-2 py-1 text-right tabular-nums">{fmt(m.acessos)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {lista.length > 20 && <p className="mt-1 text-xs text-gray-400">e mais {lista.length - 20} municípios.</p>}
      <p className="mt-2 text-xs text-gray-500">Distância em linha reta do centróide do município até o PIX mais próximo; não é o trajeto de fibra.</p>
    </div>
  )
}
