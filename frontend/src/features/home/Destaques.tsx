// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AccessError, fetchCaminho, queryColecao } from '../../services/api'
import { ProvenienciaCompacta } from '../../components/ui'
import type { FonteEntrada } from '../../components/entidade'
import { useActiveDate } from '../../hooks/useSnapshot'
import { cartaoDe, consultaDoDestaque, DESTAQUES, type Destaque } from './regrasDestaques'
import { SITE } from '../../lib/site'
import { useOrcamentoAvancado } from '../../auth/AuthContext'

interface Resposta { total?: number; items?: unknown[] }

function UmDestaque({ d, fontes }: { d: Destaque; fontes?: FonteEntrada[] | null }) {
  const date = useActiveDate()
  const c = consultaDoDestaque(d)
  const { pronto, esgotado } = useOrcamentoAvancado()
  const q = useQuery({
    queryKey: ['destaque', d.id, date],
    queryFn: (): Promise<Resposta> => (c.tipo === 'query' ? queryColecao<Resposta>(c.colecao, c.corpo, date ?? undefined) : fetchCaminho<Resposta>(c.caminho, { ...c.params, date: date ?? undefined })),
    enabled: !!date && pronto && !esgotado, staleTime: Infinity, gcTime: Infinity, retry: false,
  })
  const total = q.data ? (q.data.total ?? q.data.items?.length ?? 0) : null
  const bloqueado = esgotado || q.error instanceof AccessError
  return (
    <li className="rounded-lg border border-gray-200 border-l-4 border-l-primario-500 bg-primario-50/50 p-4 flex flex-col" data-testid="destaque">
      <p className="text-sm text-gray-700">
        <span className="block text-titulo-2 text-primario-800 tabular-nums" aria-live="polite">
          {total != null ? total.toLocaleString('pt-BR') : q.isLoading ? '…' : '—'}
        </span>
        <span className="font-medium">{d.unidade}</span> {d.frase}
      </p>
      {bloqueado && <p className="mt-1 text-xs text-aviso-700" role="status">O tempo de uso sem login acabou; entre para ver o número.</p>}
      {q.isError && !bloqueado && <p className="mt-1 text-xs text-gray-500" role="status">Não foi possível carregar agora.</p>}
      <Link to={d.to} className="mt-2 text-sm text-primario-700 hover:underline">{d.rotulo} →</Link>
      <ProvenienciaCompacta bloco={{ fontes: cartaoDe(d).fontes }} fontes={fontes} snapshot={date} />
    </li>
  )
}

/** "Destaques do snapshot": perguntas prontas reescritas como um número com uma frase, cada uma levando à lista completa. */
export function Destaques({ fontes }: { fontes?: FonteEntrada[] | null }) {
  return (
    <section aria-labelledby="destaques-titulo">
      <h2 id="destaques-titulo" className="text-titulo-3 text-gray-900">Destaques do snapshot</h2>
      <p className="text-sm text-gray-500 mt-0.5 mb-3">Perguntas que o {SITE.nome} responde a cada snapshot; cada uma abre a lista completa.</p>
      <ul className="grid gap-3 sm:grid-cols-2">
        {DESTAQUES.map((d) => <UmDestaque key={d.id} d={d} fontes={fontes} />)}
      </ul>
    </section>
  )
}
