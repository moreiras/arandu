// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MapaSobDemanda } from '../features/estados/MapaSobDemanda'
import { INDICADORES_FUST } from '../lib/indicadoresMapa'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import {
  fetchEspectroFaixas, fetchEspectroResumo, fetchFustMunicipios, fetchFustResumo, fetchMultasEmpresas, fetchMultasResumo, fetchSatelitesDireitos, fetchSatelitesResumo,
} from '../services/api'
import type { GrupoServico, RegMeta } from '../types/api'
import { SITE } from '../lib/site'
import { BarraDeAbas } from '../features/entidade/EntityPage'

const ABAS = [
  { id: 'fust', rotulo: 'FUST' },
  { id: 'multas', rotulo: 'Multas' },
  { id: 'espectro', rotulo: 'Espectro' },
  { id: 'satelites', rotulo: 'Satélites' },
]
const GRUPOS: GrupoServico[] = ['SCM', 'SMP', 'STFC', 'SeAC']
const inteiro = (v?: number | null) => (v == null ? '—' : Math.round(v).toLocaleString('pt-BR'))
const reais = (v?: number | null) => (v == null ? '—' : v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }))
const mhz = (v: number) => v.toLocaleString('pt-BR', { maximumFractionDigits: 4 })
const data = (d?: string | null) => (d ? new Date(d + 'T12:00:00').toLocaleDateString('pt-BR') : '—')
const staleTime = 10 * 60 * 1000

function Rodape({ m }: { m: RegMeta }) {
  return <p className="text-xs text-gray-500">Anatel, dados abertos (arquivo de {m.data_arquivo ? new Date(m.data_arquivo).toLocaleDateString('pt-BR') : 'data não informada'}; snapshot {m.snapshot_date}). {m.limites}</p>
}

function Paginacao({ page, total, limit, onPage }: { page: number; total: number; limit: number; onPage: (p: number) => void }) {
  const ultima = Math.max(1, Math.ceil(total / limit))
  return (
    <div className="flex items-center gap-3 text-xs text-gray-600">
      <button disabled={page <= 1} onClick={() => onPage(page - 1)} className="px-2 py-1 border rounded disabled:opacity-40">Anterior</button>
      <span>Página {page} de {ultima} · {inteiro(total)} linhas</span>
      <button disabled={page >= ultima} onClick={() => onPage(page + 1)} className="px-2 py-1 border rounded disabled:opacity-40">Próxima</button>
    </div>
  )
}

function Fust() {
  const [uf, setUf] = useState('')
  const [programa, setPrograma] = useState('')
  const resumo = useQuery({ queryKey: ['fust-resumo'], queryFn: fetchFustResumo, staleTime, retry: false })
  const lista = useQuery({ queryKey: ['fust-municipios-pagina', uf, programa], queryFn: () => fetchFustMunicipios({ uf: uf || undefined, programa: programa || undefined, limit: 15 }), staleTime, retry: false })
  const r = resumo.data
  if (!r) return <p className="text-sm text-gray-500">{resumo.isError ? 'FUST não publicado neste snapshot.' : 'Carregando…'}</p>
  const b = r.brasil
  const ufs = Object.entries(r.ufs).sort((a, c) => c[1].compromissos - a[1].compromissos)
  return (
    <div className="space-y-4">
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
        <div className="flex flex-wrap items-baseline gap-x-8 gap-y-1 text-sm">
          <div><span className="text-2xl font-semibold tabular-nums">{inteiro(b.compromissos)}</span> <span className="text-gray-500">compromissos em {inteiro(b.municipios_com_compromisso)} de {inteiro(b.municipios)} municípios</span></div>
          <div className="text-gray-600">{reais(b.investimento)} de investimento previsto</div>
          <div className="text-gray-600">Atendidos {inteiro(b.atendidos)} · A vencer {inteiro(b.a_vencer)} · Em apuração {inteiro(b.em_apuracao)}</div>
        </div>
        <div className="overflow-x-auto">
          <table className="text-xs min-w-full">
            <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Programa</th><th className="text-right px-2 py-1">Compromissos</th><th className="text-right px-2 py-1">Atendidos</th><th className="text-right px-2 py-1">Municípios</th><th className="text-right px-2 py-1">Previsto</th></tr></thead>
            <tbody>
              {r.programas.map((p) => (
                <tr key={p.codigo} className="border-t border-gray-100"><td className="px-2 py-1">{p.codigo} · {p.nome}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(p.compromissos)}</td>
                  <td className="px-2 py-1 text-right tabular-nums">{inteiro(p.atendidos)}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(p.municipios)}</td><td className="px-2 py-1 text-right tabular-nums">{reais(p.investimento)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <MapaSobDemanda indicadores={INDICADORES_FUST} titulo="Mapa do FUST por município" chamada="Compromissos do FUST por 10 mil habitantes em cada município, sobre a malha do IBGE. Carrega cerca de 0,5 MB." />
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
        <h2 className="text-sm font-semibold text-gray-700">Editais e projetos de origem</h2>
        <table className="text-xs min-w-full">
          <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Origem</th><th className="text-right px-2 py-1">Compromissos</th><th className="text-right px-2 py-1">Municípios</th><th className="text-right px-2 py-1">Previsto</th></tr></thead>
          <tbody>{r.editais.map((e) => <tr key={e.origem} className="border-t border-gray-100"><td className="px-2 py-1">{e.origem}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(e.compromissos)}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(e.municipios)}</td><td className="px-2 py-1 text-right tabular-nums">{reais(e.investimento)}</td></tr>)}</tbody>
        </table>
      </section>
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
        <h2 className="text-sm font-semibold text-gray-700">Municípios com mais compromissos</h2>
        <div className="flex flex-wrap gap-3">
          <label className="text-sm text-gray-600 flex flex-col">UF
            <select value={uf} onChange={(e) => setUf(e.target.value)} className="border border-gray-300 rounded px-2 py-1.5 text-sm"><option value="">Todas</option>{ufs.map(([u]) => <option key={u} value={u}>{u}</option>)}</select></label>
          <label className="text-sm text-gray-600 flex flex-col">Programa
            <select value={programa} onChange={(e) => setPrograma(e.target.value)} className="border border-gray-300 rounded px-2 py-1.5 text-sm"><option value="">Todos</option>{r.programas.map((p) => <option key={p.codigo} value={p.codigo}>{p.codigo} · {p.nome}</option>)}</select></label>
        </div>
        {lista.data && (
          <table className="text-xs min-w-full">
            <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Município</th><th className="text-right px-2 py-1">Compromissos</th><th className="text-right px-2 py-1">Atendidos</th><th className="text-right px-2 py-1">Previsto</th></tr></thead>
            <tbody>{lista.data.items.map((m) => <tr key={m.ibge} className="border-t border-gray-100"><td className="px-2 py-1"><Link to={`/municipio/${m.ibge}`} className="text-primario-600 hover:underline">{m.nome ?? m.ibge}</Link> <span className="text-gray-400">{m.uf}</span></td>
              <td className="px-2 py-1 text-right tabular-nums">{inteiro(m.compromissos)}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(m.atendidos)}</td><td className="px-2 py-1 text-right tabular-nums">{reais(m.investimento)}</td></tr>)}</tbody>
          </table>
        )}
      </section>
      <Rodape m={r} />
    </div>
  )
}

function Multas() {
  const [grupo, setGrupo] = useState('')
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const resumo = useQuery({ queryKey: ['multas-resumo'], queryFn: fetchMultasResumo, staleTime, retry: false })
  const lista = useQuery({ queryKey: ['multas-empresas', grupo, q, page], queryFn: () => fetchMultasEmpresas({ grupo: grupo || undefined, q: q || undefined, limit: 20, page }), staleTime, retry: false })
  const r = resumo.data
  if (!r) return <p className="text-sm text-gray-500">{resumo.isError ? 'Multas não publicadas neste snapshot.' : 'Carregando…'}</p>
  const anos = [...r.por_ano].reverse().slice(0, 12)
  return (
    <div className="space-y-4">
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
        <div className="flex flex-wrap items-baseline gap-x-8 gap-y-1 text-sm">
          <div><span className="text-2xl font-semibold tabular-nums">{inteiro(r.brasil.multas)}</span> <span className="text-gray-500">multas constituídas contra {inteiro(r.brasil.empresas)} empresas/serviços</span></div>
          <div className="text-gray-600">Saldo devedor atualizado {reais(r.brasil.saldo)} · original {reais(r.brasil.original)} · pago {reais(r.brasil.pago)}</div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {GRUPOS.map((g) => r.por_grupo[g] && (
            <div key={g} className="border border-gray-100 rounded p-2 text-sm"><div className="font-medium">{g}</div><div className="tabular-nums">{inteiro(r.por_grupo[g].multas)} multas</div><div className="text-xs text-gray-500">{inteiro(r.por_grupo[g].empresas)} empresas · saldo {reais(r.por_grupo[g].saldo)}</div></div>
          ))}
        </div>
        <table className="text-xs min-w-full">
          <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Ano da sanção</th>{GRUPOS.map((g) => <th key={g} className="text-right px-2 py-1">{g}</th>)}<th className="text-right px-2 py-1">Total</th></tr></thead>
          <tbody>{anos.map((a) => <tr key={a.ano} className="border-t border-gray-100"><td className="px-2 py-1 font-medium">{a.ano}</td>{GRUPOS.map((g) => <td key={g} className="px-2 py-1 text-right tabular-nums">{inteiro(a[g] ?? 0)}</td>)}<td className="px-2 py-1 text-right tabular-nums">{inteiro(a.total)}</td></tr>)}</tbody>
        </table>
      </section>
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
        <div className="flex flex-wrap gap-3">
          <label className="text-sm text-gray-600 flex flex-col">Serviço
            <select value={grupo} onChange={(e) => { setGrupo(e.target.value); setPage(1) }} className="border border-gray-300 rounded px-2 py-1.5 text-sm"><option value="">Todos</option>{GRUPOS.map((g) => <option key={g} value={g}>{g}</option>)}</select></label>
          <label className="text-sm text-gray-600 flex flex-col">Empresa ou raiz do CNPJ
            <input value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} className="border border-gray-300 rounded px-2 py-1.5 text-sm" /></label>
        </div>
        {lista.data && (
          <>
            <div className="overflow-x-auto">
              <table className="text-xs min-w-full">
                <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Empresa</th><th className="text-left px-2 py-1">Serviço</th><th className="text-right px-2 py-1">Multas</th><th className="text-right px-2 py-1">Devedor</th><th className="text-right px-2 py-1">Saldo atualizado</th><th className="text-left px-2 py-1">Anos</th></tr></thead>
                <tbody>{lista.data.items.map((e) => (
                  <tr key={`${e.raiz}-${e.grupo}`} className="border-t border-gray-100">
                    <td className="px-2 py-1">{e.cnpj_matriz ? <Link to={`/operadora/${e.cnpj_matriz}`} className="text-primario-600 hover:underline">{e.entidade}</Link> : e.entidade}</td>
                    <td className="px-2 py-1">{e.grupo}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(e.multas)}</td>
                    <td className="px-2 py-1 text-right tabular-nums">{inteiro((e.situacoes.Devedor ?? 0) + (e.situacoes.Parcial ?? 0))}</td><td className="px-2 py-1 text-right tabular-nums">{reais(e.saldo)}</td>
                    <td className="px-2 py-1">{e.primeiro_ano === e.ultimo_ano ? e.primeiro_ano : `${e.primeiro_ano}–${e.ultimo_ano}`}</td></tr>))}</tbody>
              </table>
            </div>
            <Paginacao page={page} total={lista.data.total} limit={20} onPage={setPage} />
          </>
        )}
      </section>
      <p className="text-xs text-gray-500">Lidas {inteiro(r.leitura.linhas)} multas; {inteiro(r.leitura.pessoa_fisica)} de pessoa física e {inteiro(r.leitura.fora_do_escopo)} de outros serviços (ou sem serviço) não são publicadas.</p>
      <Rodape m={r} />
    </div>
  )
}

function Espectro() {
  const [de, setDe] = useState('')
  const [ate, setAte] = useState('')
  const [servico, setServico] = useState('')
  const [page, setPage] = useState(1)
  const resumo = useQuery({ queryKey: ['espectro-resumo'], queryFn: fetchEspectroResumo, staleTime, retry: false })
  const lista = useQuery({
    queryKey: ['espectro-faixas', de, ate, servico, page], staleTime, retry: false,
    queryFn: () => fetchEspectroFaixas({ de: de ? Number(de.replace(',', '.')) : undefined, ate: ate ? Number(ate.replace(',', '.')) : undefined, servico: servico || undefined, limit: 25, page }),
  })
  const r = resumo.data
  if (!r) return <p className="text-sm text-gray-500">{resumo.isError ? 'Faixas não publicadas neste snapshot.' : 'Carregando…'}</p>
  return (
    <div className="space-y-4">
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
        <h2 className="text-sm font-semibold text-gray-700">Faixas de interesse para a Internet</h2>
        <div className="overflow-x-auto">
          <table className="text-xs min-w-full">
            <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Faixa</th><th className="text-right px-2 py-1">MHz</th><th className="text-left px-2 py-1">Destinação (primária primeiro)</th></tr></thead>
            <tbody>{r.referencias.map((f) => (
              <tr key={f.nome} className="border-t border-gray-100 align-top"><td className="px-2 py-1 font-medium whitespace-nowrap">{f.nome}</td><td className="px-2 py-1 text-right tabular-nums whitespace-nowrap">{mhz(f.ini_mhz)}–{mhz(f.fim_mhz)}</td>
                <td className="px-2 py-1">{f.destinacao.length ? f.destinacao.map((s) => <span key={s.servico} className={`inline-block mr-2 ${s.carater === 'Primário' ? '' : 'text-gray-400'}`}>{s.servico}</span>) : '—'}</td></tr>))}</tbody>
          </table>
        </div>
        <p className="text-xs text-gray-500">Cinza = destinação secundária. Os nomes das faixas são referência do {SITE.nome}, não nomes oficiais.</p>
      </section>
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">Quadro de atribuição e destinação ({inteiro(r.resumo.faixas)} faixas)</h2>
        <div className="flex flex-wrap gap-3">
          <label className="text-sm text-gray-600 flex flex-col">De (MHz)<input value={de} onChange={(e) => { setDe(e.target.value); setPage(1) }} inputMode="decimal" className="border border-gray-300 rounded px-2 py-1.5 text-sm w-28" /></label>
          <label className="text-sm text-gray-600 flex flex-col">Até (MHz)<input value={ate} onChange={(e) => { setAte(e.target.value); setPage(1) }} inputMode="decimal" className="border border-gray-300 rounded px-2 py-1.5 text-sm w-28" /></label>
          <label className="text-sm text-gray-600 flex flex-col">Serviço<input value={servico} onChange={(e) => { setServico(e.target.value); setPage(1) }} placeholder="ex.: móvel pessoal" className="border border-gray-300 rounded px-2 py-1.5 text-sm" /></label>
        </div>
        {lista.data && (
          <>
            <table className="text-xs min-w-full">
              <thead className="text-gray-500"><tr><th className="text-right px-2 py-1">Faixa (MHz)</th><th className="text-left px-2 py-1">Destinação</th><th className="text-left px-2 py-1">Atribuição</th></tr></thead>
              <tbody>{lista.data.items.map((f) => (
                <tr key={`${f.ini_mhz}-${f.fim_mhz}`} className="border-t border-gray-100 align-top"><td className="px-2 py-1 text-right tabular-nums whitespace-nowrap">{mhz(f.ini_mhz)}–{mhz(f.fim_mhz)}</td>
                  <td className="px-2 py-1">{f.destinacao.map((s) => <span key={s.servico} className={`inline-block mr-2 ${s.carater === 'Primário' ? '' : 'text-gray-400'}`}>{s.servico}</span>)}</td>
                  <td className="px-2 py-1">{f.atribuicao.map((s) => <span key={s.servico} className={`inline-block mr-2 ${s.carater === 'Primário' ? '' : 'text-gray-400'}`}>{s.servico}</span>)}</td></tr>))}</tbody>
            </table>
            <Paginacao page={page} total={lista.data.total} limit={25} onPage={setPage} />
          </>
        )}
      </section>
      <Rodape m={r} />
    </div>
  )
}

function Satelites() {
  const [operadora, setOperadora] = useState('')
  const [tipo, setTipo] = useState('')
  const [page, setPage] = useState(1)
  const resumo = useQuery({ queryKey: ['satelites-resumo'], queryFn: fetchSatelitesResumo, staleTime, retry: false })
  const lista = useQuery({ queryKey: ['satelites-direitos', operadora, tipo, page], queryFn: () => fetchSatelitesDireitos({ operadora: operadora || undefined, tipo: tipo || undefined, limit: 20, page }), staleTime, retry: false })
  const r = resumo.data
  if (!r) return <p className="text-sm text-gray-500">{resumo.isError ? 'Satélites não publicados neste snapshot.' : 'Carregando…'}</p>
  const s = r.resumo
  return (
    <div className="space-y-4">
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
        <div className="flex flex-wrap items-baseline gap-x-8 gap-y-1 text-sm">
          <div><span className="text-2xl font-semibold tabular-nums">{inteiro(s.direitos)}</span> <span className="text-gray-500">direitos de exploração · {inteiro(s.satelites)} satélites · {inteiro(s.operadoras)} operadoras</span></div>
          <div className="text-gray-600">{Object.entries(s.por_tipo).map(([k, v]) => `${k} ${inteiro(v)}`).join(' · ')}</div>
          <div className="text-gray-600">{inteiro(s.vencidos_na_data)} com validade vencida na data do snapshot</div>
        </div>
        <h2 className="text-sm font-semibold text-gray-700 pt-2">Constelações de órbita não geoestacionária ({inteiro(s.ngeo)})</h2>
        <div className="overflow-x-auto"><table className="text-xs min-w-full">
          <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Sistema</th><th className="text-left px-2 py-1">Prestadora</th><th className="text-left px-2 py-1">Órbita</th><th className="text-right px-2 py-1">Satélites</th><th className="text-left px-2 py-1">Situação</th></tr></thead>
          <tbody>{r.ngeo.map((n, i) => <tr key={`${n.estacao}-${i}`} className="border-t border-gray-100"><td className="px-2 py-1">{n.objeto}</td><td className="px-2 py-1">{n.prestadora}</td><td className="px-2 py-1">{n.orbita}</td>
            <td className="px-2 py-1 text-right tabular-nums">{inteiro(n.constelacao)}</td><td className="px-2 py-1">{n.status}</td></tr>)}</tbody>
        </table></div>
      </section>
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
        <div className="flex flex-wrap gap-3">
          <label className="text-sm text-gray-600 flex flex-col">Operadora ou satélite<input value={operadora} onChange={(e) => { setOperadora(e.target.value); setPage(1) }} className="border border-gray-300 rounded px-2 py-1.5 text-sm" /></label>
          <label className="text-sm text-gray-600 flex flex-col">Tipo
            <select value={tipo} onChange={(e) => { setTipo(e.target.value); setPage(1) }} className="border border-gray-300 rounded px-2 py-1.5 text-sm"><option value="">Todos</option>{Object.keys(s.por_tipo).map((t) => <option key={t} value={t}>{t}</option>)}</select></label>
        </div>
        {lista.data && (
          <>
            <div className="overflow-x-auto"><table className="text-xs min-w-full">
              <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Operadora</th><th className="text-left px-2 py-1">Satélite</th><th className="text-left px-2 py-1">Posição</th><th className="text-left px-2 py-1">Banda</th><th className="text-left px-2 py-1">Tipo</th><th className="text-left px-2 py-1">Status</th><th className="text-left px-2 py-1">Validade</th></tr></thead>
              <tbody>{lista.data.items.map((d, i) => <tr key={`${d.codigo}-${d.banda}-${i}`} className="border-t border-gray-100"><td className="px-2 py-1">{d.operadora}</td><td className="px-2 py-1">{d.satelite}</td><td className="px-2 py-1">{d.posicao}</td>
                <td className="px-2 py-1">{d.banda}</td><td className="px-2 py-1">{d.tipo}</td><td className="px-2 py-1">{d.status}</td><td className={`px-2 py-1 ${d.vencido ? 'text-perigo-700' : ''}`}>{data(d.validade)}{d.vencido ? ' (vencida)' : ''}</td></tr>)}</tbody>
            </table></div>
            <Paginacao page={page} total={lista.data.total} limit={20} onPage={setPage} />
          </>
        )}
      </section>
      <Rodape m={r} />
    </div>
  )
}

/**
 * `/regulatorio` — Regulatório complementar: FUST, multas, quadro de frequências e satélites, tudo de dados abertos da Anatel. São cadastros e normas, não desembolso, condenação nem licença
 * por operadora: cada aba repete o que o dado é e não é.
 */
export function RegulatorioPage() {
  const [params, setParams] = useSearchParams()
  const aba = ABAS.some((a) => a.id === params.get('aba')) ? params.get('aba')! : 'fust'
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Regulatório</h1>
        <p className="text-sm text-gray-500">FUST, multas constituídas, quadro de frequências e satélites com direito de exploração no Brasil. Fonte: dados abertos da Anatel.</p>
      </div>
      <BarraDeAbas abas={ABAS} ativa={aba} aoEscolher={(id) => setParams({ aba: id })} rotulo="Seções do Regulatório" />
      <div role="tabpanel" id={`painel-${aba}`} aria-labelledby={`aba-${aba}`} className="space-y-5">
      {aba === 'fust' && <Fust />}
      {aba === 'multas' && <Multas />}
      {aba === 'espectro' && <Espectro />}
      {aba === 'satelites' && <Satelites />}
      </div>
    </div>
  )
}
