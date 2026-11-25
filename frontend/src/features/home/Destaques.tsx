// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchDestaquesHome } from '../../services/api'
import { ProvenienciaCompacta } from '../../components/ui'
import type { FonteEntrada } from '../../components/entidade'
import { useActiveDate } from '../../hooks/useSnapshot'
import { cartaoDe, DESTAQUES, type Destaque } from './regrasDestaques'
import { SITE } from '../../lib/site'

/** Os totais dos destaques e o "O que mudou" numa chamada só (`/brasil/destaques`: rota fixa e aberta, não gasta o orçamento anônimo, D9). */
export function useDestaquesHome() {
  const date = useActiveDate()
  return useQuery({ queryKey: ['destaques-home', date], queryFn: () => fetchDestaquesHome(date ?? undefined), enabled: !!date, staleTime: Infinity, gcTime: Infinity, retry: false })
}

function UmDestaque({ d, fontes, q }: { d: Destaque; fontes?: FonteEntrada[] | null; q: ReturnType<typeof useDestaquesHome> }) {
  const date = useActiveDate()
  const total = q.data?.destaques?.[d.id]?.total ?? null
  return (
    <li className="rounded-lg border border-gray-200 border-l-4 border-l-primario-500 bg-primario-50/50 p-4 flex flex-col" data-testid="destaque">
      <p className="text-sm text-gray-700">
        <span className="block text-titulo-2 text-primario-800 tabular-nums" aria-live="polite">
          {total != null ? total.toLocaleString('pt-BR') : q.isLoading ? '…' : '—'}
        </span>
        <span className="font-medium">{d.unidade}</span> {d.frase}
      </p>
      {q.isError && <p className="mt-1 text-xs text-gray-500" role="status">Não foi possível carregar agora.</p>}
      <Link to={d.to} className="mt-2 text-sm text-primario-700 hover:underline">{d.rotulo} →</Link>
      <ProvenienciaCompacta bloco={{ fontes: cartaoDe(d).fontes }} fontes={fontes} snapshot={date} />
    </li>
  )
}

/** "Destaques do snapshot": perguntas prontas reescritas como um número com uma frase, cada uma levando à lista completa. */
export function Destaques({ fontes }: { fontes?: FonteEntrada[] | null }) {
  const q = useDestaquesHome()
  return (
    <section aria-labelledby="destaques-titulo">
      <h2 id="destaques-titulo" className="text-titulo-3 text-gray-900">Destaques do snapshot</h2>
      <p className="text-sm text-gray-500 mt-0.5 mb-3">Perguntas que o {SITE.nome} responde a cada snapshot; cada uma abre a lista completa.</p>
      <ul className="grid gap-3 sm:grid-cols-2">
        {DESTAQUES.map((d) => <UmDestaque key={d.id} d={d} fontes={fontes} q={q} />)}
      </ul>
    </section>
  )
}
