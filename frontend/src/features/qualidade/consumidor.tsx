// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../components/layout/LinkDatado'
import type { BlocoProps } from '../entidade/registry'
import type { MunicipioCtx } from '../municipio/contexto'
import type { OperadoraCtx } from '../operadora/contexto'
import type { UfCtx } from '../uf/contexto'
import type { ConsJanela, ConsMeta, ConsMetricas } from '../../types/api'
import { dec, inteiro } from './blocos'
import { ThOrdenavel } from '../../components/ui/ThOrdenavel'
import { useOrdenacao, type Ordem } from '../../lib/ordenacao'

/** Indicador nulo = base insuficiente (menos de 30 casos): o traço explica, não é zero. */
export const BASE_INSUF = 'base insuficiente (menos de 30 casos)'
export const pct = (v?: number | null) => (v == null ? '—' : `${dec(v, 1)}%`)

export function Indicador({ v, fmt }: { v: number | null | undefined; fmt: (x: number) => string }) {
  return v == null ? <span className="text-gray-400" title={BASE_INSUF}>—</span> : <>{fmt(v)}</>
}

/** Fonte, janela e limites sempre junto do número; avisa quando a janela não tem todos os meses. */
export function NotaConsumidor({ m, janela }: { m: ConsMeta; janela: ConsJanela }) {
  return (
    <div className="space-y-1">
      {janela.aviso && <p className="text-xs text-aviso-700">{janela.aviso}.</p>}
      <p className="text-xs text-gray-500">Consumidor.gov.br (Senacon), reclamações finalizadas de {janela.de} a {janela.ate}; snapshot {m.snapshot_date}. {m.limites}</p>
    </div>
  )
}

/** Campos das colunas de `CabecalhoMetricas` (os de `ConsMetricas`), para os acessores de `useOrdenacao`. */
export type CampoMetrica = 'n' | 'indice_solucao' | 'tempo_medio_dias' | 'nota_media' | 'pct_respondidas'
type PropsOrdem = (campo: CampoMetrica) => { campo: string; ordem: Ordem | null | undefined; onOrdenar?: (c: string) => void }

/** Cabeçalho das métricas; com `props` (de `useOrdenacao(...).props`) as colunas ordenam, sem ele são `<th>` comuns. */
export function CabecalhoMetricas({ props }: { props?: PropsOrdem } = {}) {
  const th = (campo: CampoMetrica, rotulo: string, title?: string) => (
    <ThOrdenavel {...(props ? props(campo) : { campo, ordem: null })} alinhar="right" className="text-right px-2 py-1" title={title}>{rotulo}</ThOrdenavel>
  )
  return (
    <>
      {th('n', 'Finalizadas')}{th('indice_solucao', 'Índice de solução', 'Resolvidas ÷ avaliadas pelo consumidor')}
      {th('tempo_medio_dias', 'Tempo de resposta', 'Média, em dias, das respondidas')}{th('nota_media', 'Nota média', 'Média de 1 a 5')}{th('pct_respondidas', '% respondidas')}
    </>
  )
}

export function CelulasMetricas({ x }: { x: ConsMetricas }) {
  return (
    <>
      <td className="px-2 py-1 text-right tabular-nums">{inteiro(x.n)}</td>
      <td className="px-2 py-1 text-right tabular-nums"><Indicador v={x.indice_solucao} fmt={pct} /></td>
      <td className="px-2 py-1 text-right tabular-nums"><Indicador v={x.tempo_medio_dias} fmt={(v) => `${dec(v, 1)} d`} /></td>
      <td className="px-2 py-1 text-right tabular-nums"><Indicador v={x.nota_media} fmt={(v) => dec(v, 2)} /></td>
      <td className="px-2 py-1 text-right tabular-nums"><Indicador v={x.pct_respondidas} fmt={pct} /></td>
    </>
  )
}

/** Reclamações finalizadas das empresas ligadas ao CNPJ: janela de 12 meses, série mensal e assuntos. */
export function ConsumidorOperadoraBloco({ dados }: BlocoProps<OperadoraCtx>) {
  const c = dados.consumidor
  // Só as empresas ligadas a este CNPJ (lista inteira); não é ranking entre operadoras.
  const { ordenados, props } = useOrdenacao((c?.marcas ?? []).filter((m) => m.janela), {
    marca: (m) => m.marca,
    n: (m) => m.janela!.n,
    indice_solucao: (m) => m.janela!.indice_solucao,
    tempo_medio_dias: { valor: (m) => m.janela!.tempo_medio_dias, primeiro: 'asc' },
    nota_media: (m) => m.janela!.nota_media,
    pct_respondidas: (m) => m.janela!.pct_respondidas,
  })
  if (!c) return null
  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-600">Empresas do Consumidor.gov.br ligadas a este CNPJ: {c.marcas.map((m) => `${m.marca} (${m.casamento ?? 'sem ligação'})`).join(', ')}.</p>
      <div className="overflow-x-auto">
        <table className="text-xs min-w-full"><caption className="sr-only">Empresas do Consumidor.gov.br ligadas a este CNPJ</caption>
          <thead className="text-gray-500"><tr><ThOrdenavel {...props('marca')} className="text-left px-2 py-1">Empresa (últimos 12 meses)</ThOrdenavel><CabecalhoMetricas props={props} /></tr></thead>
          <tbody>
            {ordenados.map((m) => <tr key={m.marca} className="border-t border-gray-100"><td className="px-2 py-1">{m.marca}</td><CelulasMetricas x={m.janela!} /></tr>)}
          </tbody>
        </table>
      </div>
      {c.marcas.map((m) => (
        <details key={m.marca} className="text-xs">
          <summary className="cursor-pointer text-gray-600">{m.marca}: série mensal ({m.por_mes.length} meses)</summary>
          <div className="overflow-x-auto"><table className="text-xs min-w-full"><caption className="sr-only">Série mensal da empresa no Consumidor.gov.br</caption>
            <thead className="text-gray-500"><tr><th scope="col" className="text-left px-2 py-1">Mês</th><CabecalhoMetricas /></tr></thead>
            <tbody>{m.por_mes.slice(-12).map((x) => <tr key={x.mes} className="border-t border-gray-100"><td className="px-2 py-1">{x.mes}</td><CelulasMetricas x={x} /></tr>)}</tbody>
          </table></div>
        </details>
      ))}
      {c.assuntos.length > 0 && (
        <details className="text-xs"><summary className="cursor-pointer text-gray-600">Assuntos nos últimos 12 meses</summary>
          <ul className="divide-y divide-gray-50">{[...c.assuntos].sort((a, b) => b.n - a.n).slice(0, 10).map((x) => <li key={`${x.marca}-${x.assunto}`} className="py-1 flex justify-between gap-4"><span>{x.marca} · {x.assunto}</span><span className="tabular-nums text-gray-600">{inteiro(x.n)}</span></li>)}</ul>
        </details>
      )}
      <p className="text-xs text-gray-500">A ligação empresa → CNPJ é curada ou por nome fantasia único (<Link to="/qualidade?aba=consumidor" className="text-primario-600 hover:underline">Consumidor.gov.br</Link>); reclamação finalizada não é prova de falha da empresa.</p>
      <NotaConsumidor m={c} janela={c.janela} />
    </div>
  )
}

/** Reclamações finalizadas no município: total e empresas com pelo menos 5 reclamações (ordem alfabética). */
export function ConsumidorMunicipioBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const c = dados.consumidor
  if (!c) return null
  const itens = [...c.itens].sort((a, b) => a.marca.localeCompare(b.marca))
  return (
    <div className="space-y-2">
      <div className="overflow-x-auto">
        <table className="text-xs min-w-full"><caption className="sr-only">Empresas do Consumidor.gov.br no município</caption>
          <thead className="text-gray-500"><tr><th scope="col" className="text-left px-2 py-1">Empresa (alfabética)</th><CabecalhoMetricas /></tr></thead>
          <tbody>
            <tr className="border-t border-gray-100 font-medium"><td className="px-2 py-1">Todas as operadoras</td><CelulasMetricas x={c.total} /></tr>
            {itens.map((x) => <tr key={x.marca} className="border-t border-gray-100"><td className="px-2 py-1">{x.marca}</td><CelulasMetricas x={x} /></tr>)}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-gray-500">Só empresas com pelo menos {c.minimos.reclamacoes_por_celula} reclamações no município na janela; as demais entram no total. A cidade é o nome digitado pelo consumidor, casado ao IBGE por nome e UF.</p>
      <NotaConsumidor m={c} janela={c.janela} />
    </div>
  )
}

/** Reclamações finalizadas na UF por empresa (ordem alfabética, sem ranking). */
export function ConsumidorUfBloco({ dados }: BlocoProps<UfCtx>) {
  const c = dados.consumidor
  if (!c) return null
  return (
    <div className="space-y-2">
      <div className="overflow-x-auto">
        <table className="text-xs min-w-full"><caption className="sr-only">Empresas do Consumidor.gov.br na UF</caption>
          <thead className="text-gray-500"><tr><th scope="col" className="text-left px-2 py-1">Empresa (alfabética)</th><CabecalhoMetricas /></tr></thead>
          <tbody>{c.itens.map((x) => <tr key={x.marca} className="border-t border-gray-100"><td className="px-2 py-1">{x.marca}</td><CelulasMetricas x={x} /></tr>)}</tbody>
        </table>
      </div>
      <p className="text-xs text-gray-500">Só empresas com pelo menos {c.minimos.reclamacoes_por_celula} reclamações na UF na janela. <Link to="/qualidade?aba=consumidor" className="text-primario-600 hover:underline">Consumidor.gov.br</Link>.</p>
      <NotaConsumidor m={c} janela={c.janela} />
    </div>
  )
}
