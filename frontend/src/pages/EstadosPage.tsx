// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../components/layout/LinkDatado'
import { CartogramaUfs } from '../features/estados/CartogramaUfs'
import { MapaSobDemanda } from '../features/estados/MapaSobDemanda'
import { useUfs } from '../hooks/entidades'
import { EstadoDados } from '../components/ui/EstadoDados'
import { REGIOES, nomeUf } from '../lib/ufs'
import type { ResumoUf } from '../types/api'

const fmt = (n: number) => n.toLocaleString('pt-BR')

/** PTTs da UF no snapshot; quando parte deles não teve coleta, diz quantos tiveram. Zero é "nenhum PTT do IX.br", nunca "sem PTT". */
function textoPtts(u: ResumoUf): string {
  if (!u.ptts) return 'nenhum PTT do IX.br na UF'
  const base = `${u.ptts} ${u.ptts === 1 ? 'PTT' : 'PTTs'}`
  return u.ptts_com_coleta != null && u.ptts_com_coleta < u.ptts ? `${base} (${u.ptts_com_coleta} com coleta neste snapshot)` : base
}

/**
 * `/estados`: o cartograma das 27 UFs e a lista por região, cada UF levando a `/uf/<sigla>`.
 * Uma chamada: `/ufs` traz PTTs, acessos fixos, % de fibra e usuários estimados de todas — e é aberta a qualquer visitante.
 */
export function EstadosPage() {
  const q = useUfs()
  const ufs = q.data?.items ?? []
  const porUf = new Map(ufs.map((u) => [u.uf, u]))
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Estados</h1>
        <p className="text-sm text-gray-500 mt-1">Escolha uma UF para ver seus PTTs, os maiores municípios em banda larga, os que ficam longe de um PTT e as operadoras sediadas nela.</p>
      </div>
      {q.isError && <EstadoDados erro={q.error} oQue="os números por UF" mensagem="Os números por UF não estão publicados neste snapshot." aoTentarDeNovo={() => void q.refetch()} />}
      {ufs.length > 0 && <CartogramaUfs ufs={ufs} />}
      <MapaSobDemanda />
      {REGIOES.map((r) => (
        <section key={r.id} aria-labelledby={`regiao-${r.id}`}>
          <h2 id={`regiao-${r.id}`} className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-2">{r.nome}</h2>
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {[...r.ufs].sort((a, b) => nomeUf(a).localeCompare(nomeUf(b), 'pt-BR')).map((uf) => {
              const u = porUf.get(uf)
              return (
                <li key={uf}>
                  <Link to={`/uf/${uf}`} className="block bg-white rounded-lg border border-gray-200 px-4 py-3 hover:border-primario-300 hover:shadow-sm transition">
                    <span className="flex items-baseline justify-between gap-2">
                      <span className="font-medium text-gray-800">{nomeUf(uf)}</span>
                      <span className="text-xs font-mono text-gray-400">{uf}</span>
                    </span>
                    <span className="block text-xs text-gray-500">
                      {q.isLoading ? 'Carregando…' : q.isError || !u ? '—' : textoPtts(u)}
                    </span>
                    {u && (
                      <span className="block mt-1.5 text-xs text-gray-500 tabular-nums">
                        {u.acessos == null ? 'sem SICI neste snapshot' : `${fmt(u.acessos)} acessos fixos`} · {fmt(u.usuarios)} usuários est.
                        {u.fibra_pct != null && (
                          <span className="mt-1 flex items-center gap-1.5">
                            <span className="flex-1 h-1.5 rounded-full bg-gray-100 overflow-hidden" aria-hidden><span className="block h-full bg-mercado-500" style={{ width: `${u.fibra_pct}%` }} /></span>
                            <span>{u.fibra_pct.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}% fibra</span>
                          </span>
                        )}
                      </span>
                    )}
                  </Link>
                </li>
              )
            })}
          </ul>
        </section>
      ))}
    </div>
  )
}
