// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import type { BlocoProps } from '../entidade/registry'
import type { MunicipioCtx } from '../municipio/contexto'
import type { OperadoraCtx } from '../operadora/contexto'
import type { UfCtx } from '../uf/contexto'
import type { ConsJanela, ConsMeta, ConsMetricas } from '../../types/api'
import { dec, inteiro } from './blocos'

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

export function CabecalhoMetricas() {
  return (
    <>
      <th className="text-right px-2 py-1">Finalizadas</th><th className="text-right px-2 py-1" title="Resolvidas ÷ avaliadas pelo consumidor">Índice de solução</th>
      <th className="text-right px-2 py-1" title="Média, em dias, das respondidas">Tempo de resposta</th><th className="text-right px-2 py-1" title="Média de 1 a 5">Nota média</th><th className="text-right px-2 py-1">% respondidas</th>
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
  if (!c) return null
  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-600">Empresas do Consumidor.gov.br ligadas a este CNPJ: {c.marcas.map((m) => `${m.marca} (${m.casamento ?? 'sem ligação'})`).join(', ')}.</p>
      <div className="overflow-x-auto">
        <table className="text-xs min-w-full">
          <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Empresa (últimos 12 meses)</th><CabecalhoMetricas /></tr></thead>
          <tbody>
            {c.marcas.filter((m) => m.janela).map((m) => <tr key={m.marca} className="border-t border-gray-100"><td className="px-2 py-1">{m.marca}</td><CelulasMetricas x={m.janela!} /></tr>)}
          </tbody>
        </table>
      </div>
      {c.marcas.map((m) => (
        <details key={m.marca} className="text-xs">
          <summary className="cursor-pointer text-gray-600">{m.marca}: série mensal ({m.por_mes.length} meses)</summary>
          <div className="overflow-x-auto"><table className="text-xs min-w-full">
            <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Mês</th><CabecalhoMetricas /></tr></thead>
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
        <table className="text-xs min-w-full">
          <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Empresa (alfabética)</th><CabecalhoMetricas /></tr></thead>
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
        <table className="text-xs min-w-full">
          <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Empresa (alfabética)</th><CabecalhoMetricas /></tr></thead>
          <tbody>{c.itens.map((x) => <tr key={x.marca} className="border-t border-gray-100"><td className="px-2 py-1">{x.marca}</td><CelulasMetricas x={x} /></tr>)}</tbody>
        </table>
      </div>
      <p className="text-xs text-gray-500">Só empresas com pelo menos {c.minimos.reclamacoes_por_celula} reclamações na UF na janela. <Link to="/qualidade?aba=consumidor" className="text-primario-600 hover:underline">Consumidor.gov.br</Link>.</p>
      <NotaConsumidor m={c} janela={c.janela} />
    </div>
  )
}
