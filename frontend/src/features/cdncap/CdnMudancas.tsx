// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../../auth/AuthContext'
import { isHistoricalDate } from '../../auth/accessPolicy'
import { ComoLer } from '../../components/ui/ComoLer'
import { EstadoDados } from '../../components/ui/EstadoDados'
import { LinhaProveniencia } from '../../components/ui/Kpi'
import { useSnapshots } from '../../hooks/useSnapshot'
import { fetchCdnMudancas } from '../../services/api'

/**
 * Mudanças na matriz de CDNs entre dois snapshots (PT-28 / CDNS-5.4): quem passou a constar ou deixou de constar como membro de PTT do IX.br,
 * com o catálogo e a cobertura separados pela regra de comparabilidade da API. Diferença observada no cadastro, sem causa nem intenção; ordem neutra.
 */
export function CdnMudancas() {
  const { requireLogin } = useAuth()
  const datas = useSnapshots().data?.snapshots ?? []
  const [a, setA] = useState('')
  const [b, setB] = useState('')
  const A = a || datas[datas.length - 2] || '', B = b || datas[datas.length - 1] || ''
  const escolher = (set: (v: string) => void) => (e: React.ChangeEvent<HTMLSelectElement>) => {
    if (isHistoricalDate(e.target.value, datas) && !requireLogin('historico')) return
    set(e.target.value)
  }
  const q = useQuery({ queryKey: ['cdn-mudancas', A, B], queryFn: () => fetchCdnMudancas(A, B), enabled: !!A && !!B && A < B, staleTime: Infinity, retry: false })
  const r = q.data
  const cat = r?.catalogo
  return (
    <section className="space-y-3 border-t border-gray-200 pt-4" aria-label="Mudanças entre snapshots" data-testid="cdn-mudancas">
      <h2 className="text-titulo-3 text-gray-800">Mudanças entre snapshots</h2>
      <p className="text-sm text-gray-600">Quem passou a constar ou deixou de constar na lista de membros de um PTT do IX.br entre duas datas. É o que as duas fotografias do cadastro mostram, sem causa atribuída.</p>
      <div className="flex flex-wrap gap-4 text-sm">
        {([['De', A, setA], ['Para', B, setB]] as const).map(([rotulo, valor, set]) => (
          <label key={rotulo} className="flex flex-col gap-0.5">
            <span className="text-xs text-gray-500">{rotulo}</span>
            <select value={valor} onChange={escolher(set)} className="border border-gray-200 rounded px-2 py-1 bg-white">
              {datas.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
        ))}
      </div>
      {A && B && A >= B && <p className="text-sm text-gray-500">Escolha uma data inicial anterior à final.</p>}
      {q.isLoading && <p className="text-sm text-gray-400" role="status">Carregando…</p>}
      {q.isError && <EstadoDados erro={q.error} oQue="as mudanças da matriz de CDNs" mensagem="Não há dados de presença de CDNs em uma das datas escolhidas." aoTentarDeNovo={() => void q.refetch()} />}
      {r && (
        <div className="space-y-3 text-sm">
          <p data-testid="cdn-mudancas-resumo">
            Entre {r.a} e {r.b}: {r.totais.entradas} {r.totais.entradas === 1 ? 'entrada' : 'entradas'} e {r.totais.saidas} {r.totais.saidas === 1 ? 'saída' : 'saídas'} na lista de membros
            {r.totais.nao_comparaveis > 0 && `; ${r.totais.nao_comparaveis} não ${r.totais.nao_comparaveis === 1 ? 'comparável' : 'comparáveis'}`}.
          </p>
          {(r.comparabilidade.avisos ?? []).map((av) => <p key={av.codigo} className="text-xs text-aviso-700">Aviso: {av.texto}{av.detalhe ? ` (${av.detalhe})` : ''}.</p>)}
          <div className="grid gap-4 md:grid-cols-2">
            {([['Passou a constar como membro', r.entradas], ['Deixou de constar como membro', r.saidas]] as const).map(([titulo, itens]) => (
              <div key={titulo}>
                <h3 className="font-medium text-gray-800">{titulo} ({itens.length})</h3>
                {itens.length === 0
                  ? <p className="text-gray-500">Nenhum no período.</p>
                  : <ul className="mt-1 space-y-0.5">{itens.map((i) => <li key={`${i.cdn}-${i.ptt}`}>{i.cdn} em <span className="font-mono">{i.ptt}</span></li>)}</ul>}
              </div>
            ))}
          </div>
          {r.nao_comparaveis.length > 0 && (
            <div data-testid="cdn-nao-comparaveis">
              <h3 className="font-medium text-gray-800">Fora da comparação ({r.nao_comparaveis.length})</h3>
              <ul className="mt-1 space-y-0.5">
                {r.nao_comparaveis.map((i) => (
                  <li key={`${i.cdn}-${i.ptt}`}>{i.cdn} em <span className="font-mono">{i.ptt}</span>: {i.detalhes.map((d) => d.texto).join('; ')}</li>
                ))}
              </ul>
            </div>
          )}
          {cat && (cat.cdns_incluidas.length > 0 || cat.cdns_retiradas.length > 0 || cat.asns_alterados.length > 0) && (
            <div data-testid="cdn-catalogo">
              <h3 className="font-medium text-gray-800">Mudanças na lista curada de CDNs (não são mudança de rede)</h3>
              <ul className="mt-1 space-y-0.5">
                {cat.cdns_incluidas.map((n) => <li key={`i${n}`}>{n}: incluída na lista curada</li>)}
                {cat.cdns_retiradas.map((n) => <li key={`r${n}`}>{n}: retirada da lista curada</li>)}
                {cat.asns_alterados.map((x) => (
                  <li key={`a${x.cdn}`}>{x.cdn}: {x.asns_incluidos.length > 0 && `ASNs incluídos ${x.asns_incluidos.map((n) => `AS${n}`).join(', ')}`}{x.asns_incluidos.length > 0 && x.asns_retirados.length > 0 && '; '}{x.asns_retirados.length > 0 && `ASNs retirados ${x.asns_retirados.map((n) => `AS${n}`).join(', ')}`}</li>
                ))}
              </ul>
            </div>
          )}
          <LinhaProveniencia selo={r.selo} fonte={r.fonte} dataRef={r.b} />
          <ComoLer>
            <p>{r.limites}</p>
            {r.comparabilidade.texto.map((t, i) => <p key={i}>{t}</p>)}
          </ComoLer>
        </div>
      )}
    </section>
  )
}
