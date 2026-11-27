// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Link } from '../components/layout/LinkDatado'
import { fetchDemandaOferta, fetchCeticEstimativas, fetchCeticIndicadores, fetchCeticTabelas } from '../services/api'
import type { CeticLinha } from '../types/api'
import { BarrasRecorte, recortesDaColuna } from '../features/cetic/BarrasRecorte'
import { CartogramaIndicador } from '../features/estados/CartogramaIndicador'
import { CLASSES, inteiro as inteiroDO, intervaloRazao, razao } from '../features/uf/blocks/DemandaOfertaUfBloco'
import { SITE } from '../lib/site'
import { useOrdenacao } from '../lib/ordenacao'
import { ThOrdenavel } from '../components/ui/ThOrdenavel'
import { EstadoDados, ehErroDeAcessoOuFalha } from '../components/ui/EstadoDados'
import { TEXTO_ZERO_REGISTRADO, estadoMargem } from '../features/cetic/margem'
import { ApresentacaoRecolhida } from '../components/ui/FontesEDatas'
import { SinteseCetic } from '../features/cetic/BlocoSinteseCetic'
import { useActiveDate } from '../hooks/useSnapshot'

const PESQUISAS = [
  { id: 'domicilios', rotulo: 'TIC Domicílios', descricao: 'Uso de internet e equipamentos nos domicílios brasileiros' },
  { id: 'provedores', rotulo: 'TIC Provedores', descricao: 'Pequenos provedores de acesso à Internet (autodeclaração)' },
]

const pct = (v: number | null) => (v == null ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }))
const inteiro = (v: number | null) => (v == null ? '—' : Math.round(v).toLocaleString('pt-BR'))

/** Pivô de uma tabela: linhas = recortes (dimensão + categoria), colunas = item × resposta, na ordem em que aparecem na planilha. */
function pivo(linhas: CeticLinha[]) {
  const colunas: string[] = []
  const recortes: string[] = []
  const celulas = new Map<string, CeticLinha>()
  for (const l of linhas) {
    const col = l.item ? `${l.item}: ${l.resposta}` : l.resposta
    const rec = `${l.dimensao}|${l.recorte}`
    if (!colunas.includes(col)) colunas.push(col)
    if (!recortes.includes(rec)) recortes.push(rec)
    celulas.set(`${rec}||${col}`, l)
  }
  return { colunas, recortes, celulas }
}

/** Estimativas por UF: do Arandurapé, sobre os microdados da TIC Domicílios, com a margem de erro; rotuladas como derivadas. */
function EstimativasUf() {
  const date = useActiveDate() ?? undefined
  const q = useQuery({ queryKey: ['cetic-estimativas', date], queryFn: () => fetchCeticEstimativas({ date }), staleTime: 10 * 60 * 1000, retry: false })
  const [indicador, setIndicador] = useState('internet')
  // Linhas com a estimativa do indicador escolhido: a lista muda com o indicador e a ordem por coluna é refeita sobre ela.
  const linhas = useMemo(() => (q.data?.items ?? []).map((g) => ({ g, e: g.indicadores[indicador] ?? {} })), [q.data, indicador])
  const { ordenados, props } = useOrdenacao(linhas, {
    grupo: (l) => l.g.grupo, proporcao: (l) => (l.e.suprimido ? null : l.e.proporcao), margem: (l) => (l.e.suprimido ? null : l.e.margem),
    total: (l) => l.e.total, n: (l) => l.g.n,
  })
  if (!q.data) return q.isError && ehErroDeAcessoOuFalha(q.error) ? <EstadoDados erro={q.error} oQue="as estimativas por UF" /> : null
  const c = q.data
  const grupos = c.items
  return (
    <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
      <div>
        <h2 className="text-base font-semibold text-gray-900">Por UF: estimativa do {SITE.nome} <span className="text-xs font-normal text-gray-500">· derivada dos microdados, não é número do Cetic.br</span></h2>
        <p className="text-xs text-gray-500">{c.aviso}</p>
      </div>
      <label className="text-sm text-gray-600 flex flex-col w-fit">Indicador
        <select value={indicador} onChange={(e) => setIndicador(e.target.value)} className="border border-gray-300 rounded px-2 py-1.5 text-sm">
          {Object.entries(c.indicadores).map(([id, i]) => <option key={id} value={id}>{i.rotulo}</option>)}
        </select>
      </label>
      {c.indicadores[indicador]?.definicao && (
        <p className="text-xs text-gray-600" data-testid="definicao-indicador">
          {c.indicadores[indicador].definicao}{indicador === 'banda_larga_fixa' && ' Não é o mesmo denominador da tabela A5 do Cetic.br (domicílios com Internet): a mesma ideia, com outra base, dá outro percentual.'}
        </p>
      )}
      <CartogramaIndicador
        indicadores={[{ id: indicador, rotulo: c.indicadores[indicador]?.rotulo ?? indicador, maximo: 100, texto: (v) => `${Math.round(v)}%`,
          valor: (uf) => { const e = grupos.find((g) => g.tipo === 'uf' && g.grupo === uf)?.indicadores[indicador]; return e && !e.suprimido ? e.proporcao ?? null : null } }]}
        verDados={
      <div className="overflow-x-auto">
        <table className="text-xs min-w-full">
          <caption className="sr-only">Estimativa por grupo</caption>
          <thead className="text-gray-500"><tr><ThOrdenavel {...props('grupo')} className="text-left px-2 py-1">Grupo</ThOrdenavel><ThOrdenavel {...props('proporcao')} alinhar="right" className="text-right px-2 py-1">%</ThOrdenavel><ThOrdenavel {...props('margem')} alinhar="right" className="text-right px-2 py-1">Margem (95%)</ThOrdenavel><ThOrdenavel {...props('total')} alinhar="right" className="text-right px-2 py-1">Domicílios estimados</ThOrdenavel><ThOrdenavel {...props('n')} alinhar="right" className="text-right px-2 py-1">Entrevistados</ThOrdenavel></tr></thead>
          <tbody>
            {ordenados.map(({ g, e }) => {
              return (
                <tr key={g.grupo} className="border-t border-gray-100">
                  <td className="px-2 py-1">{g.tipo === 'uf' ? <Link to={`/uf/${g.grupo}`} className="text-primario-600 hover:underline">{g.grupo}</Link> : g.grupo}{g.tipo !== 'uf' && <span className="text-gray-400"> ({g.tipo === 'brasil' ? 'Brasil' : 'região'})</span>}</td>
                  {e.suprimido ? <td colSpan={2} className="px-2 py-1 text-right text-gray-400">suprimido ({e.suprimido})</td> : (
                    <><td className="px-2 py-1 text-right tabular-nums">{pct(e.proporcao ?? null)}</td><td className="px-2 py-1 text-right tabular-nums text-gray-500">±{pct(e.margem ?? null)}{e.precisao === 'baixa' ? ' · precisão baixa' : ''}</td></>
                  )}
                  <td className="px-2 py-1 text-right tabular-nums">{inteiro(e.total ?? null)}</td>
                  <td className="px-2 py-1 text-right tabular-nums text-gray-500">{inteiro(g.n)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
        }
      />
      {c.validacao && (
        <p className="text-xs text-gray-500">
          Conferência com as tabelas oficiais ({c.validacao.comparados} recortes: Brasil e regiões, A1 e A4): a estimativa pontual difere em até {c.validacao.diferenca_max_proporcao_pp.toLocaleString('pt-BR')} ponto percentual; a
          margem oficial é de {c.validacao.razao_margem_oficial_min?.toLocaleString('pt-BR')} a {c.validacao.razao_margem_oficial_max?.toLocaleString('pt-BR')} vez a estimada aqui.
        </p>
      )}
    </section>
  )
}

/** Demanda × oferta de banda larga fixa por UF: estimativa do Arandurapé, com intervalo de 95% e a leitura (classe). */
function DemandaOfertaUfs() {
  const date = useActiveDate() ?? undefined
  const q = useQuery({ queryKey: ['demanda-oferta', date], queryFn: () => fetchDemandaOferta(date), staleTime: 10 * 60 * 1000, retry: false })
  const grupos = useMemo(() => {
    const d = q.data
    return d ? [{ id: 'Brasil', tipo: 'brasil', l: d.brasil }, ...Object.entries(d.regioes).map(([id, l]) => ({ id, tipo: 'regiao', l })), ...Object.entries(d.ufs).map(([id, l]) => ({ id, tipo: 'uf', l }))] : []
  }, [q.data])
  const { ordenados, props } = useOrdenacao(grupos, {
    grupo: (g) => g.id, demanda: (g) => g.l.demanda_domicilios, oferta: (g) => g.l.oferta_acessos_pf, razao: (g) => g.l.razao,
    intervalo: (g) => g.l.razao_min, nao_visto: (g) => g.l.nao_visto, leitura: (g) => CLASSES[g.l.classe].rotulo,
  })
  if (!q.data) return q.isError && ehErroDeAcessoOuFalha(q.error) ? <EstadoDados erro={q.error} oQue="a demanda e a oferta por UF" /> : null
  const d = q.data
  return (
    <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
      <div>
        <h2 className="text-base font-semibold text-gray-900">Demanda × oferta de banda larga fixa <span className="text-xs font-normal text-gray-500">· estimativa do {SITE.nome} (TIC × IBGE × SICI)</span></h2>
        <p className="text-xs text-gray-500">{d.limites}</p>
      </div>
      <CartogramaIndicador
        indicadores={[{ id: 'razao', rotulo: 'Razão oferta ÷ demanda', texto: (v) => v.toLocaleString('pt-BR', { maximumFractionDigits: 1 }),
          nota: 'Acessos fixos de pessoa física ÷ domicílios com demanda estimada. Estimativa com intervalo de 95% (na tabela); a leitura por classe também está nela.',
          valor: (uf) => d.ufs[uf]?.razao ?? null }]}
        verDados={
      <div className="overflow-x-auto">
        <table className="text-xs min-w-full">
          <caption className="sr-only">Demanda e oferta por grupo</caption>
          <thead className="text-gray-500"><tr><ThOrdenavel {...props('grupo')} className="text-left px-2 py-1">Grupo</ThOrdenavel><ThOrdenavel {...props('demanda')} alinhar="right" className="text-right px-2 py-1">Demanda (domicílios)</ThOrdenavel><ThOrdenavel {...props('oferta')} alinhar="right" className="text-right px-2 py-1">Oferta (acessos PF)</ThOrdenavel><ThOrdenavel {...props('razao')} alinhar="right" className="text-right px-2 py-1">Razão</ThOrdenavel><ThOrdenavel {...props('intervalo')} alinhar="right" className="text-right px-2 py-1">Intervalo (95%)</ThOrdenavel><ThOrdenavel {...props('nao_visto')} alinhar="right" className="text-right px-2 py-1">Não visto</ThOrdenavel><ThOrdenavel {...props('leitura')} className="text-left px-2 py-1">Leitura</ThOrdenavel></tr></thead>
          <tbody>
            {ordenados.map(({ id, tipo, l }) => (
              <tr key={id} className="border-t border-gray-100">
                <td className="px-2 py-1">{tipo === 'uf' ? <Link to={`/uf/${id}`} className="text-primario-600 hover:underline">{id}</Link> : id}{tipo === 'regiao' && <span className="text-gray-400"> (região)</span>}</td>
                <td className="px-2 py-1 text-right tabular-nums">{inteiroDO(l.demanda_domicilios)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{inteiroDO(l.oferta_acessos_pf)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{razao(l.razao)}</td>
                <td className="px-2 py-1 text-right tabular-nums text-gray-500">{intervaloRazao(l)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{inteiroDO(l.nao_visto)}</td>
                <td className={`px-2 py-1 ${CLASSES[l.classe].cor}`} title={l.motivo}>{CLASSES[l.classe].rotulo}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
        }
      />
      <p className="text-xs text-gray-500">TIC Domicílios {d.tic_edicao} · SICI de {d.mes_referencia_sici ?? 's/d'} · intervalo {d.intervalo}. API: <code>/mercado/demanda-oferta</code>; coleção <code>demanda_oferta</code> da consulta.</p>
    </section>
  )
}

/**
 * `/uso-da-internet` — Uso da Internet: as tabelas oficiais da TIC Domicílios e da TIC Provedores do Cetic.br|NIC.br, sem alterar nenhum número.
 * São estimativas amostrais: a margem de erro aparece junto de cada valor, e a edição (ano) e a citação ficam sempre visíveis. O recorte mais fino é a grande região.
 */
export function UsoInternetPage() {
  const date = useActiveDate() ?? undefined
  // a pesquisa é uma aba na URL (`?aba=domicilios|provedores`): o link guarda a escolha e recarregar não a perde
  const [sp, setSp] = useSearchParams()
  const pesquisa = PESQUISAS.find((p) => p.id === sp.get('aba'))?.id ?? 'domicilios'
  const setPesquisa = (id: string) => setSp((prev) => { const q = new URLSearchParams(prev); q.set('aba', id); return q }, { replace: true })
  const [tabela, setTabela] = useState('')
  const [medida, setMedida] = useState<'proporcao' | 'total'>('proporcao')
  const [coluna, setColuna] = useState('')
  // a tabela larga abre sozinha no desktop e fica recolhida no celular, onde o gráfico por recorte é a leitura principal
  const [tabelaAberta, setTabelaAberta] = useState(() => typeof window === 'undefined' || typeof window.matchMedia !== 'function' || window.matchMedia('(min-width: 768px)').matches)
  const tabelas = useQuery({ queryKey: ['cetic-tabelas', date, pesquisa], queryFn: () => fetchCeticTabelas({ date, pesquisa }), staleTime: 10 * 60 * 1000, retry: false })
  const itens = tabelas.data?.items ?? []
  const escolhida = itens.find((t) => t.tabela === tabela) ?? itens[0]
  const dados = useQuery({
    queryKey: ['cetic-indicadores', date, pesquisa, escolhida?.tabela], enabled: !!escolhida,
    queryFn: () => fetchCeticIndicadores({ date, pesquisa, tabela: escolhida!.tabela }), staleTime: 10 * 60 * 1000, retry: false,
  })
  const meta = tabelas.data
  const { colunas, recortes, celulas } = pivo(dados.data?.items ?? [])
  const colunaEf = colunas.includes(coluna) ? coluna : colunas[0] ?? ''

  return (
    <ApresentacaoRecolhida>
    <div className="space-y-5">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Uso da Internet</h1>
        <p className="text-sm text-gray-500 mt-1">
          Tabelas oficiais das pesquisas TIC do Cetic.br|NIC.br, como publicadas: proporções e totais estimados por uma amostra, sempre com a margem de erro. Não são
          contagens e o recorte mais fino é a grande região. Os números não foram alterados pelo {SITE.nome}.
        </p>
      </div>

      <SinteseCetic aoAbrirTabela={(p, t) => { setPesquisa(p); setTabela(t) }} />

      <div className="flex flex-wrap gap-3 items-end">
        <div role="group" aria-label="Pesquisa" className="flex gap-1">
          {PESQUISAS.map((p) => (
            <button key={p.id} type="button" aria-pressed={pesquisa === p.id} aria-describedby={pesquisa === p.id ? 'pesquisa-descricao' : undefined}
              onClick={() => { setPesquisa(p.id); setTabela('') }} title={p.descricao}
              className={`px-3 py-1.5 text-sm rounded border ${pesquisa === p.id ? 'bg-primario-600 text-white border-primario-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}>
              {p.rotulo}
            </button>
          ))}
        </div>
        {/* a descrição da pesquisa ficava só no title dos botões */}
        <p id="pesquisa-descricao" className="basis-full text-xs text-gray-600">{PESQUISAS.find((p) => p.id === pesquisa)?.descricao}</p>
        <label className="text-sm text-gray-600 flex flex-col">Tabela
          <select value={escolhida?.tabela ?? ''} onChange={(e) => setTabela(e.target.value)} className="border border-gray-300 rounded px-2 py-1.5 text-sm max-w-xl">
            {itens.map((t) => <option key={t.tabela} value={t.tabela}>{t.codigo}: {t.titulo}</option>)}
          </select>
        </label>
        <label className="text-sm text-gray-600 flex flex-col">Mostrar
          <select value={medida} onChange={(e) => setMedida(e.target.value as 'proporcao' | 'total')} className="border border-gray-300 rounded px-2 py-1.5 text-sm">
            <option value="proporcao">Percentual (%)</option>
            <option value="total">Total estimado</option>
          </select>
        </label>
      </div>

      {tabelas.isError && <EstadoDados erro={tabelas.error} oQue="as tabelas do Cetic.br" mensagem="As tabelas do Cetic.br não estão publicadas neste snapshot." aoTentarDeNovo={() => void tabelas.refetch()} />}
      {escolhida && (
        <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
          <div>
            <h2 className="text-base font-semibold text-gray-900">{escolhida.codigo}: {escolhida.titulo}</h2>
            <p className="text-xs text-gray-500">Universo: {escolhida.universo || '—'} · {meta?.pesquisa} {meta?.edicao}</p>
          </div>
          {dados.isLoading && <p className="text-sm text-gray-500">Carregando…</p>}
          {dados.data && colunas.length > 0 && (
            <div className="space-y-2">
              <label className="text-sm text-gray-600 flex flex-col w-fit max-w-full">Coluna no gráfico
                <select value={colunaEf} onChange={(e) => setColuna(e.target.value)} className="border border-gray-300 rounded px-2 py-1.5 text-sm max-w-full">
                  {colunas.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </label>
              <BarrasRecorte recortes={recortesDaColuna(dados.data.items, colunaEf, medida)} medida={medida} coluna={colunaEf} />
            </div>
          )}
          {dados.data && (
            <details open={tabelaAberta} onToggle={(e) => setTabelaAberta((e.currentTarget as HTMLDetailsElement).open)}>
              <summary className="cursor-pointer text-sm text-primario-600 hover:underline">Tabela completa ({recortes.length} recortes × {colunas.length} colunas)</summary>
            <div className="overflow-x-auto mt-2">
              <table className="text-xs min-w-full">
                <caption className="sr-only">{`${escolhida.codigo}: ${escolhida.titulo}`}</caption>
                <thead className="text-gray-500">
                  <tr><th scope="col" className="text-left px-2 py-1">Recorte</th>{colunas.map((c) => <th key={c} scope="col" className="text-right px-2 py-1 font-medium">{c}</th>)}</tr>
                </thead>
                <tbody>
                  {recortes.map((r) => {
                    const [dim, rec] = r.split('|')
                    return (
                      <tr key={r} className="border-t border-gray-100">
                        <th scope="row" className="px-2 py-1 whitespace-nowrap text-left font-normal"><span className="text-gray-500">{dim === 'Total' ? '' : `${dim}: `}</span>{rec}</th>
                        {colunas.map((c) => {
                          const l = celulas.get(`${r}||${c}`)
                          const v = medida === 'proporcao' ? l?.proporcao ?? null : l?.total ?? null
                          const m = medida === 'proporcao' ? l?.margem_proporcao ?? null : l?.margem_total ?? null
                          const estado = estadoMargem(v, m, medida)
                          return (
                            <td key={c} className="px-2 py-1 text-right tabular-nums whitespace-nowrap">
                              {medida === 'proporcao' ? pct(v) : inteiro(v)}
                              {estado === 'zero_registrado'
                                ? <span className="text-gray-500" title={TEXTO_ZERO_REGISTRADO}> ±{'—'}<span className="sr-only"> ({TEXTO_ZERO_REGISTRADO})</span></span>
                                : v != null && m != null && <span className="text-gray-500"> ±{medida === 'proporcao' ? pct(m) : inteiro(m)}</span>}
                              {estado === 'precisao_baixa' && <span className="text-aviso-900"> · precisão baixa</span>}
                            </td>
                          )
                        })}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            {(() => {
              const zeradas = recortes.reduce((n, r) => n + colunas.filter((c) => {
                const l = celulas.get(`${r}||${c}`)
                return medida === 'proporcao' && estadoMargem(l?.proporcao, l?.margem_proporcao, 'proporcao') === 'zero_registrado'
              }).length, 0)
              return zeradas > 0 && (
                <p className="text-xs text-gray-600 mt-1" data-testid="nota-margem-zero">
                  {zeradas.toLocaleString('pt-BR')} {zeradas === 1 ? 'célula tem' : 'células têm'} {TEXTO_ZERO_REGISTRADO}, com proporção entre 0% e
                  100%; numa pesquisa amostral isso não é precisão perfeita, e a margem aparece como "±{'—'}".
                </p>
              )
            })()}
            </details>
          )}
          {escolhida.notas.length > 0 && (
            <ul className="text-xs text-gray-500 space-y-0.5">{escolhida.notas.map((n, i) => <li key={i}>{n}</li>)}</ul>
          )}
        </section>
      )}

      {pesquisa === 'domicilios' && <EstimativasUf />}
      {pesquisa === 'domicilios' && <DemandaOfertaUfs />}

      {meta && (
        <p className="text-xs text-gray-500">
          Fonte: {meta.fonte} · licença {meta.licenca} · <a href={meta.pagina} className="text-primario-600 hover:underline" target="_blank" rel="noopener noreferrer">página da pesquisa</a>.
          {' '}{meta.aviso} Os mesmos dados estão na API (<code>/cetic/indicadores</code>) e na coleção <code>cetic_indicadores</code> da consulta.
        </p>
      )}
    </div>
    </ApresentacaoRecolhida>
  )
}
