// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { BlocoProps } from '../entidade/registry'
import type { MunicipioCtx } from '../municipio/contexto'
import type { OperadoraCtx } from '../operadora/contexto'
import type { UfCtx } from '../uf/contexto'
import type { QualIndicador, QualMeta, ReclTaxa } from '../../types/api'

export const inteiro = (v?: number | null) => (v == null ? '—' : Math.round(v).toLocaleString('pt-BR'))
export const dec = (v?: number | null, casas = 1) => (v == null ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas }))
export const arquivo = (m: QualMeta) => (m.data_arquivo ? new Date(m.data_arquivo).toLocaleDateString('pt-BR') : 'data não informada')

/** O que o dado é e não é, sempre junto do número (fonte, data do arquivo e limites). */
export function NotaQualidade({ m }: { m: QualMeta }) {
  return <p className="text-xs text-gray-500">Anatel, dados abertos (arquivo de {arquivo(m)}; snapshot {m.snapshot_date}). {m.limites}</p>
}

/** Referência da Anatel do indicador, sem interpretar o sentido. */
export function referencia(i?: QualIndicador): string {
  if (!i || (!i.referencia_superior && !i.referencia_inferior)) return '—'
  return `${i.referencia_superior ?? '—'} / ${i.referencia_inferior ?? '—'}`
}

export const chaveInd = (servico: string, codigo: string) => `${servico}|${codigo}`
export const mapaInd = (lista: QualIndicador[]) => new Map(lista.map((i) => [chaveInd(i.servico, i.codigo), i]))

function TituloInd({ i, codigo }: { i?: QualIndicador; codigo: string }) {
  return <span title={codigo}>{i ? i.descricao : codigo} <span className="text-gray-400">{codigo}</span></span>
}

/** RQUAL das prestadoras ligadas ao CNPJ: o último mês nacional de cada indicador (média dos municípios medidos). */
export function QualidadeOperadoraBloco({ dados }: BlocoProps<OperadoraCtx>) {
  const q = dados.qualidade
  const inds = useMemo(() => mapaInd(q?.indicadores ?? []), [q])
  if (!q) return null
  return (
    <div className="space-y-3">
      {q.prestadoras.map((p) => {
        const linhas = q.itens.filter((x) => x.servico === p.servico && x.prestadora === p.prestadora)
        const iqs = linhas.filter((x) => inds.get(chaveInd(x.servico, x.indicador))?.tipo === 'Indicador IQS')
        const info = linhas.filter((x) => inds.get(chaveInd(x.servico, x.indicador))?.tipo !== 'Indicador IQS')
        const tabela = (itens: typeof linhas) => (
          <table className="text-xs min-w-full">
            <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Indicador</th><th className="text-left px-2 py-1">Mês</th><th className="text-right px-2 py-1">Municípios medidos</th>
              <th className="text-right px-2 py-1">Média ponderada</th><th className="text-right px-2 py-1">Média simples</th><th className="text-right px-2 py-1">Mediana</th><th className="text-left px-2 py-1">Referência Anatel</th></tr></thead>
            <tbody>
              {itens.map((x) => {
                const i = inds.get(chaveInd(x.servico, x.indicador))
                return (
                  <tr key={x.indicador} className="border-t border-gray-100">
                    <td className="px-2 py-1"><TituloInd i={i} codigo={x.indicador} /></td><td className="px-2 py-1">{x.mes}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(x.municipios)}</td>
                    <td className="px-2 py-1 text-right tabular-nums">{dec(x.media_ponderada, 2)} {i?.unidade}</td><td className="px-2 py-1 text-right tabular-nums">{dec(x.media, 2)}</td>
                    <td className="px-2 py-1 text-right tabular-nums">{dec(x.mediana, 2)}</td><td className="px-2 py-1">{referencia(i)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )
        return (
          <div key={`${p.servico}-${p.prestadora}`} className="space-y-1">
            <h3 className="text-sm font-medium text-gray-700">{p.servico} · prestadora {p.prestadora} <span className="text-xs font-normal text-gray-500">({inteiro(p.municipios)} municípios medidos · ligação ao CNPJ: {p.casamento})</span></h3>
            <div className="overflow-x-auto">{tabela(iqs)}</div>
            {info.length > 0 && <details className="text-xs"><summary className="cursor-pointer text-gray-600">Indicadores informativos ({info.length})</summary><div className="overflow-x-auto">{tabela(info)}</div></details>}
          </div>
        )
      })}
      <p className="text-xs text-gray-500">Valores nacionais da prestadora (não do CNPJ isolado): média dos municípios medidos, ponderada pelas medidas quando a Anatel as informa. A base de cada ligação está em <Link to="/qualidade" className="text-primario-600 hover:underline">Qualidade</Link>.</p>
      <NotaQualidade m={q} />
    </div>
  )
}

/** RQUAL no município: o último resultado de cada indicador por prestadora, com medidas, erro amostral e intervalo. */
export function QualidadeMunicipioBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const q = dados.qualidade
  const inds = useMemo(() => mapaInd(q?.indicadores ?? []), [q])
  if (!q) return null
  // Resumo: um quadro por serviço, indicadores nas linhas e prestadoras nas colunas, no lugar de uma tabela recolhida por prestadora.
  const servicos = [...new Set(q.prestadoras.map((p) => p.servico))].sort()
  return (
    <div className="space-y-4" data-testid="rqual-resumo">
      {servicos.map((sv) => {
        const prest = q.prestadoras.filter((p) => p.servico === sv).sort((a, b) => a.prestadora.localeCompare(b.prestadora))
        const codigos = [...new Set(prest.flatMap((p) => p.itens.map((x) => x.indicador)))].sort()
        return (
          <div key={sv} className="overflow-x-auto">
            <h3 className="text-sm font-medium text-gray-700 mb-1">{sv} <span className="text-xs font-normal text-gray-500">({prest.length} prestadora{prest.length === 1 ? '' : 's'}, {codigos.length} indicadores)</span></h3>
            <table className="text-xs min-w-full" data-tabela="grade">
              <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Indicador</th>{prest.map((p) => <th key={p.prestadora} className="text-right px-2 py-1">{p.prestadora}</th>)}<th className="text-left px-2 py-1">Referência Anatel</th></tr></thead>
              <tbody>
                {codigos.map((c) => {
                  const i = inds.get(chaveInd(sv, c))
                  return (
                    <tr key={c} className="border-t border-gray-100">
                      <td className="px-2 py-1"><TituloInd i={i} codigo={c} /></td>
                      {prest.map((p) => {
                        const x = p.itens.find((it) => it.indicador === c)
                        const detalhe = x ? `mês ${x.mes}; ${inteiro(x.medidas)} medidas${x.erro_amostral == null ? '' : `; erro amostral ${dec(x.erro_amostral, 2)}`}${x.limite_inferior == null ? '' : `; intervalo ${dec(x.limite_inferior, 1)} a ${dec(x.limite_superior, 1)}`}` : ''
                        return <td key={p.prestadora} title={detalhe} className="px-2 py-1 text-right tabular-nums">{x ? `${dec(x.resultado, 2)} ${i?.unidade ?? ''}` : '—'}</td>
                      })}
                      <td className="px-2 py-1">{referencia(i)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )
      })}
      <p className="text-xs text-gray-500">Passe o mouse (ou toque) no valor para ver o mês, o número de medidas, o erro amostral e o intervalo.</p>
      <NotaQualidade m={q} />
    </div>
  )
}

/** RQUAL na UF: o último ano de cada prestadora num indicador escolhido (ordem alfabética, sem ranking). */
export function QualidadeUfBloco({ dados }: BlocoProps<UfCtx>) {
  const q = dados.qualidade
  const servicos = useMemo(() => [...new Set((q?.itens ?? []).map((x) => x.servico))].sort(), [q])
  const [servico, setServico] = useState('')
  const [indicador, setIndicador] = useState('')
  if (!q) return null
  const sv = servico || servicos[0] || ''
  const indsDoServico = q.indicadores.filter((i) => i.servico === sv && q.itens.some((x) => x.servico === sv && x.indicador === i.codigo))
  const ind = indicador && indsDoServico.some((i) => i.codigo === indicador) ? indicador : (indsDoServico[0]?.codigo ?? '')
  const ref = q.indicadores.find((i) => i.servico === sv && i.codigo === ind)
  const linhas = q.itens.filter((x) => x.servico === sv && x.indicador === ind).sort((a, b) => a.prestadora.localeCompare(b.prestadora))
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-3">
        <label className="text-sm text-gray-600 flex flex-col">Serviço
          <select value={sv} onChange={(e) => { setServico(e.target.value); setIndicador('') }} className="border border-gray-300 rounded px-2 py-1.5 text-sm">{servicos.map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
        <label className="text-sm text-gray-600 flex flex-col">Indicador
          <select value={ind} onChange={(e) => setIndicador(e.target.value)} className="border border-gray-300 rounded px-2 py-1.5 text-sm">{indsDoServico.map((i) => <option key={i.codigo} value={i.codigo}>{i.codigo} · {i.descricao}</option>)}</select></label>
      </div>
      <table className="text-xs min-w-full">
        <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Prestadora (alfabética)</th><th className="text-left px-2 py-1">Ano</th><th className="text-right px-2 py-1">Municípios medidos</th>
          <th className="text-right px-2 py-1">Média ponderada</th><th className="text-right px-2 py-1">Média simples</th></tr></thead>
        <tbody>
          {linhas.map((x) => (
            <tr key={x.prestadora} className="border-t border-gray-100"><td className="px-2 py-1">{x.prestadora}</td><td className="px-2 py-1">{x.ano}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(x.municipios)}</td>
              <td className="px-2 py-1 text-right tabular-nums">{dec(x.media_ponderada, 2)} {ref?.unidade}</td><td className="px-2 py-1 text-right tabular-nums">{dec(x.media, 2)}</td></tr>
          ))}
        </tbody>
      </table>
      <p className="text-xs text-gray-500">Referência da Anatel para este indicador: {referencia(ref)}. <Link to="/qualidade" className="text-primario-600 hover:underline">Qualidade</Link>.</p>
      <NotaQualidade m={q} />
    </div>
  )
}

export function TaxasReclamacoes({ itens, janela, mes }: { itens: ReclTaxa[]; janela: { de: string; ate: string } | null; mes: { SCM: string | null; SMP: string | null } }) {
  if (itens.length === 0) return null
  return (
    <div className="space-y-1">
      <h3 className="text-sm font-medium text-gray-700">Reclamações por mil acessos {janela && <span className="text-xs font-normal text-gray-500">(reclamações de {janela.de} a {janela.ate} ÷ acessos do SICI de {mes.SCM ?? '—'} (fixo) e {mes.SMP ?? '—'} (móvel))</span>}</h3>
      <table className="text-xs min-w-full">
        <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Marca</th><th className="text-left px-2 py-1">Serviço</th><th className="text-right px-2 py-1">Reclamações</th><th className="text-right px-2 py-1">Acessos (SICI)</th><th className="text-right px-2 py-1">Por mil acessos</th></tr></thead>
        <tbody>
          {itens.map((t) => (
            <tr key={`${t.marca}-${t.grupo}`} className="border-t border-gray-100"><td className="px-2 py-1">{t.marca}</td><td className="px-2 py-1">{t.grupo}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(t.reclamacoes)}</td>
              <td className="px-2 py-1 text-right tabular-nums">{inteiro(t.acessos)}</td><td className="px-2 py-1 text-right tabular-nums">{t.por_mil_acessos == null ? <span className="text-gray-400" title={t.motivo_sem_taxa ?? ''}>não calculado</span> : dec(t.por_mil_acessos, 2)}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Reclamações das marcas ligadas ao CNPJ: por ano e serviço, assuntos do último ano e a taxa por mil acessos onde defensável. */
export function ReclamacoesOperadoraBloco({ dados }: BlocoProps<OperadoraCtx>) {
  const r = dados.reclamacoes
  if (!r) return null
  const anos = r.anos.slice(-6)
  const servicos = [...new Set(anos.flatMap((a) => Object.keys(a.por_servico)))].sort()
  const assuntos = [...r.assuntos_ano.itens].sort((a, b) => b.reclamacoes - a.reclamacoes).slice(0, 8)
  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-600">Marcas ligadas a este CNPJ: {r.marcas.map((m) => `${m.marca} (${m.casamento})`).join(', ')}. {r.aviso}</p>
      <div className="overflow-x-auto">
        <table className="text-xs min-w-full">
          <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Ano</th><th className="text-right px-2 py-1">Reclamações</th>{servicos.map((s) => <th key={s} className="text-right px-2 py-1">{s}</th>)}</tr></thead>
          <tbody>
            {anos.map((a) => (
              <tr key={a.ano} className="border-t border-gray-100"><td className="px-2 py-1">{a.ano}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(a.reclamacoes)}</td>{servicos.map((s) => <td key={s} className="px-2 py-1 text-right tabular-nums">{inteiro(a.por_servico[s] ?? 0)}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
      {assuntos.length > 0 && (
        <details className="text-xs"><summary className="cursor-pointer text-gray-600">Assuntos em {r.assuntos_ano.ano}</summary>
          <ul className="divide-y divide-gray-50">{assuntos.map((x) => <li key={`${x.servico}-${x.assunto}`} className="py-1 flex justify-between gap-4"><span>{x.servico} · {x.assunto}</span><span className="tabular-nums text-gray-600">{inteiro(x.reclamacoes)}</span></li>)}</ul>
        </details>
      )}
      <TaxasReclamacoes itens={r.taxas.itens} janela={r.taxas.janela} mes={r.taxas.sici_mes_referencia} />
      <p className="text-xs text-gray-500">{r.taxas.regra}. O ano mais recente pode estar incompleto. <Link to="/qualidade?aba=reclamacoes" className="text-primario-600 hover:underline">Reclamações</Link>.</p>
      <NotaQualidade m={r} />
    </div>
  )
}

/** Reclamações no município nos últimos 3 anos da fonte: totais, por 100 mil habitantes e por serviço; marcas em ordem alfabética. */
export function ReclamacoesMunicipioBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const r = dados.reclamacoes
  if (!r) return null
  const ultimo = r.anos[r.anos.length - 1]
  return (
    <div className="space-y-2">
      <div className="overflow-x-auto">
        <table className="text-xs min-w-full">
          <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Ano</th><th className="text-right px-2 py-1">Reclamações</th><th className="text-right px-2 py-1">Por 100 mil habitantes</th><th className="text-left px-2 py-1">Por serviço</th></tr></thead>
          <tbody>
            {r.anos.map((a) => (
              <tr key={a.ano} className="border-t border-gray-100"><td className="px-2 py-1">{a.ano}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(a.reclamacoes)}</td><td className="px-2 py-1 text-right tabular-nums">{dec(a.por_100mil_hab, 1)}</td>
                <td className="px-2 py-1">{Object.entries(a.por_servico).sort().map(([s, n]) => `${s} ${inteiro(n)}`).join(' · ')}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      {ultimo && (
        <details className="text-xs"><summary className="cursor-pointer text-gray-600">Marcas citadas em {ultimo.ano} (ordem alfabética)</summary>
          <ul className="columns-1 sm:columns-2 gap-6">{[...ultimo.marcas].sort((a, b) => a.marca.localeCompare(b.marca) || a.servico.localeCompare(b.servico)).map((m) => <li key={`${m.marca}-${m.servico}`}>{m.marca} · {m.servico}: <span className="tabular-nums">{inteiro(m.reclamacoes)}</span></li>)}</ul>
        </details>
      )}
      <p className="text-xs text-gray-500">O ano mais recente pode estar incompleto.</p>
      <NotaQualidade m={r} />
    </div>
  )
}

/** Reclamações na UF por ano e serviço. */
export function ReclamacoesUfBloco({ dados }: BlocoProps<UfCtx>) {
  const r = dados.reclamacoes
  if (!r) return null
  const anos = r.anos.slice(-8)
  const servicos = [...new Set(anos.flatMap((a) => Object.keys(a.por_servico)))].sort()
  return (
    <div className="space-y-2">
      <div className="overflow-x-auto">
        <table className="text-xs min-w-full">
          <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Ano</th><th className="text-right px-2 py-1">Reclamações</th>{servicos.map((s) => <th key={s} className="text-right px-2 py-1">{s}</th>)}</tr></thead>
          <tbody>
            {anos.map((a) => <tr key={a.ano} className="border-t border-gray-100"><td className="px-2 py-1">{a.ano}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(a.reclamacoes)}</td>{servicos.map((s) => <td key={s} className="px-2 py-1 text-right tabular-nums">{inteiro(a.por_servico[s] ?? 0)}</td>)}</tr>)}
          </tbody>
        </table>
      </div>
      <NotaQualidade m={r} />
    </div>
  )
}
