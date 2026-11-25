// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { MoasEntry, MoasResumo } from '../../types/routingAnalysis'
import { Tip, SortIcon, type SortDir } from './BgpShared'
import { ordenar } from '../../lib/ordenacao'

interface Props {
  data: MoasEntry[]
  resumo: MoasResumo
  date?: string
}

type SortKey = 'prefix' | 'afi' | 'origens' | 'menos_coletores'
type AfiFiltro = 'all' | 'v6' | 'v4'

function fmt(n: number) { return n.toLocaleString('pt-BR') }

/** Menor número de coletores entre as origens: uma origem vista por poucos coletores é visão de poucos pontos de observação. */
function menosColetores(r: MoasEntry): number {
  return Math.min(...r.origens.map((o) => o.coletores))
}

/**
 * Prefixos brasileiros com mais de um AS de origem observado (fato, sem causa). A lista vazia só chega aqui com a coleta capaz
 * (`moas_resumo` presente): é "nenhum observado", com o número de coletores; o "não medido" fica com quem chama.
 */
export function MoasTable({ data, resumo, date }: Props) {
  const [afi, setAfi] = useState<AfiFiltro>('all')
  const [page, setPage] = useState(0)
  const [sortKey, setSortKey] = useState<SortKey>('afi')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const PAGE = 20

  function handleSort(key: SortKey) {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortKey(key); setSortDir(key === 'origens' ? 'desc' : 'asc') }
    setPage(0)
  }

  const filtradas = useMemo(() => {
    const rows = data.filter((r) => afi === 'all' || r.afi === afi)
    const valor = (r: MoasEntry): string | number => {
      switch (sortKey) {
        case 'prefix': return r.prefix
        case 'afi': return r.afi === 'v6' ? 0 : 1                    // IPv6 antes de IPv4
        case 'origens': return r.origens.length
        case 'menos_coletores': return menosColetores(r)
      }
    }
    return ordenar(rows, valor, sortDir)
  }, [data, afi, sortKey, sortDir])

  const visiveis = filtradas.slice(page * PAGE, (page + 1) * PAGE)
  const q = date ? `?date=${date}` : ''

  function SortTh({ k, label, right, tooltip }: { k: SortKey; label: string; right?: boolean; tooltip?: string }) {
    const active = sortKey === k
    return (
      <th scope="col" aria-sort={active ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
        className={['text-xs font-medium pb-1.5 px-1 whitespace-nowrap', right ? 'text-right' : 'text-left', active ? 'text-primario-600' : 'text-gray-500'].join(' ')}>
        <span className={`inline-flex items-center gap-0.5${right ? ' justify-end' : ''}`}>
          <button type="button" onClick={() => handleSort(k)} className="hover:text-gray-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario-500">
            {label}<SortIcon active={active} dir={sortDir} />
          </button>
          {tooltip && <Tip text={tooltip} />}
        </span>
      </th>
    )
  }

  const contagem = (['v6', 'v4'] as const).map((a) => {
    const p = resumo.prefixos[a]
    const n = resumo.coletores[a]?.length ?? 0
    return p
      ? `${a === 'v6' ? 'IPv6' : 'IPv4'}: ${fmt(p.br)} brasileiros de ${fmt(p.global)} na tabela, entre ${fmt(n)} coletores`
      : `${a === 'v6' ? 'IPv6' : 'IPv4'}: não medido neste snapshot`
  })

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-start justify-between mb-3 flex-wrap gap-2">
        <div>
          <h3 className="text-sm font-medium text-gray-700">Prefixos brasileiros com mais de uma origem observada</h3>
          <p className="text-xs text-gray-500 mt-0.5" data-testid="moas-contagem">{contagem.join(' · ')}</p>
        </div>
        <div className="flex gap-1" role="group" aria-label="Família de endereços">
          {(['all', 'v6', 'v4'] as const).map((a) => (
            <button key={a} type="button" aria-pressed={afi === a} onClick={() => { setAfi(a); setPage(0) }}
              className={`text-xs px-2 py-0.5 rounded ${afi === a ? 'bg-primario-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
              {a === 'all' ? 'Todos' : a === 'v6' ? 'IPv6' : 'IPv4'}
            </button>
          ))}
        </div>
      </div>

      {data.length === 0 ? (
        <p className="text-sm text-gray-600" data-testid="moas-vazio">
          Nenhum MOAS observado neste snapshot entre os prefixos brasileiros: nenhum prefixo em bloco do Registro.br apareceu com mais de um AS de origem nos coletores usados.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px]">
            <caption className="sr-only">Prefixos brasileiros com mais de um AS de origem observado, com o número de coletores que viram cada origem</caption>
            <thead>
              <tr className="border-b border-gray-200">
                <SortTh k="prefix" label="Prefixo" tooltip="Prefixo contido em bloco alocado pelo Registro.br, observado com mais de um AS de origem." />
                <SortTh k="afi" label="Família" />
                <SortTh k="origens" label="Origens" right tooltip="ASNs de origem distintos (último AS do AS_PATH) observados para o prefixo." />
                <SortTh k="menos_coletores" label="Coletores por origem" tooltip="Em quantos coletores algum ponto de observação viu cada origem. Origem vista por poucos coletores pode ser visão de poucos pontos de observação." />
              </tr>
            </thead>
            <tbody>
              {visiveis.map((r) => (
                <tr key={r.prefix} className="border-t border-gray-100">
                  <th scope="row" className="py-1.5 px-1 text-xs font-mono font-normal text-left">
                    <Link to={`/prefixo/${r.prefix}${q}`} className="text-primario-600 hover:underline">{r.prefix}</Link>
                  </th>
                  <td className="py-1.5 px-1 text-xs text-gray-500">{r.afi === 'v6' ? 'IPv6' : 'IPv4'}</td>
                  <td className="py-1.5 px-1 text-xs text-right">{fmt(r.origens.length)}</td>
                  <td className="py-1.5 px-1 text-xs">
                    <ul className="flex flex-wrap gap-x-3 gap-y-0.5">
                      {r.origens.map((o) => (
                        <li key={o.asn}>
                          <Link to={`/asn/${o.asn}${q}`} className="font-mono text-primario-600 hover:underline">AS{o.asn}</Link>
                          <span className="text-gray-500"> {fmt(o.coletores)} {o.coletores === 1 ? 'coletor' : 'coletores'}</span>
                          {o.asn_br && <span className="text-gray-400"> (Registro.br)</span>}
                        </li>
                      ))}
                    </ul>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {resumo.lista_truncada && (
        <p className="text-xs text-aviso-700 mt-2">Lista cortada em {fmt(resumo.lista_limite)} prefixos; a contagem acima é a completa.</p>
      )}
      {filtradas.length > PAGE && (
        <div className="flex justify-between items-center mt-3">
          <span className="text-xs text-gray-500">{fmt(filtradas.length)} prefixos</span>
          <div className="flex gap-1">
            <button type="button" disabled={page === 0} onClick={() => setPage((p) => p - 1)} className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600 disabled:opacity-40">← anterior</button>
            <button type="button" disabled={(page + 1) * PAGE >= filtradas.length} onClick={() => setPage((p) => p + 1)} className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600 disabled:opacity-40">próxima →</button>
          </div>
        </div>
      )}
    </div>
  )
}
