// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchCommunities } from '../services/api'
import { EstadoDados } from '../components/ui/EstadoDados'

const POR_PAGINA = 25
const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const CLASSES: Record<string, string> = {
  nao_exportar_para: 'Não exportar para o AS', exportar_somente_para: 'Exportar somente para o AS', nao_exportar_rir: 'Não exportar por RIR', exportar_somente_rir: 'Exportar somente por RIR',
  nao_exportar_ptt: 'Não exportar para o PTT', nao_exportar_rtt: 'Não exportar por RTT', nao_exportar_perda: 'Não exportar por perda', blackhole: 'Blackhole', rpki: 'Validação RPKI',
  informativa: 'Informativa do IX.br', rejeicao: 'Motivo de rejeição', outra: 'Outra (community própria)',
}

/**
 * `/communities` — explorador de communities dos route servers do IX.br. Busca uma community (ou um ASN-alvo) e mostra o que o dicionário do Alice diz dela e quem a usa, por PTT.
 * Só das rotas recebidas coletadas (PTTs prioritários, rodízio dentro de um orçamento de requisições): ausência na lista não prova que ninguém a usa. É declaração do membro, não tráfego.
 */
export function CommunitiesPage() {
  const [sp, setSp] = useSearchParams()
  const q = sp.get('q') ?? ''
  const ixp = sp.get('ixp') ?? ''
  const classe = sp.get('classe') ?? ''
  const pagina = Math.max(1, Number(sp.get('p') ?? 1) || 1)
  const muda = (k: string, v: string) => { const x = new URLSearchParams(sp); if (v) x.set(k, v); else x.delete(k); if (k !== 'p') x.delete('p'); setSp(x, { replace: true }) }
  const r = useQuery({ queryKey: ['communities', q, ixp, classe, pagina], retry: false, staleTime: 5 * 60 * 1000,
    queryFn: () => fetchCommunities({ q: q || undefined, ixp: ixp || undefined, classe: classe || undefined, limit: POR_PAGINA, page: pagina }) })
  const d = r.data
  const paginas = d ? Math.max(1, Math.ceil(d.total / POR_PAGINA)) : 1
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Communities dos route servers do IX.br</h1>
        <p className="text-sm text-gray-500 mt-1">
          O que cada community significa (dicionário do Alice-LG do IX.br) e quem a usa em cada PTT, a partir das rotas recebidas coletadas: communities presentes nas rotas que o membro enviou ao route server (podem ter sido marcadas por ele ou recebidas de clientes), não tráfego nem relação comercial;
          só entram os PTTs e membros coletados na rodada (a coleta é parcial, por desenho).
        </p>
      </div>
      <div className="flex flex-wrap items-end gap-3 text-sm">
        <label className="flex flex-col gap-0.5"><span className="text-xs text-gray-500">Buscar (community, texto ou ASN-alvo)</span>
          <input value={q} onChange={(e) => muda('q', e.target.value)} placeholder="ex.: 65000:0:13335, blackhole, 13335" className="border border-gray-200 rounded px-2 py-1 bg-white w-72" /></label>
        <label className="flex flex-col gap-0.5"><span className="text-xs text-gray-500">PTT (código)</span>
          <input value={ixp} onChange={(e) => muda('ixp', e.target.value.trim().toLowerCase())} placeholder="todos (ex.: sp)" className="border border-gray-200 rounded px-2 py-1 bg-white w-32" /></label>
        <label className="flex flex-col gap-0.5"><span className="text-xs text-gray-500">Classe</span>
          <select value={classe} onChange={(e) => muda('classe', e.target.value)} className="border border-gray-200 rounded px-2 py-1 bg-white">
            <option value="">todas</option>
            {Object.entries(CLASSES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select></label>
      </div>
      {r.isLoading && <p className="text-sm text-gray-500">Carregando…</p>}
      {r.isError && <EstadoDados erro={r.error} oQue="as communities" mensagem="Communities dos route servers ainda não estão disponíveis neste snapshot." aoTentarDeNovo={() => void r.refetch()} />}
      {d && (
        <>
          <p className="text-xs text-gray-600" data-testid="resumo-communities">
            {n(d.total)} communities{Object.keys(d.por_classe).length ? ` (${Object.entries(d.por_classe).map(([k, v]) => `${n(v)} ${CLASSES[k]?.toLowerCase() ?? k}`).join('; ')})` : ''}. Snapshot {d.snapshot_date}; rotas recebidas coletadas em {d.coletado_nivel3?.slice(0, 16).replace('T', ' ') ?? '—'} UTC.
          </p>
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="text-gray-500"><tr>
                <th className="text-left px-2 py-1">Community</th><th className="text-left px-2 py-1">Significado</th><th className="text-right px-2 py-1" title="ASNs distintos: um membro em vários PTTs conta uma vez">Membros</th><th className="text-right px-2 py-1">PTTs</th><th className="text-right px-2 py-1" title="A mesma rota anunciada em vários PTTs conta uma vez por PTT">Rotas (soma por PTT)</th><th className="text-left px-2 py-1">Quem mais usa</th>
              </tr></thead>
              <tbody className="divide-y divide-gray-100">
                {d.items.map((c) => {
                  const top = Object.entries(c.ixps).flatMap(([code, u]) => u.top.slice(0, 3).map((t) => ({ code, ...t }))).sort((a, b) => b.rotas - a.rotas).slice(0, 4)
                  return (
                    <tr key={c.community}>
                      <td className="px-2 py-1 font-mono">{c.community}</td>
                      <td className="px-2 py-1">{c.rotulo ?? 'sem decodificação no dicionário'} <span className="text-gray-400">· {CLASSES[c.classe] ?? c.classe}{c.forma === 'equivalente_padrao' ? ' *' : ''}</span></td>
                      <td className="px-2 py-1 text-right tabular-nums">{n(c.asns_total)}</td>
                      <td className="px-2 py-1 text-right tabular-nums">{n(c.ptts ?? Object.keys(c.ixps).length)}</td>
                      <td className="px-2 py-1 text-right tabular-nums">{n(c.rotas_total)}</td>
                      <td className="px-2 py-1">{top.map((t, i) => <span key={`${t.code}-${t.asn}`}>{i > 0 && ', '}<Link to={`/asn/${t.asn}`} className="text-primario-600 hover:underline">AS{t.asn}</Link> ({t.code.toUpperCase()})</span>)}</td>
                    </tr>
                  )
                })}
                {d.items.length === 0 && <tr><td colSpan={6} className="px-2 py-3 text-gray-500">Nenhuma community encontrada nas rotas coletadas.</td></tr>}
              </tbody>
            </table>
          </div>
          {d.items.some((c) => c.forma === 'equivalente_padrao') && (
            <p className="text-xs text-gray-500">* community padrão ou estendida lida como a grande equivalente do dicionário do Alice (equivalência assumida pela forma, não declarada pelo Alice).</p>
          )}
          {paginas > 1 && (
            <div className="flex items-center gap-3 text-xs">
              <button disabled={pagina <= 1} onClick={() => muda('p', String(pagina - 1))} className="px-2 py-1 border rounded disabled:opacity-40">Anterior</button>
              <span>Página {pagina} de {paginas}</span>
              <button disabled={pagina >= paginas} onClick={() => muda('p', String(pagina + 1))} className="px-2 py-1 border rounded disabled:opacity-40">Próxima</button>
            </div>
          )}
          <p className="text-xs text-gray-500">{d.limites}</p>
          <p className="text-xs text-gray-400">Fonte: {d.fonte ?? 'Looking Glass do IX.br (Alice-LG)'}{d.versao_alice ? ` ${d.versao_alice}` : ''}.</p>
        </>
      )}
    </div>
  )
}
