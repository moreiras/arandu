// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Fragment, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../../../auth/AuthContext'
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
import { palavra } from '../../../lib/sintese'
import { baixarCsvParticipantes, montarCsvParticipantes } from '../participantesCsv'
import { fmtPortas } from '../portas'

const POR_PAGINA = 50
/** Páginas do CSV: o máximo da rota, para pedir o PTT inteiro em poucas chamadas (mais de 100 linhas é da classe `login`). */
const POR_PAGINA_CSV = 200
const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))

/** Filtros e o que cada um diz, na ordem da tela. Os contadores vêm do servidor e valem para o PTT inteiro. */
const FILTROS: Array<[FiltroParticipantes, string]> = [
  ['todos', 'Todos'], ['sem-v6', 'Sem direto IPv6'], ['sem-v4', 'Sem direto IPv4'], ['sem-direto', 'Sem direto em nenhuma família'],
  ['membro-sem-sessao-rs', 'No cadastro, sem sessão no RS'], ['sessao-sem-cadastro', 'Sessão no RS, fora do cadastro'], ['com-cdn', 'CDN da lista curada'], ['com-rejeicao', 'Com rota filtrada no RS'],
]
const ORDENS: Record<string, { primeiro: 'asc' | 'desc' }> = { asn: { primeiro: 'asc' }, nome: { primeiro: 'asc' }, uf: { primeiro: 'asc' }, sessoes_rs: { primeiro: 'desc' }, rejeicao: { primeiro: 'desc' }, assinantes: { primeiro: 'desc' }, usuarios_apnic: { primeiro: 'desc' }, usuarios_ptt: { primeiro: 'desc' } }

/** Sim, não ou "sem coleta": `null` é família sem coleta válida e nunca vira "não". */
const simNao = (v: boolean | null) => (v == null ? 'sem coleta' : v ? 'sim' : 'não')
/** Usuários estimados: inteiro arredondado; entre 0 e 0,5 diz "menos de 1" (0 de verdade é 0); `null` é "não se aplica" (ASN fora do Brasil, sem dado ou sem coleta IPv4). */
const usuarios = (v: number | null | undefined) => (v == null ? '—' : v > 0 && v < 0.5 ? 'menos de 1' : n(Math.round(v)))
/** Originador: `null` é família sem coleta ou ASN fora do Brasil (a lista publicada é só dos brasileiros). */
const originador = (l: ParticipantePtt, v: boolean | null) => (v == null ? (l.is_br === false ? 'n/d (fora do Brasil)' : 'sem coleta') : v ? 'sim' : 'não')

/** Prefixos vistos no PTT por família (IPv6 antes de IPv4): próprios (o ASN é o originador) e de terceiros (repassados por ele); `null` é sem sessão direta na família. */
function Prefixos({ l }: { l: ParticipantePtt }) {
  const fam = (['v6', 'v4'] as const).filter((a) => l.prefixos?.[a])
  if (!fam.length) return <p>Prefixos vistos no PTT: sem sessão direta observada no looking glass, então não há prefixos por este ASN.</p>
  return (
    <ul className="list-none space-y-0.5">
      {fam.map((a) => {
        const st = l.prefixos[a]!
        const unidade = a === 'v6' ? '/48' : '/24'
        return (
          <li key={a}>
            Prefixos vistos no PTT em {a === 'v6' ? 'IPv6' : 'IPv4'}: {n(st.own_prefixes)} {palavra(st.own_prefixes, 'próprio', 'próprios')}
            {st.own_space_24 > 0 ? ` (${n(st.own_space_24)} ${unidade})` : ''} e {n(st.third_prefixes)} {palavra(st.third_prefixes, 'de terceiro', 'de terceiros')}
            {st.third_space_24 > 0 ? ` (${n(st.third_space_24)} ${unidade})` : ''}, de {n(st.origin_asns)} {palavra(st.origin_asns, 'ASN originador', 'ASNs originadores')}.
          </li>
        )
      })}
    </ul>
  )
}

function Detalhe({ l, ptt, sel }: { l: ParticipantePtt; ptt: string; sel: (l: ParticipantePtt) => void }) {
  const r = l.rejeicao
  const d = l.rejeicao_detalhe
  const portas = fmtPortas(l.peeringdb?.portas_mbps ?? undefined)
  const inst = l.peeringdb?.instalacoes ?? []
  const comDireto = l.direto.v6 === true || l.direto.v4 === true
  return (
    <div className="space-y-1 text-xs text-gray-700">
      <p>
        <Link to={`/asn/${l.asn}`} className="text-primario-700 hover:underline">Abrir AS{l.asn}</Link>
        {comDireto && (
          <>
            {' · '}
            <Link to={`/ixp/${ptt}?aba=cobertura`} onClick={() => sel(l)} className="text-primario-700 hover:underline" data-testid={`hilbert-${l.asn}`}>
              Destacar AS{l.asn} na curva de Hilbert (abre a aba Cobertura)
            </Link>
          </>
        )}
      </p>
      <Prefixos l={l} />
      <p>{l.membro ? 'Consta no cadastro de participantes do IX.br.' : 'Não consta no cadastro de participantes do IX.br.'}{' '}
        {l.sessao_rs ? `Sessões com o route server: ${n(l.sessao_rs.up)} up e ${n(l.sessao_rs.down)} down de ${n(l.sessao_rs.sessoes)}${l.sessao_rs.incertas ? ` (${n(l.sessao_rs.incertas)} em route server sem cache de vizinhos atual)` : ''}.` : 'Sem dado de sessões no route server.'}
        {l.cadastrado_sem_sessao_rs ? ' No cadastro e sem sessão com o route server: pode haver peering bilateral, que estas fontes não observam.' : ''}</p>
      {r && <p>Rotas filtradas ÷ recebidas nas sessões up: {n(r.filtradas)} ÷ {n(r.recebidas)}{r.pct != null ? ` (${r.pct.toLocaleString('pt-BR')}%)` : ' (sem rotas recebidas: sem percentual)'}, em {n(r.sessoes_up)} {palavra(r.sessoes_up, 'sessão', 'sessões')}.</p>}
      {d && <p>Detalhe por motivo (outra coleta): {n(d.rotas)} rotas rejeitadas{d.contagem === 'amostra' ? ' (contagem parcial)' : ''}, coleta de {d.coletado_ate?.slice(0, 10) ?? 'data desconhecida'}{d.idade_dias != null ? `, ${n(d.idade_dias)} ${palavra(d.idade_dias, 'dia', 'dias')} antes do snapshot` : ''}{d.herdado ? '; herdada de uma rodada anterior' : ''}.</p>}
      {(l.sici_alcancado?.v6 != null || l.sici_alcancado?.v4 != null) && (
        <p>Acessos fixos (SICI) dos CNPJs nos AS-paths que este ASN anuncia no PTT, sem repetir CNPJ:{' '}
          {(['v6', 'v4'] as const).filter((a) => l.sici_alcancado[a] != null).map((a) => `${a === 'v6' ? 'IPv6' : 'IPv4'} ${n(l.sici_alcancado[a])}`).join(' e ')}.</p>
      )}
      {portas && <p>Porta declarada pela própria rede no PeeringDB para este PTT: {portas}. Autodeclarado: pode estar desatualizado e não é a porta contratada no IX.br nem tráfego.</p>}
      {inst.length > 0 && (
        <p>Instalações (inferidas do PeeringDB) onde a rede declara presença e que abrigam este PTT:{' '}
          {inst.map((x, i) => <span key={x.id}>{i > 0 ? ', ' : ''}<Link to={`/instalacao/${x.id}`} className="text-primario-700 hover:underline">{x.nome ?? `instalação ${x.id}`}</Link></span>)}.</p>
      )}
      {l.cdns.length > 0 && <p>CDNs da lista curada que são membros deste PTT: {l.cdns.join(', ')}.</p>}
    </div>
  )
}

/**
 * Tabela única de participantes do PTT (PT-24 / IXP-E5.5): uma linha por ASN visto no cadastro do IX.br, no looking glass ou nos route servers, com paginação,
 * busca e filtros no servidor (`GET /ixps/{code}/participantes`) e o estado na URL. Substitui os blocos "Participantes e filtros", "Membros registrados sem peering
 * direto" e as tabelas de ASNs por família (peers IPv6 e IPv4), de que traz empresa, política de peering, usuários, prefixos e o destaque na curva de Hilbert. Cadastro (membro) e sessão com o route server são colunas distintas; família sem coleta aparece como tal, nunca como ausência. Sem cor de juízo e com ordem
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
  const { requireLogin } = useAuth()
  const [baixando, setBaixando] = useState(false)
  const [erroCsv, setErroCsv] = useState(false)

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
  /** CSV do que a tela mostra (mesmos filtro, UF, busca e ordem), do PTT inteiro e não só da página. Exige login, como toda exportação. */
  const baixar = async () => {
    if (!requireLogin('exportar')) return
    setBaixando(true); setErroCsv(false)
    try {
      const itens: ParticipantePtt[] = []
      let ultima: Awaited<ReturnType<typeof fetchIxpParticipantes>> | null = null
      for (let pag = 1; ; pag++) {
        const r = await fetchIxpParticipantes(code, { date: date ?? undefined, filtro, uf: uf || undefined, q: q || undefined, ordem: campo, desc: desc || undefined, limit: POR_PAGINA_CSV, page: pag })
        itens.push(...r.items); ultima = r
        if (itens.length >= r.total || r.items.length === 0) break
      }
      baixarCsvParticipantes(montarCsvParticipantes(itens, ultima.fontes, ultima.snapshot_date), code, ultima.snapshot_date)
    } catch {
      setErroCsv(true)
    } finally {
      setBaixando(false)
    }
  }
  /** Destaca o AS na curva de Hilbert de cada família em que ele tem sessão direta (a seleção vive na página e a aba Cobertura a lê). */
  const sel = (l: ParticipantePtt) => { setSelectedPeerV6(l.direto.v6 ? l.asn : null); setSelectedPeerV4(l.direto.v4 ? l.asn : null) }

  if (error && !data) return <EstadoDados erro={error} oQue="a tabela de participantes do PTT" />
  if (isLoading && !data) return <EstadoDados estado="carregando" mensagem="Carregando os participantes…" />
  if (!data) return null
  const paginas = Math.max(1, Math.ceil(data.total / POR_PAGINA))
  const f = data.fontes
  const semColeta = (['v6', 'v4'] as const).filter((a) => f.looking_glass.coleta[a] !== 'ok')
  const colunas = rs ? 17 : 14

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
        <button type="button" onClick={baixar} disabled={baixando} className="mb-0.5 rounded border border-gray-200 bg-white px-2.5 py-1 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          title="Baixa o PTT inteiro com o filtro, a UF, a busca e a ordem atuais, com todas as colunas. Exige entrar com a conta.">
          {baixando ? 'Preparando o CSV…' : 'Baixar CSV'}
        </button>
        {erroCsv && <span role="alert" className="pb-1 text-gray-700">Não foi possível preparar o CSV agora. Tente de novo em instantes.</span>}
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
          <caption className="sr-only">Participantes do PTT: uma linha por ASN, com empresa, política de peering declarada no PeeringDB, cadastro, sessão direta por família, originador, route server, rejeição, idade da coleta, usuários estimados pela APNIC, acessos fixos declarados ao SICI e CDNs. A ordem padrão é por ASN.</caption>
          <thead>
            <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
              <ThOrdenavel {...th('asn')} className="py-1 pr-3 font-medium">ASN</ThOrdenavel>
              <ThOrdenavel {...th('nome')} className="py-1 pr-3 font-medium">Nome</ThOrdenavel>
              <ThOrdenavel {...th('uf')} className="py-1 pr-3 font-medium">UF</ThOrdenavel>
              <th scope="col" className="py-1 pr-3 font-medium">Empresa<Dica rotulo="Empresa" texto="Nome comercial do CNPJ vinculado ao ASN, pelas bases da Anatel. O link abre a página da operadora. Sem nome nas fontes, a célula diz isso e o CNPJ não é usado como nome." /></th>
              <th scope="col" className="py-1 pr-3 font-medium">Política de peering (PeeringDB)<Dica rotulo="Política de peering" texto="O que a própria rede declarou no PeeringDB (Open, Selective, Restrictive ou No). É autodeclarado, pode estar desatualizado e não é verificado. Traço: sem cadastro ou sem o campo." /></th>
              <th scope="col" className="py-1 pr-3 font-medium">Membro (cadastro)<Dica rotulo="Membro (cadastro)" texto={UNIVERSOS.membroCadastro.definicao} /></th>
              <th scope="col" className="py-1 pr-3 font-medium">Direto IPv6<Dica rotulo="Direto IPv6" texto="Sessão BGP com o route server vista no looking glass do IX.br, na família IPv6. Não é o cadastro, e não inclui peering bilateral." /></th>
              <th scope="col" className="py-1 pr-3 font-medium">Direto IPv4</th>
              <th scope="col" className="py-1 pr-3 font-medium">Originador IPv6<Dica rotulo="Originador" texto="Prefixos originados por este ASN aparecem nas rotas do PTT, anunciados por ele ou por terceiros. A lista publicada cobre só ASNs brasileiros." /></th>
              <th scope="col" className="py-1 pr-3 font-medium">Originador IPv4</th>
              {rs && <ThOrdenavel {...th('sessoes_rs')} className="py-1 pr-3 font-medium" extra={<Dica rotulo="Sessões no route server" texto={UNIVERSOS.sessaoRs.definicao} />}>Sessões RS (up/total)</ThOrdenavel>}
              {rs && <ThOrdenavel {...th('rejeicao')} className="py-1 pr-3 font-medium" extra={<Dica rotulo="Rotas filtradas ÷ recebidas" texto="Contadores do route server nas sessões up, do mesmo instante. Rota filtrada é a que o route server não aceitou; o motivo está no detalhe da linha e a causa não é atribuída." />}>Filtradas ÷ recebidas</ThOrdenavel>}
              {rs && <th scope="col" className="py-1 pr-3 font-medium">Idade da coleta por motivo<Dica rotulo="Idade da coleta por motivo" texto="Dias entre a coleta do detalhe de rotas rejeitadas por motivo e a data do snapshot. É uma coleta à parte (rodízio) e pode ser herdada de uma rodada anterior." /></th>}
              <ThOrdenavel {...th('assinantes')} className="py-1 pr-3 font-medium" extra={<Dica rotulo="Acessos fixos (SICI)" texto="Acessos de banda larga fixa que o CNPJ do ASN declarou ao SICI da Anatel no mês de referência (outra data que a do snapshot). 'Compartilhado': o CNPJ tem mais de um ASN e o mesmo total vale em cada um; não some. Traço: sem CNPJ vinculado ao ASN ou sem declaração." />}>Acessos fixos (SICI)</ThOrdenavel>
              <ThOrdenavel {...th('usuarios_apnic')} className="py-1 pr-3 font-medium" extra={<Dica rotulo="Usuários APNIC (total do AS)" texto="Usuários que a APNIC estima para o AS inteiro, por amostragem de anúncios, não por prefixo. Só ASN brasileiro; os demais ficam em traço." />}>Usuários APNIC (total do AS)</ThOrdenavel>
              <ThOrdenavel {...th('usuarios_ptt')} className="py-1 pr-3 font-medium" extra={<Dica rotulo="Dos quais via prefixos vistos no PTT (estimado)" texto="Estimativa: usuários APNIC do AS multiplicados pela parte do espaço IPv4 do AS que aparece neste PTT. Supõe usuários uniformes no espaço IPv4. Veja Como ler abaixo da tabela." />}>Dos quais via prefixos vistos no PTT (estimado)</ThOrdenavel>
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
                    <td className="py-1 pr-3 text-gray-700">
                      {l.empresa ? <Link to={`/operadora/${l.empresa.cnpj}`} className="text-primario-700 hover:underline">{l.empresa.nome ?? 'operadora (sem nome nas fontes)'}</Link> : <span className="text-gray-500">—</span>}
                    </td>
                    <td className="py-1 pr-3 text-gray-700">{l.politica_peering ?? <span className="text-gray-500">—</span>}</td>
                    <td className="py-1 pr-3">{l.membro ? 'sim' : 'não'}</td>
                    <td className="py-1 pr-3">{simNao(l.direto.v6)}</td>
                    <td className="py-1 pr-3">{simNao(l.direto.v4)}</td>
                    <td className="py-1 pr-3">{originador(l, l.originador.v6)}</td>
                    <td className="py-1 pr-3">{originador(l, l.originador.v4)}</td>
                    {rs && <td className="py-1 pr-3 tabular-nums">{l.sessao_rs ? `${n(l.sessao_rs.up)}/${n(l.sessao_rs.sessoes)}` : 'sem dado'}</td>}
                    {rs && <td className="py-1 pr-3 tabular-nums">{l.rejeicao ? `${n(l.rejeicao.filtradas)} ÷ ${n(l.rejeicao.recebidas)}${l.rejeicao.pct != null ? ` (${l.rejeicao.pct.toLocaleString('pt-BR')}%)` : ''}` : '—'}</td>}
                    {rs && <td className="py-1 pr-3">{l.rejeicao_detalhe ? `${l.rejeicao_detalhe.idade_dias != null ? `${n(l.rejeicao_detalhe.idade_dias)} d` : 'idade desconhecida'}${l.rejeicao_detalhe.herdado ? ', herdada' : ''}` : '—'}</td>}
                    <td className="py-1 pr-3 tabular-nums">{l.sici ? <>{n(l.sici.acessos)}{l.sici.compartilhado && <span className="text-xs text-gray-600"> (compartilhado)</span>}</> : '—'}</td>
                    <td className="py-1 pr-3 tabular-nums">{usuarios(l.usuarios_apnic)}</td>
                    <td className="py-1 pr-3 tabular-nums">{usuarios(l.usuarios_ptt)}</td>
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
        <p><b>Como ler as colunas de usuários.</b> {data.limites_usuarios}</p>
        {data.usuarios_ptt_resumo && (
          <p data-testid="usuarios-resumo">
            Estimativa para o PTT inteiro: {usuarios(data.usuarios_ptt_resumo.na_tabela)} {palavra(Math.round(data.usuarios_ptt_resumo.na_tabela), 'usuário', 'usuários')} na coluna, somando todos os participantes (não só esta página)
            {data.usuarios_ptt_resumo.fora_da_tabela.asns > 0 && <>, e {usuarios(data.usuarios_ptt_resumo.fora_da_tabela.usuarios)} {palavra(Math.round(data.usuarios_ptt_resumo.fora_da_tabela.usuarios), 'usuário', 'usuários')} de {n(data.usuarios_ptt_resumo.fora_da_tabela.asns)} {palavra(data.usuarios_ptt_resumo.fora_da_tabela.asns, 'ASN que anuncia', 'ASNs que anunciam')} prefixos neste PTT sem constar como {palavra(data.usuarios_ptt_resumo.fora_da_tabela.asns, 'participante', 'participantes')}</>}
            : total de {usuarios(data.usuarios_ptt_resumo.total_do_ptt)}, o mesmo valor de usuários estimados do PTT no resumo da página.
          </p>
        )}
        <LinhaProveniencia selo="fato" fonte={`${f.cadastro.fonte}: coluna Membro`} dataRef={f.cadastro.snapshot} />
        <LinhaProveniencia selo="fato" fonte={`${f.looking_glass.fonte}: colunas Direto e Originador`} dataRef={f.looking_glass.snapshot} />
        <LinhaProveniencia selo="fato" fonte={`${f.route_servers.fonte ?? 'route servers (Alice-LG)'}${f.route_servers.versao_alice ? ` ${f.route_servers.versao_alice}` : ''}: sessões e rotas filtradas ÷ recebidas`} dataRef={f.route_servers.coletado_em} />
        <LinhaProveniencia selo="fato" fonte={`${f.rejeicoes_por_motivo.fonte ?? 'route servers (Alice-LG)'}: rotas rejeitadas por motivo, no detalhe da linha`} dataRef={f.rejeicoes_por_motivo.coletado_nivel2} />
        <LinhaProveniencia selo="fato" fonte={`${f.sici.fonte}: coluna Acessos fixos, declarados pelo CNPJ do ASN`} dataRef={f.sici.mes_referencia ?? f.sici.snapshot} />
        <LinhaProveniencia selo="fato" fonte={`${f.apnic.fonte}: coluna Usuários APNIC (total do AS)`} dataRef={f.apnic.snapshot} />
        <LinhaProveniencia selo="estimado" fonte={`${f.apnic.fonte} e ${f.prefixos.fonte}: coluna Dos quais via prefixos vistos no PTT`} dataRef={f.prefixos.snapshot} />
        <LinhaProveniencia selo="fato" fonte={`${f.peeringdb.fonte}: coluna Política de peering`} dataRef={f.peeringdb.coletado_em ?? f.peeringdb.snapshot} />
        <LinhaProveniencia selo="fato" fonte={`${f.prefixos.fonte}: prefixos próprios e de terceiros, no detalhe da linha`} dataRef={f.prefixos.snapshot} />
        <LinhaProveniencia selo="fato" fonte={`${f.cdns.fonte}: coluna CDNs (membro do PTT que é ASN de CDN da lista)`} dataRef={f.cdns.snapshot} />
      </div>
    </div>
  )
}
