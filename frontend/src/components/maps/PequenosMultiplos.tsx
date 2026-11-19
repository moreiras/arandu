// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { GradeUfs, METRICAS } from '../../features/estados/CartogramaUfs'
import type { ResumoUf } from '../../types/api'

/**
 * Pequenos múltiplos: vários cartogramas de UF lado a lado, um por indicador **normalizado**, cada um com a própria escala (declarada) ou todos com a
 * mesma (`escalaComum`, só faz sentido para indicadores na mesma unidade). Mostra de relance se o padrão territorial muda de um indicador para outro.
 */
export function PequenosMultiplos({ ufs, metricas, escalaComum = false }: { ufs: ResumoUf[]; metricas: string[]; escalaComum?: boolean }) {
  const lista = metricas.flatMap((id) => METRICAS.filter((m) => m.id === id))
  const porUf = new Map(ufs.map((u) => [u.uf, u]))
  const valoresDe = (m: (typeof lista)[number]) => ufs.map((u) => m.valor(u)).filter((v): v is number => v != null)
  const todos = lista.flatMap(valoresDe)
  return (
    <section aria-label="Pequenos múltiplos por UF" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="pequenos-multiplos">
      {lista.map((m) => {
        const v = valoresDe(m)
        const ref = escalaComum ? todos : v
        return (
          <figure key={m.id} className="rounded-lg border border-gray-200 bg-white p-3">
            <figcaption className="mb-2 text-xs font-medium text-gray-700">{m.rotulo}</figcaption>
            <GradeUfs valores={(uf) => { const u = porUf.get(uf); return u ? m.valor(u) : null }} maximo={ref.length ? Math.max(...ref) : 0} minimo={0} texto={m.texto} rotulo={m.rotulo} pequeno />
            <p className="mt-1 text-center text-xs text-gray-500">de {v.length ? m.texto(Math.min(...v)) : '—'} a {v.length ? m.texto(Math.max(...v)) : '—'}</p>
          </figure>
        )
      })}
    </section>
  )
}
