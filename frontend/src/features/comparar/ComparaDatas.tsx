// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchDiffSnapshots, fetchSnapshots } from '../../services/api'
import { useAuth } from '../../auth/AuthContext'
import { isHistoricalDate } from '../../auth/accessPolicy'
import { ROTULO_METRICA, TIPOS_DA_PAGINA } from '../historico/rotulos'

const fmt = (n: number) => n.toLocaleString('pt-BR')
const ROTULO: Record<string, string> = { ...ROTULO_METRICA, n_asns: 'ASNs brasileiros (por UF da sede)', ptts_coletados: 'PTTs coletados por inteiro', ptts_membros: 'Membros cadastrados nos PTTs' }

/**
 * Comparar duas datas: a diferença agregada do Brasil entre dois snapshots com histórico (`/snapshots/diff`) e o que mudou entre eles.
 * Totais por UF somam ASNs com sede na UF; usuários são estimativas da APNIC. As datas históricas (fora das 2 atuais) pedem login, como o seletor de snapshot.
 */
export function ComparaDatas() {
  const { requireLogin } = useAuth()
  const { data } = useQuery({ queryKey: ['snapshots'], queryFn: fetchSnapshots, staleTime: Infinity, gcTime: Infinity })
  const datas = data?.snapshots ?? []
  const [a, setA] = useState('')
  const [b, setB] = useState('')
  const A = a || datas[datas.length - 2] || '', B = b || datas[datas.length - 1] || ''
  const escolher = (set: (v: string) => void) => (e: React.ChangeEvent<HTMLSelectElement>) => {
    if (isHistoricalDate(e.target.value, datas) && !requireLogin('historico')) return
    set(e.target.value)
  }
  const diff = useQuery({ queryKey: ['diff', A, B], queryFn: () => fetchDiffSnapshots(A, B), enabled: !!A && !!B && A !== B, staleTime: Infinity, retry: false })
  const eventos = Object.entries(diff.data?.eventos.por_tipo ?? {}).filter(([t]) => TIPOS_DA_PAGINA.includes(t))
  return (
    <div className="space-y-5">
      <p className="text-sm text-gray-500">Compare os totais do Brasil em duas datas e veja quantas mudanças foram observadas entre elas. Só há comparação para datas com histórico guardado (desde outubro de 2026).</p>
      <div className="flex flex-wrap gap-4 text-sm">
        {([['Data A', A, setA], ['Data B', B, setB]] as const).map(([rotulo, valor, set]) => (
          <label key={rotulo} className="flex flex-col gap-0.5">
            <span className="text-xs text-gray-500">{rotulo}</span>
            <select value={valor} onChange={escolher(set)} className="border border-gray-200 rounded px-2 py-1 bg-white">
              {datas.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
        ))}
      </div>
      {A === B && <p className="text-sm text-gray-500">Escolha duas datas diferentes.</p>}
      {diff.isLoading && <p className="text-sm text-gray-400" role="status">Carregando…</p>}
      {diff.isError && <p className="text-sm text-gray-500" role="status">Não há histórico guardado em uma das datas escolhidas.</p>}
      {diff.data && (
        <>
          <table className="text-sm bg-white border border-gray-200 rounded-lg">
            <thead><tr className="text-left text-xs text-gray-500"><th className="px-3 py-2">Indicador</th><th className="px-3 py-2 text-right">{diff.data.a}</th><th className="px-3 py-2 text-right">{diff.data.b}</th><th className="px-3 py-2 text-right">Variação</th></tr></thead>
            <tbody>
              {Object.entries(diff.data.totais).map(([k, v]) => (
                <tr key={k} className="border-t border-gray-100">
                  <td className="px-3 py-1.5">{ROTULO[k] ?? k}</td>
                  <td className="px-3 py-1.5 text-right tabular-nums">{fmt(v.a)}</td>
                  <td className="px-3 py-1.5 text-right tabular-nums">{fmt(v.b)}</td>
                  <td className="px-3 py-1.5 text-right tabular-nums">{v.variacao > 0 ? '+' : ''}{fmt(v.variacao)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-xs text-gray-500">{diff.data.nota}</p>
          {eventos.length > 0 && (
            <div>
              <h2 className="text-sm font-medium mb-1">Mudanças observadas entre {diff.data.eventos.entre[0]} e {diff.data.eventos.entre[1]}</h2>
              <ul className="text-sm space-y-0.5">
                {eventos.map(([t, c]) => <li key={t}>{t.replace(/_/g, ' ')}: {c.confirmado} confirmadas{c.pendente > 0 && `, ${c.pendente} em confirmação`}</li>)}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  )
}
