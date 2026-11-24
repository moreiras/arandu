// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { Link } from '../components/layout/LinkDatado'
import { fetchIpv4Espaco, fetchIpv4Subasignacoes, fetchIpv4Mercado, fetchIpv4Recuperacao, fetchIpv4Transferencias, fetchIpv4UsoPorTerceiros } from '../services/api'
import type { Ipv4Direcao, Ipv4Operacao } from '../types/api'
import { CLASSES_ESPACO } from '../features/ipv4/blocos'
import { useOrdenacao } from '../lib/ordenacao'
import { ThOrdenavel } from '../components/ui/ThOrdenavel'
import { EstadoDados, ehErroDeAcessoOuFalha } from '../components/ui/EstadoDados'

const ABAS = [
  { id: 'transferencias', rotulo: 'Transferências' },
  { id: 'recuperacao', rotulo: 'Recuperação' },
  { id: 'espaco', rotulo: 'Espaço sem uso' },
  { id: 'terceiros', rotulo: 'Uso por terceiros' },
  { id: 'subasignacoes', rotulo: 'Sub-asignações' },
]
const DIRECOES: Record<Ipv4Direcao, string> = { br_br: 'Brasil → Brasil', br_exterior: 'Brasil → exterior', exterior_br: 'Exterior → Brasil' }
const TAMANHOS: Record<string, string> = { ate_24: 'até /24', '22_a_23': '/23 a /22', '20_a_21': '/21 a /20', '19_ou_maior': '/19 ou maior' }
import { formatarData } from '../lib/datas'
import { BarraDeAbas } from '../features/entidade/EntityPage'
import { useActiveDate } from '../hooks/useSnapshot'
import { manterData } from '../lib/dataAtiva'

/** Ordem dos tipos de recurso no resumo da recuperação: IPv6 antes de IPv4. */
const ORDEM_TIPO: Record<string, number> = { asn: 0, bloco6: 1, bloco: 2 }
const inteiro = (v?: number | null) => (v == null ? '—' : Math.round(v).toLocaleString('pt-BR'))
const data = formatarData

/**
 * Filtros e página de uma aba na URL (`?aba=espaco&uf=RJ&p=2&date=…`): o endereço reabre a mesma lista no mesmo snapshot.
 * Mudar um filtro volta à primeira página.
 */
function useFiltrosNaUrl() {
  const [sp, setSp] = useSearchParams()
  const valor = (k: string) => sp.get(k) ?? ''
  const muda = (k: string, v: string) => { const x = new URLSearchParams(sp); if (v) x.set(k, v); else x.delete(k); if (k !== 'p') x.delete('p'); setSp(x, { replace: true }) }
  const page = Math.max(1, Number(sp.get('p') ?? 1) || 1)
  const setPage = (n: number) => muda('p', n > 1 ? String(n) : '')
  return { valor, muda, page, setPage }
}

function Parte({ p }: { p: Ipv4Operacao['origem'] }) {
  return <span>{p.nome ?? '—'}<span className="text-gray-400"> · {p.pais ?? '?'}</span></span>
}

function Transferencias() {
  const date = useActiveDate() ?? undefined
  const { valor, muda, page, setPage } = useFiltrosNaUrl()
  const ano = valor('ano'), direcao = valor('direcao'), q = valor('q')
  const setAno = (v: string) => muda('ano', v), setDirecao = (v: string) => muda('direcao', v), setQ = (v: string) => muda('q', v)
  const mercado = useQuery({ queryKey: ['ipv4-mercado', date], queryFn: () => fetchIpv4Mercado(date), staleTime: 10 * 60 * 1000, retry: false })
  const lista = useQuery({
    queryKey: ['ipv4-transferencias', date, ano, direcao, q, page], retry: false, staleTime: 10 * 60 * 1000,
    queryFn: () => fetchIpv4Transferencias({ date, ano: ano || undefined, direcao: direcao || undefined, q: q || undefined, limit: 25, page }),
  })
  const m = mercado.data
  const anos = m ? Object.keys(m.por_ano).sort().reverse() : []
  const porAno = useOrdenacao(anos, {
    ano: { valor: (a) => Number(a), primeiro: 'asc' },
    operacoes: (a) => m?.por_ano[a].operacoes,
    blocos: (a) => m?.por_ano[a].blocos,
    enderecos: (a) => m?.por_ano[a].enderecos,
    br_br: (a) => m?.por_ano[a].por_direcao.br_br?.operacoes ?? 0,
    br_exterior: (a) => m?.por_ano[a].por_direcao.br_exterior?.operacoes ?? 0,
    exterior_br: (a) => m?.por_ano[a].por_direcao.exterior_br?.operacoes ?? 0,
  })
  const total = lista.data?.total ?? 0
  return (
    <div className="space-y-4">
      {mercado.isError && ehErroDeAcessoOuFalha(mercado.error) && <EstadoDados erro={mercado.error} oQue="o resumo das transferências" />}
      {m && (
        <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
          <div className="flex flex-wrap gap-x-8 gap-y-2 text-sm">
            <div><span className="text-2xl font-semibold tabular-nums">{inteiro(m.operacoes)}</span> <span className="text-gray-500">operações ({inteiro(m.blocos)} blocos, {inteiro(m.enderecos)} endereços)</span></div>
            {m.maior_operacao && <div className="text-gray-600">Maior operação: {inteiro(m.maior_operacao.blocos)} blocos em {data(m.maior_operacao.data)}</div>}
            {m.defasagem.mediana_dias != null && <div className="text-gray-600">Defasagem mediana de publicação: {inteiro(m.defasagem.mediana_dias)} dias ({inteiro(m.defasagem.operacoes_com_medida)} operações medidas)</div>}
            {m.casamento.pct != null && <div className="text-gray-600">{m.casamento.pct.toLocaleString('pt-BR')}% dos destinos brasileiros casam com um ASN</div>}
          </div>
          <div className="overflow-x-auto">
            <table className="text-xs min-w-full">
              <thead className="text-gray-500"><tr><ThOrdenavel {...porAno.props('ano')} className="text-left px-2 py-1">Ano</ThOrdenavel><ThOrdenavel {...porAno.props('operacoes')} alinhar="right" className="text-right px-2 py-1">Operações</ThOrdenavel><ThOrdenavel {...porAno.props('blocos')} alinhar="right" className="text-right px-2 py-1">Blocos</ThOrdenavel><ThOrdenavel {...porAno.props('enderecos')} alinhar="right" className="text-right px-2 py-1">Endereços</ThOrdenavel>
                {(Object.keys(DIRECOES) as Ipv4Direcao[]).map((d) => <ThOrdenavel key={d} {...porAno.props(d)} alinhar="right" className="text-right px-2 py-1">{DIRECOES[d]}</ThOrdenavel>)}</tr></thead>
              <tbody>
                {porAno.ordenados.map((a) => (
                  <tr key={a} className="border-t border-gray-100">
                    <td className="px-2 py-1 font-medium">{a}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(m.por_ano[a].operacoes)}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(m.por_ano[a].blocos)}</td>
                    <td className="px-2 py-1 text-right tabular-nums">{inteiro(m.por_ano[a].enderecos)}</td>
                    {(Object.keys(DIRECOES) as Ipv4Direcao[]).map((d) => <td key={d} className="px-2 py-1 text-right tabular-nums text-gray-600">{inteiro(m.por_ano[a].por_direcao[d]?.operacoes ?? 0)}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-gray-500">Por tamanho: {Object.entries(m.por_tamanho).map(([k, v]) => `${TAMANHOS[k] ?? k} ${inteiro(v)}`).join(' · ')}. Um lote de blocos no mesmo dia e entre as mesmas partes conta como uma operação.</p>
        </section>
      )}
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-sm text-gray-600 flex flex-col">Ano
            <select value={ano} onChange={(e) => { setAno(e.target.value) }} className="border border-gray-300 rounded px-2 py-1.5 text-sm"><option value="">todos</option>{anos.map((a) => <option key={a} value={a}>{a}</option>)}</select></label>
          <label className="text-sm text-gray-600 flex flex-col">Direção
            <select value={direcao} onChange={(e) => { setDirecao(e.target.value) }} className="border border-gray-300 rounded px-2 py-1.5 text-sm"><option value="">todas</option>{(Object.keys(DIRECOES) as Ipv4Direcao[]).map((d) => <option key={d} value={d}>{DIRECOES[d]}</option>)}</select></label>
          <label className="text-sm text-gray-600 flex flex-col">Parte
            <input value={q} onChange={(e) => { setQ(e.target.value) }} placeholder="nome" className="border border-gray-300 rounded px-2 py-1.5 text-sm" /></label>
        </div>
        {lista.isError && <EstadoDados erro={lista.error} oQue="a lista de transferências" mensagem="A lista de transferências não está publicada neste snapshot." aoTentarDeNovo={() => void lista.refetch()} />}
        <div className="overflow-x-auto" hidden={lista.isError}>
          <table className="text-xs min-w-full">
            <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Data</th><th className="text-left px-2 py-1">Origem</th><th className="text-left px-2 py-1">Destino</th><th className="text-right px-2 py-1">Blocos</th><th className="text-right px-2 py-1">Endereços</th>
              <th className="text-left px-2 py-1">ASN atual</th><th className="text-left px-2 py-1">Visto na lista</th></tr></thead>
            <tbody>
              {(lista.data?.items ?? []).map((o) => (
                <tr key={o.id} className="border-t border-gray-100 align-top">
                  <td className="px-2 py-1 whitespace-nowrap">{data(o.data)}</td><td className="px-2 py-1"><Parte p={o.origem} /></td><td className="px-2 py-1"><Parte p={o.destino} /></td>
                  <td className="px-2 py-1 text-right tabular-nums" title={o.blocos.slice(0, 6).join(', ')}>{o.n_blocos}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(o.enderecos)}</td>
                  <td className="px-2 py-1">{o.casamento ? <Link to={`/asn/${o.casamento.asn}`} className="text-primario-600 hover:underline">AS{o.casamento.asn}</Link> : '—'}</td>
                  <td className="px-2 py-1 whitespace-nowrap text-gray-500">{o.anterior_a_coleta ? 'antes da coleta' : `${data(o.primeira_vez_visto)}${o.defasagem_dias != null ? ` (+${o.defasagem_dias} d)` : ''}`}{o.fontes.length > 1 ? ' · 2 fontes' : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center gap-3 text-sm text-gray-600">
          <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="px-2 py-1 border border-gray-300 rounded disabled:opacity-40">Anterior</button>
          {!lista.isError && <span>{inteiro(total)} operações · página {page} de {Math.max(1, Math.ceil(total / 25))}</span>}
          <button disabled={page * 25 >= total} onClick={() => setPage(page + 1)} className="px-2 py-1 border border-gray-300 rounded disabled:opacity-40">Próxima</button>
        </div>
      </section>
    </div>
  )
}

/** Aba sem dado: carregando, erro com causa ou "não publicado" (só para 404); antes a aba sumia em branco. */
function EstadoAba({ q, oQue }: { q: { isLoading: boolean; isError: boolean; error: unknown; refetch: () => unknown }; oQue: string }) {
  if (q.isLoading) return <EstadoDados estado="carregando" />
  if (!q.isError) return null
  return <EstadoDados erro={q.error} oQue={oQue} mensagem={`Sem dado publicado neste snapshot para ${oQue}.`} aoTentarDeNovo={() => void q.refetch()} />
}

function Recuperacao() {
  const date = useActiveDate() ?? undefined
  const q = useQuery({ queryKey: ['ipv4-recuperacao', date], queryFn: () => fetchIpv4Recuperacao(date), staleTime: 10 * 60 * 1000, retry: false })
  const TIPO_ROTULO: Record<string, string> = { bloco: 'IPv4', bloco6: 'IPv6', asn: 'ASN' }
  const itens = useOrdenacao(q.data?.em_recuperacao.itens, {
    tipo: (i) => TIPO_ROTULO[i.tipo] ?? i.tipo,
    recurso: (i) => (i.tipo === 'asn' ? Number(i.recurso) : i.recurso),
    janela: { valor: (i) => i.inicio, primeiro: 'asc' },
    delegated: (i) => i.status_delegated,
  })
  // Os meses mais recentes primeiro; o cabeçalho reordena todos os meses e só depois corta nos 18 exibidos.
  const todosMeses = useMemo(() => Object.keys(q.data?.eventos_por_mes ?? {}).sort().reverse(), [q.data])
  const porMes = useOrdenacao(todosMeses, {
    mes: { valor: (m) => m, primeiro: 'desc' },
    recuperacao: (m) => q.data?.eventos_por_mes[m].recuperacao ?? 0,
    liberacao: (m) => q.data?.eventos_por_mes[m].liberacao ?? 0,
  })
  if (!q.data) return <EstadoAba q={q} oQue="os recursos em recuperação" />
  const r = q.data
  const meses = porMes.ordenados.slice(0, 18)
  return (
    <div className="space-y-4">
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
        <h2 className="text-base font-semibold text-gray-900">Em recuperação no Registro.br</h2>
        <p className="text-sm text-gray-600">
          {inteiro(r.em_recuperacao.total)} recursos ({Object.entries(r.em_recuperacao.por_tipo).sort(([a], [b]) => (ORDEM_TIPO[a] ?? 9) - (ORDEM_TIPO[b] ?? 9)).map(([k, v]) => `${k === 'bloco' ? 'blocos IPv4' : k === 'bloco6' ? 'blocos IPv6' : 'ASNs'} ${inteiro(v)}`).join(' · ')});
          janela{r.em_recuperacao.janelas.length > 1 ? 's' : ''}: {r.em_recuperacao.janelas.map(([a, b]) => `${data(a)} a ${data(b)}`).join(', ')}. Já recuperados: {inteiro(r.recuperados.total)}.
        </p>
        <div className="overflow-x-auto max-h-96">
          <table className="text-xs min-w-full">
            <thead className="text-gray-500"><tr><ThOrdenavel {...itens.props('tipo')} className="text-left px-2 py-1">Tipo</ThOrdenavel><ThOrdenavel {...itens.props('recurso')} className="text-left px-2 py-1">Recurso</ThOrdenavel><ThOrdenavel {...itens.props('janela')} className="text-left px-2 py-1">Janela</ThOrdenavel><ThOrdenavel {...itens.props('delegated')} className="text-left px-2 py-1">No delegated</ThOrdenavel></tr></thead>
            <tbody>
              {itens.ordenados.map((i) => (
                <tr key={`${i.tipo}${i.recurso}`} className="border-t border-gray-100">
                  <td className="px-2 py-1">{i.tipo === 'bloco' ? 'IPv4' : i.tipo === 'bloco6' ? 'IPv6' : 'ASN'}</td>
                  <td className="px-2 py-1">{i.tipo === 'asn' ? <Link to={`/asn/${i.recurso}`} className="text-primario-600 hover:underline">AS{i.recurso}</Link> : i.tipo === 'bloco' ? <Link to={`/prefixo/${encodeURIComponent(i.recurso)}`} className="text-primario-600 hover:underline">{i.recurso}</Link> : i.recurso}</td>
                  <td className="px-2 py-1 whitespace-nowrap">{data(i.inicio)} a {data(i.fim)}</td><td className="px-2 py-1 text-gray-500">{i.status_delegated ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {meses.length > 0 && (
        <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
          <h2 className="text-base font-semibold text-gray-900">Endereços recuperados e liberados por mês <span className="text-xs font-normal text-gray-500">· blocos do Brasil vistos no delegated</span></h2>
          <table className="text-xs">
            <thead className="text-gray-500"><tr><ThOrdenavel {...porMes.props('mes')} className="text-left px-2 py-1">Mês</ThOrdenavel><ThOrdenavel {...porMes.props('recuperacao')} alinhar="right" className="text-right px-2 py-1">Passaram a reservados</ThOrdenavel><ThOrdenavel {...porMes.props('liberacao')} alinhar="right" className="text-right px-2 py-1">Saíram da reserva</ThOrdenavel></tr></thead>
            <tbody>{meses.map((m) => <tr key={m} className="border-t border-gray-100"><td className="px-2 py-1">{m}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(r.eventos_por_mes[m].recuperacao ?? 0)}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(r.eventos_por_mes[m].liberacao ?? 0)}</td></tr>)}</tbody>
          </table>
        </section>
      )}
    </div>
  )
}

function EspacoSemUso() {
  const date = useActiveDate() ?? undefined
  const { valor, muda, page, setPage } = useFiltrosNaUrl()
  const classe = valor('classe'), uf = valor('uf')
  const setClasse = (v: string) => muda('classe', v), setUf = (v: string) => muda('uf', v)
  const q = useQuery({ queryKey: ['ipv4-espaco', date, classe, uf, page], retry: false, staleTime: 10 * 60 * 1000, queryFn: () => fetchIpv4Espaco({ date, classe: classe || undefined, uf: uf || undefined, limit: 25, page }) })
  const d = q.data
  const classes = useMemo(() => Object.entries(d?.resumo.por_classe ?? {}), [d])
  const porClasse = useOrdenacao(classes, {
    situacao: ([c]) => (c === 'anunciado' ? 'anunciado' : CLASSES_ESPACO[c] ?? c),
    blocos: ([, v]) => v.blocos,
    enderecos: ([, v]) => v.enderecos,
    pct: ([, v]) => v.enderecos,
  })
  if (!d) return <EstadoAba q={q} oQue="o espaço IPv4 alocado" />
  const r = d.resumo
  const ufs = Object.keys(r.por_uf).filter((u) => u !== 'sem_asn').sort()
  return (
    <div className="space-y-4">
      <section className="bg-aviso-50 border border-aviso-200 rounded-lg p-3 text-sm text-aviso-900">
        <strong>Não anunciado não é sem uso.</strong> Rede interna, enlace ponto a ponto, reserva técnica e CGNAT não aparecem na tabela global. Esta lista é inferida do cruzamento entre os blocos do Brasil no delegated e a
        tabela de origens do snapshot ({d.duracao.tabelas_anteriores_consultadas.length} tabelas anteriores consultadas para a duração; a tabela é semanal).
      </section>
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
        <p className="text-sm text-gray-700">{inteiro(r.total_blocos)} blocos IPv4 do Brasil ({inteiro(r.total_enderecos)} endereços). Foto do delegated de {data(d.ultima_foto)}.</p>
        <table className="text-xs">
          <thead className="text-gray-500"><tr><ThOrdenavel {...porClasse.props('situacao')} className="text-left px-2 py-1">Situação</ThOrdenavel><ThOrdenavel {...porClasse.props('blocos')} alinhar="right" className="text-right px-2 py-1">Blocos</ThOrdenavel><ThOrdenavel {...porClasse.props('enderecos')} alinhar="right" className="text-right px-2 py-1">Endereços</ThOrdenavel><ThOrdenavel {...porClasse.props('pct')} alinhar="right" className="text-right px-2 py-1">%</ThOrdenavel></tr></thead>
          <tbody>
            {porClasse.ordenados.map(([c, v]) => (
              <tr key={c} className="border-t border-gray-100"><td className="px-2 py-1">{c === 'anunciado' ? 'anunciado' : CLASSES_ESPACO[c] ?? c}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(v.blocos)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{inteiro(v.enderecos)}</td><td className="px-2 py-1 text-right tabular-nums text-gray-500">{(100 * v.enderecos / r.total_enderecos).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%</td></tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-sm text-gray-600 flex flex-col">Situação
            <select value={classe} onChange={(e) => { setClasse(e.target.value) }} className="border border-gray-300 rounded px-2 py-1.5 text-sm"><option value="">todas</option>{Object.entries(CLASSES_ESPACO).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
          <label className="text-sm text-gray-600 flex flex-col">UF do titular
            <select value={uf} onChange={(e) => { setUf(e.target.value) }} className="border border-gray-300 rounded px-2 py-1.5 text-sm"><option value="">todas</option>{ufs.map((u) => <option key={u} value={u}>{u}</option>)}</select></label>
        </div>
        <div className="overflow-x-auto">
          <table className="text-xs min-w-full">
            <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Bloco</th><th className="text-right px-2 py-1">Endereços</th><th className="text-left px-2 py-1">Situação</th><th className="text-left px-2 py-1">Titular</th><th className="text-left px-2 py-1">UF</th><th className="text-left px-2 py-1">Sem anúncio</th></tr></thead>
            <tbody>
              {d.items.map((b) => (
                <tr key={b.inicio} className="border-t border-gray-100">
                  <td className="px-2 py-1"><Link to={`/prefixo/${encodeURIComponent(`${b.inicio}/${32 - Math.ceil(Math.log2(b.quantidade))}`)}`} className="text-primario-600 hover:underline">{b.inicio}</Link></td>
                  <td className="px-2 py-1 text-right tabular-nums">{inteiro(b.quantidade)}</td><td className="px-2 py-1">{CLASSES_ESPACO[b.classe] ?? b.classe}{b.classe === 'parcial' ? ` (${b.anunciado_pct.toLocaleString('pt-BR')}%)` : ''}</td>
                  <td className="px-2 py-1">{b.asn ? <Link to={`/asn/${b.asn}`} className="text-primario-600 hover:underline">AS{b.asn}</Link> : '—'} <span className="text-gray-500">{b.org ?? ''}</span></td><td className="px-2 py-1">{b.uf ?? '—'}</td>
                  <td className="px-2 py-1 text-gray-500 whitespace-nowrap">{b.tabelas_sem_anuncio ? `${b.tabelas_sem_anuncio} tabela${b.tabelas_sem_anuncio > 1 ? 's' : ''} (desde ${data(b.sem_anuncio_desde)})` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center gap-3 text-sm text-gray-600">
          <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="px-2 py-1 border border-gray-300 rounded disabled:opacity-40">Anterior</button>
          <span>{inteiro(d.total)} blocos · página {page} de {Math.max(1, Math.ceil(d.total / 25))}</span>
          <button disabled={page * 25 >= d.total} onClick={() => setPage(page + 1)} className="px-2 py-1 border border-gray-300 rounded disabled:opacity-40">Próxima</button>
        </div>
      </section>
    </div>
  )
}

function UsoPorTerceiros() {
  const date = useActiveDate() ?? undefined
  const { valor, muda, page, setPage } = useFiltrosNaUrl()
  const sinal = valor('sinal'), confianca = valor('confianca')
  const setSinal = (v: string) => muda('sinal', v), setConfianca = (v: string) => muda('confianca', v)
  const q = useQuery({ queryKey: ['ipv4-uso', date, sinal, confianca, page], retry: false, staleTime: 10 * 60 * 1000, queryFn: () => fetchIpv4UsoPorTerceiros({ date, sinal: sinal || undefined, confianca: confianca || undefined, limit: 25, page }) })
  const d = q.data
  if (!d) return <EstadoAba q={q} oQue="o uso por terceiros" />
  return (
    <div className="space-y-4">
      <section className="bg-aviso-50 border border-aviso-200 rounded-lg p-3 text-sm text-aviso-900">
        <strong>Hipótese de uso por terceiros, não aluguel.</strong> Cada sinal pode ter explicação legítima: o caso comum é o provedor que anuncia o bloco do cliente. A regra e os falsos positivos de cada sinal estão abaixo; nenhuma intenção é atribuída.
      </section>
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
        <h2 className="text-base font-semibold text-gray-900">Sinais <span className="text-xs font-normal text-gray-500">· {inteiro(d.total)} de {inteiro(d.blocos_avaliados)} blocos têm ao menos um</span></h2>
        <ul className="text-sm space-y-1">
          {Object.entries(d.sinais).map(([id, s]) => (
            <li key={id}><span className="font-medium">{id} {s.nome}</span> <span className="text-gray-500">{s.avaliado ? `· ${inteiro(d.por_sinal[id] ?? 0)} blocos` : '· não avaliado'}</span>
              <div className="text-xs text-gray-500">{s.avaliado ? `Falso positivo conhecido: ${s.falsos_positivos}` : s.motivo}</div></li>
          ))}
        </ul>
      </section>
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-sm text-gray-600 flex flex-col">Sinal
            <select value={sinal} onChange={(e) => { setSinal(e.target.value) }} className="border border-gray-300 rounded px-2 py-1.5 text-sm"><option value="">todos</option>{['S1', 'S2', 'S3', 'S4'].map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
          <label className="text-sm text-gray-600 flex flex-col">Confiança
            <select value={confianca} onChange={(e) => { setConfianca(e.target.value) }} className="border border-gray-300 rounded px-2 py-1.5 text-sm"><option value="">todas</option>{['alta', 'media', 'baixa'].map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
        </div>
        <ul className="text-xs divide-y divide-gray-100">
          {d.items.map((i) => (
            <li key={i.inicio} className="py-2">
              <Link to={`/prefixo/${encodeURIComponent(`${i.inicio}/${32 - Math.ceil(Math.log2(i.quantidade))}`)}`} className="font-medium text-primario-600 hover:underline">{i.inicio}</Link> <span className="text-gray-500">({inteiro(i.quantidade)} endereços, {i.classe.replace('_', ' ')})</span>
              {' '}· titular {i.titular ? <><Link to={`/asn/${i.titular.asn}`} className="text-primario-600 hover:underline">AS{i.titular.asn}</Link> <span className="text-gray-500">{i.titular.org}</span></> : 'sem ASN'} · confiança <strong>{i.confianca}</strong>
              <ul className="text-gray-600 list-disc ml-5">{i.sinais.map((s) => <li key={s.id}><span className="font-medium">{s.id}</span> {s.evidencia}</li>)}</ul>
            </li>
          ))}
        </ul>
        <div className="flex items-center gap-3 text-sm text-gray-600">
          <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="px-2 py-1 border border-gray-300 rounded disabled:opacity-40">Anterior</button>
          <span>{inteiro(d.total)} blocos · página {page} de {Math.max(1, Math.ceil(d.total / 25))}</span>
          <button disabled={page * 25 >= d.total} onClick={() => setPage(page + 1)} className="px-2 py-1 border border-gray-300 rounded disabled:opacity-40">Próxima</button>
        </div>
      </section>
    </div>
  )
}

const VALIDACOES_ROTULO: Record<string, string> = { receptor_origina: 'origina', tem_roa: 'ROA', tamanho: '/24 a /22', receptor_ipv6: 'IPv6', prazo_3_anos: '3 anos', nao_infra_critica: 'não crítica' }

/** Sub-asignações (aluguel regulado, LAC-2025-5): enquanto não houver bitácora oficial, explica o que falta e mostra o vigia dos diretórios; com a fonte, lista os registros com as validações. */
function Subasignacoes() {
  const date = useActiveDate() ?? undefined
  const q = useQuery({ queryKey: ['ipv4-subasignacoes', date], retry: false, staleTime: 10 * 60 * 1000, queryFn: () => fetchIpv4Subasignacoes({ date, limit: 100 }) })
  const d = q.data
  if (!d) return <EstadoAba q={q} oQue="as sub-asignações" />
  return (
    <div className="space-y-4">
      {d.aguardando && (
        <section className="bg-aviso-50 border border-aviso-200 rounded-lg p-4 space-y-2 text-sm text-aviso-900">
          <h2 className="text-base font-semibold">Aguardando a publicação oficial</h2>
          <p>{d.aviso}</p>
        </section>
      )}
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
        <h2 className="text-base font-semibold text-gray-900">Vigia dos diretórios</h2>
        <p className="text-sm text-gray-600">Última varredura: {data(d.vigia.ultima_varredura)}. {d.vigia.alertas_30_dias.length === 0 ? 'Nenhum arquivo novo nem mudança de formato nos últimos 30 dias.' : `${d.vigia.alertas_30_dias.length} alertas nos últimos 30 dias:`}</p>
        {d.vigia.alertas_30_dias.length > 0 && <ul className="text-xs text-gray-600 list-disc ml-5">{d.vigia.alertas_30_dias.map((a, i) => <li key={i}>{data(a.data)}: {a.tipo.replace('_', ' ')} {a.nome ?? a.padrao ?? ''} <span className="text-gray-400">{a.url}</span></li>)}</ul>}
        <p className="text-xs text-gray-500">{d.politica.nome}: {d.politica.estado}. Fonte oficial: {d.politica.fonte_oficial}.</p>
      </section>
      {!d.aguardando && (
        <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
          <p className="text-sm text-gray-700">{d.total} sub-asignações. Anúncios de terceiros: {d.indicador_terceiros.com_registro ?? '—'} com registro oficial e {d.indicador_terceiros.sem_registro ?? '—'} sem. {d.indicador_terceiros.nota}</p>
          <table className="text-xs min-w-full">
            <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Bloco</th><th className="text-left px-2 py-1">Receptor</th><th className="text-left px-2 py-1">Período</th>{Object.keys(d.validacoes).map((k) => <th key={k} className="text-center px-2 py-1" title={d.validacoes[k]}>{VALIDACOES_ROTULO[k] ?? k}</th>)}</tr></thead>
            <tbody>
              {d.items.map((s) => (
                <tr key={s.id} className="border-t border-gray-100">
                  <td className="px-2 py-1">{s.bloco}</td><td className="px-2 py-1"><Link to={`/asn/${s.receptor_asn}`} className="text-primario-600 hover:underline">AS{s.receptor_asn}</Link></td>
                  <td className="px-2 py-1 whitespace-nowrap">{data(s.inicio)} a {s.fim ? data(s.fim) : 'em aberto'}</td>
                  {Object.keys(d.validacoes).map((k) => <td key={k} className="px-2 py-1 text-center">{s.validacoes[k] === true ? 'sim' : s.validacoes[k] === false ? 'não' : <span className="text-gray-400">sem dado</span>}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      {d.esquema_hipotetico && <p className="text-xs text-gray-500">O esquema dos registros é hipotético até o formato oficial ser conhecido; as validações aceitam "sem dado" e nunca inventam resultado.</p>}
    </div>
  )
}

/**
 * `/mercado-ipv4` — Mercado de IPv4: o que o Registro.br e o LACNIC declaram de transferências com o Brasil e o que o `delegated` diário mostra. São diferenças observadas, sem causa nem
 * intenção: não se chama de venda nem de aluguel. Nome de pessoa física provável é omitido; o histórico das listas do Registro.br só existe desde o início da nossa coleta.
 */
export function MercadoIpv4Page() {
  const [params, setParams] = useSearchParams()
  const aba = ABAS.some((a) => a.id === params.get('aba')) ? params.get('aba')! : 'transferencias'
  const date = useActiveDate() ?? undefined
  const meta = useQuery({ queryKey: ['ipv4-mercado', date], queryFn: () => fetchIpv4Mercado(date), staleTime: 10 * 60 * 1000, retry: false })
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Mercado secundário de IPv4</h1>
        <p className="text-sm text-gray-500">Transferências de blocos IPv4 com o Brasil, recursos em recuperação e o ciclo de vida de cada bloco. Fontes: Registro.br e LACNIC.</p>
      </div>
      <BarraDeAbas abas={ABAS} ativa={aba} aoEscolher={(id) => setParams(manterData(params, { aba: id }))} rotulo="Seções do Mercado IPv4" />
      <div role="tabpanel" id={`painel-${aba}`} aria-labelledby={`aba-${aba}`} className="space-y-5">
      {aba === 'transferencias' && <Transferencias />}
      {aba === 'recuperacao' && <Recuperacao />}
      {aba === 'espaco' && <EspacoSemUso />}
      {aba === 'terceiros' && <UsoPorTerceiros />}
      {aba === 'subasignacoes' && <Subasignacoes />}
      </div>
      {meta.data && <p className="text-xs text-gray-500">{meta.data.limites} Os mesmos dados estão na API (<code>/ipv4/transferencias</code>) e nas coleções <code>transferencias_ipv4</code>, <code>recuperacao_ipv4</code> e <code>eventos_bloco</code> da consulta.</p>}
    </div>
  )
}
