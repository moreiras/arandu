// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { lazy, Suspense, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { fetchConsumidorMarcas, fetchConsumidorResumo, fetchQualidadePrestadoras, fetchQualidadeResumo, fetchQualidadeSerie, fetchReclamacoesMarcas, fetchReclamacoesResumo } from '../services/api'
import { EstadoDados } from '../components/ui/EstadoDados'
import type { QualIndicador } from '../types/api'
import { BulletPrestadoras } from '../features/qualidade/BulletPrestadoras'
import { arquivo, dec, inteiro, NotaQualidade, referencia } from '../features/qualidade/blocos'
import { CabecalhoMetricas, CelulasMetricas, NotaConsumidor } from '../features/qualidade/consumidor'
import { BarraDeAbas } from '../features/entidade/EntityPage'

const ABAS = [
  { id: 'indicadores', rotulo: 'Indicadores (RQUAL)' },
  { id: 'reclamacoes', rotulo: 'Reclamações' },
  { id: 'consumidor', rotulo: 'Consumidor.gov.br' },
]
const SERVICOS = ['Banda Larga Fixa', 'Telefonia Fixa', 'Telefonia Móvel']
const SERVICOS_RECL = ['SCM', 'SMP_Pós', 'SMP_Pré', 'STFC', 'SeAC', 'Outros']
const UFS = ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO']
const staleTime = 10 * 60 * 1000
const MapaQualidade = lazy(() => import('../features/qualidade/MapaQualidade'))

/** O mapa pesa cerca de 0,5 MB (MapLibre e tiles): só carrega quando a pessoa pede, como nas demais páginas (orçamento). */
/** Link para a operadora: o nome da empresa quando a API o devolve; sem nome, a raiz do CNPJ (o CNPJ completo fica no title). */
function EmpresaLink({ cnpj, nomes }: { cnpj: string; nomes?: Record<string, string> }) {
  return <Link to={`/operadora/${cnpj}`} title={`CNPJ ${cnpj}`} className="text-primario-600 hover:underline mr-2">{nomes?.[cnpj] ?? cnpj.slice(0, 8)}</Link>
}

function MapaQualidadeSobDemanda({ servico, indicador }: { servico: string; indicador: QualIndicador }) {
  const [aberto, setAberto] = useState(false)
  if (!aberto) return <button type="button" onClick={() => setAberto(true)} className="rounded-md border border-primario-300 bg-primario-50 px-3 py-1.5 text-sm text-primario-700 hover:bg-primario-100">Mostrar o mapa deste indicador por município (carrega cerca de 0,5 MB)</button>
  return <Suspense fallback={<p className="text-sm text-gray-400" role="status">Carregando o mapa…</p>}><MapaQualidade servico={servico} indicador={indicador} /></Suspense>
}

function Indicadores() {
  const [servico, setServico] = useState(SERVICOS[0])
  const [indicador, setIndicador] = useState('')
  const [uf, setUf] = useState('')
  const resumo = useQuery({ queryKey: ['qualidade-resumo'], queryFn: fetchQualidadeResumo, staleTime, retry: false })
  const inds = useMemo(() => (resumo.data?.indicadores ?? []).filter((i) => i.servico === servico), [resumo.data, servico])
  const ind = indicador && inds.some((i) => i.codigo === indicador) ? indicador : (inds[0]?.codigo ?? '')
  const pres = useQuery({
    queryKey: ['qualidade-prestadoras', servico, ind, uf], enabled: !!ind,
    queryFn: () => fetchQualidadePrestadoras({ servico, indicador: ind, uf: uf || undefined }), staleTime, retry: false,
  })
  const serie = useQuery({
    queryKey: ['qualidade-serie', servico, ind, uf], enabled: !!ind,
    queryFn: () => fetchQualidadeSerie({ servico, indicador: ind, uf: uf || undefined }), staleTime, retry: false,
  })
  const r = resumo.data
  if (!r) return resumo.isError ? <EstadoDados erro={resumo.error} oQue="os indicadores do RQUAL" mensagem="RQUAL não publicado neste snapshot." aoTentarDeNovo={() => void resumo.refetch()} /> : <p className="text-sm text-gray-500">Carregando…</p>
  const eixo: 'mes' | 'ano' = uf ? 'ano' : 'mes'
  const periodos = [...new Set((serie.data?.items ?? []).map((x) => String((x as unknown as Record<string, unknown>)[eixo])))].sort().slice(-12)
  const nomes = [...new Set((serie.data?.items ?? []).map((x) => x.prestadora))].sort()
  const valor = (p: string, per: string) => {
    const x = (serie.data?.items ?? []).find((y) => y.prestadora === p && String((y as unknown as Record<string, unknown>)[eixo]) === per)
    return x ? (x.media_ponderada ?? x.media) : null
  }
  const refInd = inds.find((i) => i.codigo === ind)
  return (
    <div className="space-y-4">
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
        <div className="flex flex-wrap items-baseline gap-x-8 gap-y-1 text-sm">
          <div><span className="text-2xl font-semibold tabular-nums">{inteiro(r.leitura.resultados_numericos)}</span> <span className="text-gray-500">resultados numéricos em {inteiro(r.leitura.municipios_com_resultado)} municípios, {r.leitura.mes_inicial} a {r.leitura.mes_final}</span></div>
          <div className="text-gray-600">{r.casamento.com_cnpj} de {r.casamento.prestadoras} prestadoras ligadas a um CNPJ (tabela curada de {r.casamento.tabela_curada.curada_em})</div>
        </div>
        <p className="text-xs text-gray-600">Sem ranking: as prestadoras aparecem em ordem alfabética e cada indicador mostra a referência da própria Anatel. O RQUAL cobre só as grandes prestadoras de cada serviço; a ausência de uma empresa não diz nada sobre ela.</p>
      </section>
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
        <div className="flex flex-wrap gap-3">
          <label className="text-sm text-gray-600 flex flex-col">Serviço
            <select value={servico} onChange={(e) => { setServico(e.target.value); setIndicador('') }} className="border border-gray-300 rounded px-2 py-1.5 text-sm">{SERVICOS.map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
          <label className="text-sm text-gray-600 flex flex-col">Indicador
            <select value={ind} onChange={(e) => setIndicador(e.target.value)} className="border border-gray-300 rounded px-2 py-1.5 text-sm">{inds.map((i) => <option key={i.codigo} value={i.codigo}>{i.codigo} · {i.descricao}</option>)}</select></label>
          <label className="text-sm text-gray-600 flex flex-col">UF
            <select value={uf} onChange={(e) => setUf(e.target.value)} className="border border-gray-300 rounded px-2 py-1.5 text-sm"><option value="">Brasil</option>{UFS.map((u) => <option key={u} value={u}>{u}</option>)}</select></label>
        </div>
        {refInd && <p className="text-xs text-gray-600">{refInd.descricao} ({refInd.tipo}, {refInd.grupo}); unidade {refInd.unidade}; referência da Anatel (superior / inferior): {referencia(refInd)}. O sentido de melhor ou pior depende do indicador e não é interpretado aqui.</p>}
        {refInd && <MapaQualidadeSobDemanda servico={servico} indicador={refInd} />}
        {pres.data && refInd && <BulletPrestadoras indicador={refInd} linhas={pres.data.items.map((x) => ({ prestadora: x.prestadora, valor: x.media_ponderada ?? x.media ?? null }))} />}
        {pres.data && (
          <div className="overflow-x-auto">
            <table className="text-xs min-w-full">
              <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Prestadora (alfabética)</th><th className="text-left px-2 py-1">{uf ? 'Ano' : 'Mês'}</th><th className="text-right px-2 py-1">Municípios medidos</th><th className="text-right px-2 py-1">Medidas</th>
                <th className="text-right px-2 py-1">Média ponderada</th><th className="text-right px-2 py-1">Média simples</th><th className="text-right px-2 py-1">Mediana</th><th className="text-left px-2 py-1">CNPJ</th></tr></thead>
              <tbody>
                {pres.data.items.map((x) => {
                  const p = r.prestadoras.find((y) => y.servico === servico && y.prestadora === x.prestadora)
                  return (
                    <tr key={x.prestadora} className="border-t border-gray-100">
                      <td className="px-2 py-1">{x.prestadora}</td><td className="px-2 py-1">{pres.data.periodo.mes ?? pres.data.periodo.ano}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(x.municipios)}</td>
                      <td className="px-2 py-1 text-right tabular-nums">{inteiro(x.medidas)}</td><td className="px-2 py-1 text-right tabular-nums">{dec(x.media_ponderada, 2)} {pres.data.indicador.unidade}</td>
                      <td className="px-2 py-1 text-right tabular-nums">{dec(x.media, 2)}</td><td className="px-2 py-1 text-right tabular-nums">{'mediana' in x ? dec(x.mediana, 2) : '—'}</td>
                      <td className="px-2 py-1">{p?.cnpjs_matriz?.length ? p.cnpjs_matriz.map((c) => <EmpresaLink key={c} cnpj={c} nomes={r.nomes} />) : <span className="text-gray-400">sem CNPJ ligado</span>}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
        {periodos.length > 0 && (
          <details className="text-xs"><summary className="cursor-pointer text-gray-600">Série ({uf ? 'anual da UF' : 'mensal nacional'}, últimos {periodos.length} períodos, média ponderada)</summary>
            <div className="overflow-x-auto">
              <table className="text-xs min-w-full">
                <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Período</th>{nomes.map((n) => <th key={n} className="text-right px-2 py-1">{n}</th>)}</tr></thead>
                <tbody>{periodos.map((per) => <tr key={per} className="border-t border-gray-100"><td className="px-2 py-1">{per}</td>{nomes.map((n) => <td key={n} className="px-2 py-1 text-right tabular-nums">{dec(valor(n, per), 2)}</td>)}</tr>)}</tbody>
              </table>
            </div>
          </details>
        )}
        {r.casamento.sem_cnpj.length > 0 && <p className="text-xs text-gray-500">Prestadoras sem CNPJ ligado (nome sem casamento seguro): {r.casamento.sem_cnpj.join(', ')}.</p>}
      </section>
      <NotaQualidade m={r} />
    </div>
  )
}

function Reclamacoes() {
  const [servico, setServico] = useState('')
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const resumo = useQuery({ queryKey: ['reclamacoes-resumo'], queryFn: fetchReclamacoesResumo, staleTime, retry: false })
  const lista = useQuery({
    queryKey: ['reclamacoes-marcas', servico, q, page], enabled: !!resumo.data,
    queryFn: () => fetchReclamacoesMarcas({ servico: servico || undefined, q: q || undefined, limit: 25, page }), staleTime, retry: false,
  })
  const r = resumo.data
  if (!r) return resumo.isError ? <EstadoDados erro={resumo.error} oQue="as reclamações" mensagem="Reclamações não publicadas neste snapshot." aoTentarDeNovo={() => void resumo.refetch()} /> : <p className="text-sm text-gray-500">Carregando…</p>
  const anos = [...new Set(r.por_ano_servico.map((x) => x.ano))].sort((a, b) => b - a).slice(0, 8)
  const servicos = SERVICOS_RECL.filter((s) => r.por_ano_servico.some((x) => x.servico === s))
  const cel = (ano: number, s: string) => r.por_ano_servico.find((x) => x.ano === ano && x.servico === s)?.reclamacoes ?? 0
  const ultima = Math.max(1, Math.ceil((lista.data?.total ?? 0) / 25))
  return (
    <div className="space-y-4">
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
        <div className="flex flex-wrap items-baseline gap-x-8 gap-y-1 text-sm">
          <div><span className="text-2xl font-semibold tabular-nums">{inteiro(r.leitura.reclamacoes)}</span> <span className="text-gray-500">reclamações desde {r.leitura.anos[0]} em {inteiro(r.leitura.municipios)} municípios</span></div>
          <div className="text-gray-600">{dec(r.casamento.pct_com_cnpj, 1)}% das reclamações com CNPJ ligado ({inteiro(r.casamento.marcas_com_cnpj)} de {inteiro(r.casamento.marcas)} marcas; tabela curada de {r.casamento.tabela_curada.curada_em})</div>
        </div>
        <p className="text-xs text-gray-600">Só agregados da própria Anatel: nenhum texto livre nem dado de quem reclamou. Sem ranking: a lista de marcas é alfabética e o número de reclamações depende do tamanho da base de clientes; reclamação não é prova de falha da empresa.</p>
        <div className="overflow-x-auto">
          <table className="text-xs min-w-full">
            <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Ano</th>{servicos.map((s) => <th key={s} className="text-right px-2 py-1">{s}</th>)}</tr></thead>
            <tbody>{anos.map((a) => <tr key={a} className="border-t border-gray-100"><td className="px-2 py-1">{a}</td>{servicos.map((s) => <td key={s} className="px-2 py-1 text-right tabular-nums">{inteiro(cel(a, s))}</td>)}</tr>)}</tbody>
          </table>
        </div>
        <p className="text-xs text-gray-500">Arquivos: {Object.entries(r.leitura.arquivos).map(([n, a]) => `${n} (${a.mes_inicial} a ${a.mes_final})`).join('; ')}. O ano mais recente pode estar incompleto.</p>
      </section>
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
        <h2 className="text-sm font-semibold text-gray-700">Marcas em {lista.data?.ano ?? r.leitura.anos[r.leitura.anos.length - 1]} (ordem alfabética)</h2>
        <div className="flex flex-wrap gap-3">
          <label className="text-sm text-gray-600 flex flex-col">Serviço
            <select value={servico} onChange={(e) => { setServico(e.target.value); setPage(1) }} className="border border-gray-300 rounded px-2 py-1.5 text-sm"><option value="">Todos</option>{servicos.map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
          <label className="text-sm text-gray-600 flex flex-col">Buscar marca
            <input value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} placeholder="ex.: vivo" className="border border-gray-300 rounded px-2 py-1.5 text-sm" /></label>
        </div>
        {lista.data && (
          <div className="overflow-x-auto">
            <table className="text-xs min-w-full">
              <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Marca</th><th className="text-right px-2 py-1">Reclamações</th><th className="text-left px-2 py-1">Por serviço</th><th className="text-left px-2 py-1">CNPJ ligado</th><th className="text-right px-2 py-1">Por mil acessos</th></tr></thead>
              <tbody>
                {lista.data.items.map((m) => (
                  <tr key={m.marca} className="border-t border-gray-100">
                    <td className="px-2 py-1">{m.marca}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(m.reclamacoes)}</td>
                    <td className="px-2 py-1">{Object.entries(m.por_servico).sort().map(([s, n]) => `${s} ${inteiro(n)}`).join(' · ')}</td>
                    <td className="px-2 py-1">{m.cnpjs_matriz.length ? m.cnpjs_matriz.map((c) => <EmpresaLink key={c} cnpj={c} nomes={lista.data?.nomes} />) : <span className="text-gray-400">sem CNPJ ligado</span>}
                      {m.casamento && <span className="text-gray-400"> ({m.casamento})</span>}</td>
                    <td className="px-2 py-1 text-right tabular-nums">{m.taxas.filter((t) => t.por_mil_acessos != null).map((t) => `${t.grupo} ${dec(t.por_mil_acessos, 2)}`).join(' · ') || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="flex items-center gap-3 text-xs text-gray-600">
          <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="px-2 py-1 border rounded disabled:opacity-40">Anterior</button>
          <span>Página {page} de {ultima} · {inteiro(lista.data?.total)} marcas</span>
          <button disabled={page >= ultima} onClick={() => setPage(page + 1)} className="px-2 py-1 border rounded disabled:opacity-40">Próxima</button>
        </div>
        <p className="text-xs text-gray-500">Por mil acessos: {r.taxas.regra}. Janela {r.taxas.janela ? `${r.taxas.janela.de} a ${r.taxas.janela.ate}` : '—'}; SICI de {r.taxas.sici_mes_referencia.SCM ?? '—'} (fixo) e {r.taxas.sici_mes_referencia.SMP ?? '—'} (móvel).</p>
      </section>
      {r.assuntos_ano.ano && (
        <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
          <h2 className="text-sm font-semibold text-gray-700">Assuntos em {r.assuntos_ano.ano}</h2>
          <ul className="text-xs columns-1 md:columns-2 gap-6">{[...r.assuntos_ano.itens].sort((a, b) => b.reclamacoes - a.reclamacoes).slice(0, 20).map((x) => <li key={`${x.servico}-${x.assunto}`} className="flex justify-between gap-4"><span>{x.servico} · {x.assunto}</span><span className="tabular-nums text-gray-600">{inteiro(x.reclamacoes)}</span></li>)}</ul>
        </section>
      )}
      <p className="text-xs text-gray-500">Anatel, dados abertos (arquivo de {arquivo(r)}; snapshot {r.snapshot_date}). {r.limites}</p>
    </div>
  )
}

function Consumidor() {
  const [uf, setUf] = useState('')
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const resumo = useQuery({ queryKey: ['consumidor-resumo'], queryFn: fetchConsumidorResumo, staleTime, retry: false })
  const lista = useQuery({
    queryKey: ['consumidor-marcas', uf, q, page], enabled: !!resumo.data,
    queryFn: () => fetchConsumidorMarcas({ uf: uf || undefined, q: q || undefined, limit: 25, page }), staleTime, retry: false,
  })
  const r = resumo.data
  if (!r) return resumo.isError ? <EstadoDados erro={resumo.error} oQue="os dados do Consumidor.gov.br" mensagem="Consumidor.gov.br não publicado neste snapshot." aoTentarDeNovo={() => void resumo.refetch()} /> : <p className="text-sm text-gray-500">Carregando…</p>
  const ultima = Math.max(1, Math.ceil((lista.data?.total ?? 0) / 25))
  const meses = r.setor_por_mes.slice(-12)
  return (
    <div className="space-y-4">
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
        <div className="flex flex-wrap items-baseline gap-x-8 gap-y-1 text-sm">
          <div><span className="text-2xl font-semibold tabular-nums">{inteiro(r.casamento.reclamacoes_janela)}</span> <span className="text-gray-500">reclamações finalizadas de operadoras, {r.janela.de} a {r.janela.ate}</span></div>
          <div className="text-gray-600">{dec(r.casamento.pct_com_cnpj, 1)}% com CNPJ ligado ({inteiro(r.casamento.marcas_com_cnpj)} de {inteiro(r.casamento.marcas)} empresas); {dec(r.cidades.pct_com_codigo_ibge, 1)}% com município no IBGE</div>
        </div>
        <p className="text-xs text-gray-600">Reclamações finalizadas no Consumidor.gov.br (Senacon), só agregados: sexo e faixa etária de quem reclamou não são guardados. Sem ranking: a lista é alfabética, o número de reclamações depende do tamanho da base de clientes e só empresas que aderiram à plataforma aparecem. Índice de solução, tempo e nota só com 30 ou mais casos.</p>
        <div className="overflow-x-auto">
          <table className="text-xs min-w-full">
            <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Mês (todas as operadoras)</th><CabecalhoMetricas /></tr></thead>
            <tbody>{meses.map((x) => <tr key={x.mes} className="border-t border-gray-100"><td className="px-2 py-1">{x.mes}</td><CelulasMetricas x={x} /></tr>)}</tbody>
          </table>
        </div>
      </section>
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
        <h2 className="text-sm font-semibold text-gray-700">Empresas, {r.janela.de} a {r.janela.ate} (ordem alfabética)</h2>
        <div className="flex flex-wrap gap-3">
          <label className="text-sm text-gray-600 flex flex-col">UF
            <select value={uf} onChange={(e) => { setUf(e.target.value); setPage(1) }} className="border border-gray-300 rounded px-2 py-1.5 text-sm"><option value="">Brasil</option>{UFS.map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
          <label className="text-sm text-gray-600 flex flex-col">Buscar empresa
            <input value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} placeholder="ex.: claro" className="border border-gray-300 rounded px-2 py-1.5 text-sm" /></label>
        </div>
        {lista.data && (
          <div className="overflow-x-auto">
            <table className="text-xs min-w-full">
              <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Empresa</th><CabecalhoMetricas /><th className="text-left px-2 py-1">CNPJ ligado</th></tr></thead>
              <tbody>
                {lista.data.items.map((m) => (
                  <tr key={m.marca} className="border-t border-gray-100">
                    <td className="px-2 py-1">{m.marca}</td><CelulasMetricas x={m} />
                    <td className="px-2 py-1">{m.cnpjs_matriz.length ? m.cnpjs_matriz.map((c) => <EmpresaLink key={c} cnpj={c} nomes={lista.data.nomes} />) : <span className="text-gray-400">sem CNPJ ligado</span>}
                      {m.casamento && <span className="text-gray-400"> ({m.casamento})</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="flex items-center gap-3 text-xs text-gray-600">
          <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="px-2 py-1 border rounded disabled:opacity-40">Anterior</button>
          <span>Página {page} de {ultima} · {inteiro(lista.data?.total)} empresas</span>
          <button disabled={page >= ultima} onClick={() => setPage(page + 1)} className="px-2 py-1 border rounded disabled:opacity-40">Próxima</button>
        </div>
      </section>
      <NotaConsumidor m={r} janela={r.janela} />
    </div>
  )
}

/** Qualidade e reclamações da Anatel: fatos medidos ou declarados, com fonte e período; sem ranking nem veredito. */
export function QualidadePage() {
  const [params, setParams] = useSearchParams()
  const aba = ABAS.some((a) => a.id === params.get('aba')) ? (params.get('aba') as string) : 'indicadores'
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Qualidade e reclamações</h1>
        <p className="text-sm text-gray-500">Indicadores de qualidade (RQUAL), reclamações de consumidores registradas na Anatel e reclamações finalizadas no Consumidor.gov.br. Fatos com fonte e período, sem ranking nem veredito.</p>
      </div>
      {/* a barra de abas única do site (setas do teclado, estado em ?aba=). */}
      <BarraDeAbas abas={ABAS} ativa={aba} aoEscolher={(id) => setParams(id === 'indicadores' ? {} : { aba: id })} rotulo="Seções de Qualidade" />
      <div role="tabpanel" id={`painel-${aba}`} aria-labelledby={`aba-${aba}`}>
        {aba === 'indicadores' ? <Indicadores /> : aba === 'reclamacoes' ? <Reclamacoes /> : <Consumidor />}
      </div>
    </div>
  )
}
