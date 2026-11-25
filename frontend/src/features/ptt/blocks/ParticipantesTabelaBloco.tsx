// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Fragment, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Link } from '../../../components/layout/LinkDatado'
import { Dica } from '../../../components/ui/Dica'
import { EstadoDados } from '../../../components/ui/EstadoDados'
import { LinhaProveniencia } from '../../../components/ui/Kpi'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'
import { alternarOrdem, type Ordem } from '../../../lib/ordenacao'
import { UNIVERSOS } from '../../../lib/universos'
import { fetchIxpParticipantes } from '../../../services/api'
import type { FiltroParticipantes, ParticipantePtt } from '../../../types/api'
import type { BlocoProps } from '../../entidade/registry'
import type { PttCtx } from '../contexto'

const POR_PAGINA = 50
const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))

/** Filtros e o que cada um diz, na ordem da tela. Os contadores vêm do servidor e valem para o PTT inteiro. */
const FILTROS: Array<[FiltroParticipantes, string]> = [
  ['todos', 'Todos'], ['sem-v6', 'Sem direto IPv6'], ['sem-v4', 'Sem direto IPv4'], ['sem-direto', 'Sem direto em nenhuma família'],
  ['membro-sem-sessao-rs', 'No cadastro, sem sessão no RS'], ['sessao-sem-cadastro', 'Sessão no RS, fora do cadastro'], ['com-cdn', 'CDN da lista curada'], ['com-rejeicao', 'Com rota filtrada no RS'],
]
const ORDENS: Record<string, { primeiro: 'asc' | 'desc' }> = { asn: { primeiro: 'asc' }, nome: { primeiro: 'asc' }, uf: { primeiro: 'asc' }, sessoes_rs: { primeiro: 'desc' }, rejeicao: { primeiro: 'desc' } }

/** Sim, não ou "sem coleta": `null` é família sem coleta válida e nunca vira "não". */
const simNao = (v: boolean | null) => (v == null ? 'sem coleta' : v ? 'sim' : 'não')
/** Originador: `null` é família sem coleta ou ASN fora do Brasil (a lista publicada é só dos brasileiros). */
const originador = (l: ParticipantePtt, v: boolean | null) => (v == null ? (l.is_br === false ? 'n/d (fora do Brasil)' : 'sem coleta') : v ? 'sim' : 'não')

function Detalhe({ l, ptt, sel }: { l: ParticipantePtt; ptt: string; sel: (asn: number) => void }) {
  const r = l.rejeicao
  const d = l.rejeicao_detalhe
  return (
    <div className="space-y-1 text-xs text-gray-700">
      <p>
        <Link to={`/asn/${l.asn}`} className="text-primario-700 hover:underline">Abrir AS{l.asn}</Link>
        {' · '}
        <Link to={`/ixp/${ptt}?aba=cobertura`} onClick={() => sel(l.asn)} className="text-primario-700 hover:underline">Destacar na curva de Hilbert (aba Cobertura)</Link>
      </p>
      <p>{l.membro ? 'Consta no cadastro de participantes do IX.br.' : 'Não consta no cadastro de participantes do IX.br.'}{' '}
        {l.sessao_rs ? `Sessões com o route server: ${n(l.sessao_rs.up)} up e ${n(l.sessao_rs.down)} down de ${n(l.sessao_rs.sessoes)}${l.sessao_rs.incertas ? ` (${n(l.sessao_rs.incertas)} em route server sem cache de vizinhos atual)` : ''}.` : 'Sem dado de sessões no route server.'}
        {l.cadastrado_sem_sessao_rs ? ' No cadastro e sem sessão com o route server: pode haver peering bilateral, que estas fontes não observam.' : ''}</p>
      {r && <p>Rotas filtradas ÷ recebidas nas sessões up: {n(r.filtradas)} ÷ {n(r.recebidas)}{r.pct != null ? ` (${r.pct.toLocaleString('pt-BR')}%)` : ' (sem rotas recebidas: sem percentual)'}, em {n(r.sessoes_up)} sessão(ões).</p>}
      {d && <p>Detalhe por motivo (outra coleta): {n(d.rotas)} rotas rejeitadas{d.contagem === 'amostra' ? ' (contagem parcial)' : ''}, coleta de {d.coletado_ate?.slice(0, 10) ?? 'data desconhecida'}{d.idade_dias != null ? `, ${n(d.idade_dias)} dia(s) antes do snapshot` : ''}{d.herdado ? '; herdada de uma rodada anterior' : ''}.</p>}
      {l.cdns.length > 0 && <p>CDNs da lista curada que são membros deste PTT: {l.cdns.join(', ')}.</p>}
    </div>
  )
}

/**
 * Tabela única de participantes do PTT (PT-24 / IXP-E5.5): uma linha por ASN visto no cadastro do IX.br, no looking glass ou nos route servers, com paginação,
 * busca e filtros no servidor (`GET /ixps/{code}/participantes`) e o estado na URL. Substitui os blocos "Participantes e filtros" e "Membros registrados sem peering
 * direto". Cadastro (membro) e sessão com o route server são colunas distintas; família sem coleta aparece como tal, nunca como ausência. Sem cor de juízo e com ordem
 * padrão por ASN: nenhuma coluna aqui é ranking.
 */
export function ParticipantesTabelaBloco({ dados }: BlocoProps<PttCtx>) {
  const { code, date, setSelectedPeerV4, setSelectedPeerV6 } = dados
  const [params, setParams] = useSearchParams()
  const filtro = (FILTROS.find(([f]) => f === params.get('filtro'))?.[0] ?? 'todos') as FiltroParticipantes
  const uf = params.get('uf') ?? ''
  const q = params.get('busca') ?? ''
  const campo = params.get('ordem') && ORDENS[params.get('ordem')!] ? params.get('ordem')! : 'asn'
  const desc = params.has('ordem') ? params.get('sentido') === 'desc' : false
  const pagina = Math.max(1, Number(params.get('pagina')) || 1)
  const rs = params.get('rs') === '1'
  const [busca, setBusca] = useState(q)
  const [abertas, setAbertas] = useState<Set<number>>(new Set())

  const mudar = (patch: Record<string, string | null>, manterPagina = false) => {
    setParams((atual) => {
      const p = new URLSearchParams(atual)
      for (const [k, v] of Object.entries(patch)) { if (v) p.set(k, v); else p.delete(k) }
      if (!manterPagina) p.delete('pagina')
      return p
    }, { replace: true })
  }
  useEffect(() => {
    if (busca === q) return
    const t = window.setTimeout(() => mudar({ busca: busca.trim() || null }), 350)
    return () => window.clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [busca])

  const { data, isLoading, error } = useQuery({
    queryKey: ['ixp-participantes', code, date, filtro, uf, q, campo, desc, pagina],
    queryFn: () => fetchIxpParticipantes(code, { date: date ?? undefined, filtro, uf: uf || undefined, q: q || undefined, ordem: campo, desc: desc || undefined, limit: POR_PAGINA, page: pagina }),
    staleTime: 5 * 60 * 1000, placeholderData: (anterior) => anterior,
  })

  const ordemAtual: Ordem = { campo, dir: desc ? 'desc' : 'asc' }
  const ordenar = (c: string) => { const o = alternarOrdem(campo === c ? ordemAtual : null, c, ORDENS[c].primeiro); mudar({ ordem: o.campo === 'asn' && o.dir === 'asc' ? null : o.campo, sentido: o.dir === 'desc' ? 'desc' : null }) }
  const th = (c: string) => ({ campo: c, ordem: ordemAtual, onOrdenar: ordenar })
  const alternar = (asn: number) => setAbertas((s) => { const x = new Set(s); if (x.has(asn)) x.delete(asn); else x.add(asn); return x })
  const sel = (asn: number) => { setSelectedPeerV4(asn); setSelectedPeerV6(asn) }

  if (error && !data) return <EstadoDados erro={error} oQue="a tabela de participantes do PTT" />
  if (isLoading && !data) return <EstadoDados estado="carregando" mensagem="Carregando os participantes…" />
  if (!data) return null
  const paginas = Math.max(1, Math.ceil(data.total / POR_PAGINA))
  const f = data.fontes
  const semColeta = (['v6', 'v4'] as const).filter((a) => f.looking_glass.coleta[a] !== 'ok')
  const colunas = rs ? 12 : 9

  return (
    <div className="space-y-3" data-testid="participantes-tabela">
      <div className="flex flex-wrap items-center gap-2 text-xs" role="group" aria-label="Filtros de participantes">
        {FILTROS.map(([id, rot]) => (
          <button key={id} type="button" aria-pressed={filtro === id} onClick={() => mudar({ filtro: id === 'todos' ? null : id })}
            className={`rounded-full border px-2.5 py-1 ${filtro === id ? 'bg-primario-600 text-white border-primario-600' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}`}>
            {rot} <span className="tabular-nums">({n(data.contagens[id])})</span>
          </button>
        ))}
      </div>
      <div className="flex flex-wrap items-end gap-3 text-xs text-gray-600">
        <label className="flex flex-col">Buscar por ASN ou nome
          <input type="search" value={busca} onChange={(e) => setBusca(e.target.value)} className="border border-gray-200 rounded px-2 py-1 text-sm w-56" placeholder="ex.: AS64496 ou parte do nome" />
        </label>
        {data.ufs.length > 0 && (
          <label className="flex flex-col">UF da sede
            <select value={uf} onChange={(e) => mudar({ uf: e.target.value || null })} className="border border-gray-200 rounded px-2 py-1 text-sm">
              <option value="">todas</option>{data.ufs.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </label>
        )}
        <label className="flex items-center gap-1.5 pb-1">
          <input type="checkbox" checked={rs} onChange={(e) => mudar({ rs: e.target.checked ? '1' : null }, true)} /> mostrar colunas do route server (sessões, rejeição, idade da coleta)
        </label>
      </div>
      <p className="text-xs text-gray-600" aria-live="polite">
        {n(data.total)} de {n(data.total_participantes)} participantes ({data.filtros.definicao_do_filtro}). Ordem: {data.ordem}.
      </p>
      {semColeta.length > 0 && (
        <p className="text-xs text-gray-600">
          Sem coleta válida no looking glass em {semColeta.map((a) => (a === 'v6' ? 'IPv6' : 'IPv4')).join(' e ')} neste snapshot: a coluna correspondente diz "sem coleta" e a família fica fora dos filtros. Isso não quer dizer que não haja sessões.
        </p>
      )}
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <caption className="sr-only">Participantes do PTT: uma linha por ASN, com cadastro, sessão direta por família, originador, route server, rejeição, idade da coleta e CDNs. A ordem padrão é por ASN.</caption>
          <thead>
            <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
              <ThOrdenavel {...th('asn')} className="py-1 pr-3 font-medium">ASN</ThOrdenavel>
              <ThOrdenavel {...th('nome')} className="py-1 pr-3 font-medium">Nome</ThOrdenavel>
              <ThOrdenavel {...th('uf')} className="py-1 pr-3 font-medium">UF</ThOrdenavel>
              <th scope="col" className="py-1 pr-3 font-medium">Membro (cadastro)<Dica rotulo="Membro (cadastro)" texto={UNIVERSOS.membroCadastro.definicao} /></th>
              <th scope="col" className="py-1 pr-3 font-medium">Direto IPv6<Dica rotulo="Direto IPv6" texto="Sessão BGP com o route server vista no looking glass do IX.br, na família IPv6. Não é o cadastro, e não inclui peering bilateral." /></th>
              <th scope="col" className="py-1 pr-3 font-medium">Direto IPv4</th>
              <th scope="col" className="py-1 pr-3 font-medium">Originador IPv6<Dica rotulo="Originador" texto="Prefixos originados por este ASN aparecem nas rotas do PTT, anunciados por ele ou por terceiros. A lista publicada cobre só ASNs brasileiros." /></th>
              <th scope="col" className="py-1 pr-3 font-medium">Originador IPv4</th>
              {rs && <ThOrdenavel {...th('sessoes_rs')} className="py-1 pr-3 font-medium" extra={<Dica rotulo="Sessões no route server" texto={UNIVERSOS.sessaoRs.definicao} />}>Sessões RS (up/total)</ThOrdenavel>}
              {rs && <ThOrdenavel {...th('rejeicao')} className="py-1 pr-3 font-medium" extra={<Dica rotulo="Rotas filtradas ÷ recebidas" texto="Contadores do route server nas sessões up, do mesmo instante. Rota filtrada é a que o route server não aceitou; o motivo está no detalhe da linha e a causa não é atribuída." />}>Filtradas ÷ recebidas</ThOrdenavel>}
              {rs && <th scope="col" className="py-1 pr-3 font-medium">Idade da coleta por motivo<Dica rotulo="Idade da coleta por motivo" texto="Dias entre a coleta do detalhe de rotas rejeitadas por motivo e a data do snapshot. É uma coleta à parte (rodízio) e pode ser herdada de uma rodada anterior." /></th>}
              <th scope="col" className="py-1 pr-3 font-medium">CDNs</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((l) => {
              const aberta = abertas.has(l.asn)
              const idDet = `part-${l.asn}`
              return (
                <Fragment key={l.asn}>
                  <tr className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer" onClick={(e) => { if (!(e.target as HTMLElement).closest('a,button,select,input')) alternar(l.asn) }}>
                    <td className="py-1 pr-3 whitespace-nowrap">
                      <button type="button" aria-expanded={aberta} aria-controls={idDet} aria-label={`Detalhes de AS${l.asn}`} onClick={() => alternar(l.asn)}
                        className="mr-1 rounded text-gray-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario-500"><span aria-hidden="true">{aberta ? '▾' : '▸'}</span></button>
                      <Link to={`/asn/${l.asn}`} className="text-primario-700 hover:underline">AS{l.asn}</Link>
                    </td>
                    <td className="py-1 pr-3 text-gray-700">{l.nome ?? <span className="text-gray-500">sem nome na fonte</span>}</td>
                    <td className="py-1 pr-3 text-gray-500">{l.uf ?? ''}</td>
                    <td className="py-1 pr-3">{l.membro ? 'sim' : 'não'}</td>
                    <td className="py-1 pr-3">{simNao(l.direto.v6)}</td>
                    <td className="py-1 pr-3">{simNao(l.direto.v4)}</td>
                    <td className="py-1 pr-3">{originador(l, l.originador.v6)}</td>
                    <td className="py-1 pr-3">{originador(l, l.originador.v4)}</td>
                    {rs && <td className="py-1 pr-3 tabular-nums">{l.sessao_rs ? `${n(l.sessao_rs.up)}/${n(l.sessao_rs.sessoes)}` : 'sem dado'}</td>}
                    {rs && <td className="py-1 pr-3 tabular-nums">{l.rejeicao ? `${n(l.rejeicao.filtradas)} ÷ ${n(l.rejeicao.recebidas)}${l.rejeicao.pct != null ? ` (${l.rejeicao.pct.toLocaleString('pt-BR')}%)` : ''}` : '—'}</td>}
                    {rs && <td className="py-1 pr-3">{l.rejeicao_detalhe ? `${l.rejeicao_detalhe.idade_dias != null ? `${n(l.rejeicao_detalhe.idade_dias)} d` : 'idade desconhecida'}${l.rejeicao_detalhe.herdado ? ', herdada' : ''}` : '—'}</td>}
                    <td className="py-1 pr-3 text-xs text-gray-600">{l.cdns.length ? `${l.cdns.slice(0, 2).join(', ')}${l.cdns.length > 2 ? ` +${l.cdns.length - 2}` : ''}` : ''}</td>
                  </tr>
                  {aberta && <tr id={idDet} className="border-b border-gray-100 bg-gray-50"><td colSpan={colunas} className="px-3 py-2"><Detalhe l={l} ptt={code} sel={sel} /></td></tr>}
                </Fragment>
              )
            })}
            {data.items.length === 0 && <tr><td colSpan={colunas} className="py-4 text-center text-xs text-gray-500">Nenhum participante com estes filtros.</td></tr>}
          </tbody>
        </table>
      </div>
      {paginas > 1 && (
        <nav aria-label="Páginas de participantes" className="flex items-center gap-3 text-sm">
          <button type="button" disabled={pagina <= 1} onClick={() => mudar({ pagina: pagina - 1 > 1 ? String(pagina - 1) : null }, true)} className="px-2 py-1 border border-gray-200 rounded disabled:opacity-40">Anterior</button>
          <span className="text-xs text-gray-600">página {n(pagina)} de {n(paginas)}</span>
          <button type="button" disabled={pagina >= paginas} onClick={() => mudar({ pagina: String(pagina + 1) }, true)} className="px-2 py-1 border border-gray-200 rounded disabled:opacity-40">Próxima</button>
        </nav>
      )}
      <div className="space-y-0.5 text-xs text-gray-600">
        <p><b>Como ler.</b> {data.limites}</p>
        <LinhaProveniencia selo="fato" fonte={`${f.cadastro.fonte}: coluna Membro`} dataRef={f.cadastro.snapshot} />
        <LinhaProveniencia selo="fato" fonte={`${f.looking_glass.fonte}: colunas Direto e Originador`} dataRef={f.looking_glass.snapshot} />
        <LinhaProveniencia selo="fato" fonte={`${f.route_servers.fonte ?? 'route servers (Alice-LG)'}${f.route_servers.versao_alice ? ` ${f.route_servers.versao_alice}` : ''}: sessões e rotas filtradas ÷ recebidas`} dataRef={f.route_servers.coletado_em} />
        <LinhaProveniencia selo="fato" fonte={`${f.rejeicoes_por_motivo.fonte ?? 'route servers (Alice-LG)'}: rotas rejeitadas por motivo, no detalhe da linha`} dataRef={f.rejeicoes_por_motivo.coletado_nivel2} />
        <LinhaProveniencia selo="fato" fonte={`${f.cdns.fonte}: coluna CDNs (membro do PTT que é ASN de CDN da lista)`} dataRef={f.cdns.snapshot} />
      </div>
    </div>
  )
}
