// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { BlocoProps } from '../../entidade/registry'
import type { PttCtx } from '../contexto'

type Filtro = 'todos' | 'sem-v6' | 'sem-v4' | 'sem-rs' | 'sem-direto'
const FILTROS: Array<[Filtro, string]> = [['todos', 'Todos'], ['sem-v6', 'Sem IPv6'], ['sem-v4', 'Sem IPv4'], ['sem-rs', 'Cadastrados sem sessão com o route server'], ['sem-direto', 'Sem peering direto']]
const PAGINA = 50

/**
 * Participantes do PTT com filtros: os membros cadastrados e os que têm peering direto, com a família de IP e a UF de origem do AS. "Sem sessão com o route server"
 * vem do cruzamento com o cadastro do IX.br e pode ser peering bilateral; "sem IPv6" quer dizer sem peering direto IPv6 observado nas rotas coletadas.
 */
export function ParticipantesFiltradosBloco({ dados }: BlocoProps<PttCtx>) {
  const { ixp, mergedV4, mergedV6, membersData, routeServers } = dados
  const [filtro, setFiltro] = useState<Filtro>('todos')
  const [uf, setUf] = useState('')
  const [limite, setLimite] = useState(PAGINA)
  const linhas = useMemo(() => {
    const v4 = new Set(mergedV4?.asn_direct ?? []); const v6 = new Set(mergedV6?.asn_direct ?? [])
    const semRs = new Set((routeServers?.membros ?? []).filter((m) => m.cadastrado_sem_sessao).map((m) => m.asn))
    const todos = Array.from(new Set<number>([...(ixp?.asn_members ?? []), ...v4, ...v6])).sort((a, b) => a - b)
    return todos.map((asn) => {
      const n = membersData?.nomes?.[String(asn)]
      return { asn, nome: n?.name ?? '', uf: n?.uf ?? '', v4: v4.has(asn), v6: v6.has(asn), semRs: semRs.has(asn) }
    })
  }, [ixp, mergedV4, mergedV6, membersData, routeServers])
  const ufs = useMemo(() => Array.from(new Set(linhas.map((l) => l.uf).filter(Boolean))).sort(), [linhas])
  const vis = linhas.filter((l) => (!uf || l.uf === uf) && (filtro === 'todos' || (filtro === 'sem-v6' && !l.v6) || (filtro === 'sem-v4' && !l.v4) || (filtro === 'sem-rs' && l.semRs) || (filtro === 'sem-direto' && !l.v4 && !l.v6)))
  return (
    <div className="space-y-2" data-testid="participantes-filtrados">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {FILTROS.map(([id, rot]) => (
          <button key={id} type="button" aria-pressed={filtro === id} onClick={() => { setFiltro(id); setLimite(PAGINA) }}
            className={`rounded-full border px-2.5 py-1 ${filtro === id ? 'bg-primario-600 text-white border-primario-600' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}`}>{rot}</button>
        ))}
        {ufs.length > 0 && (
          <label className="flex items-center gap-1 text-gray-600">UF de origem
            <select value={uf} onChange={(e) => { setUf(e.target.value); setLimite(PAGINA) }} className="border border-gray-200 rounded px-1 py-0.5">
              <option value="">todas</option>{ufs.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </label>
        )}
      </div>
      <p className="text-xs text-gray-500">{vis.length.toLocaleString('pt-BR')} de {linhas.length.toLocaleString('pt-BR')} participantes.</p>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead><tr className="text-left text-xs text-gray-500 border-b border-gray-200"><th className="py-1 pr-3 font-medium">AS</th><th className="py-1 pr-3 font-medium">Nome</th><th className="py-1 pr-3 font-medium">UF</th><th className="py-1 pr-3 font-medium">IPv6</th><th className="py-1 pr-3 font-medium">IPv4</th><th className="py-1 pr-3 font-medium">Route server</th></tr></thead>
          <tbody>
            {vis.slice(0, limite).map((l) => (
              <tr key={l.asn} className="border-b border-gray-100">
                <td className="py-1 pr-3"><Link to={`/asn/${l.asn}`} className="text-primario-700 hover:underline">AS{l.asn}</Link></td>
                <td className="py-1 pr-3 text-gray-700">{l.nome}</td><td className="py-1 pr-3 text-gray-500">{l.uf}</td>
                <td className="py-1 pr-3">{l.v6 ? 'direto' : '—'}</td><td className="py-1 pr-3">{l.v4 ? 'direto' : '—'}</td>
                <td className="py-1 pr-3 text-xs text-gray-500">{l.semRs ? 'cadastrado, sem sessão' : ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {vis.length > limite && <button type="button" className="text-xs text-primario-700 hover:underline" onClick={() => setLimite(limite + PAGINA)}>mostrar mais {Math.min(PAGINA, vis.length - limite)}</button>}
    </div>
  )
}
