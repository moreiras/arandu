// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { TomKpi } from '../../components/ui'
import type { SiciStats, SnapshotSummary } from '../../types/api'

/** Um indicador da faixa "o Brasil em números": valor, variação desde a comparação anterior, a fonte e a data a que o número se refere. */
export interface KpiHome {
  id: string
  rotulo: string
  valor: string | null
  variacao?: { texto: string; bom?: boolean }
  fonte: string
  /** Data do snapshot (rede) ou mês de referência (SICI): o que o número descreve, não a data de coleta. */
  dataRef: string | null
  /** O número é estimativa (não medição). */
  estimado?: boolean
  /** Acento de cor do indicador na home. */
  tom?: TomKpi
}

const n0 = (v: number) => v.toLocaleString('pt-BR', { maximumFractionDigits: 0 })
const n1 = (v: number) => v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })
const sinal = (v: number) => (v > 0 ? '+' : v < 0 ? '−' : '')
const compacto = (v: number) => (v >= 1e6 ? `${n1(v / 1e6)} mi` : v >= 1e3 ? `${n0(v / 1e3)} mil` : n0(v))

/** Variação absoluta ("+12" / "−3" / "sem variação"), ou nada quando falta um dos dois snapshots. */
function deltaInteiro(atual?: number | null, antes?: number | null, bom?: boolean): KpiHome['variacao'] {
  if (atual == null || antes == null) return undefined
  const d = atual - antes
  return d === 0 ? { texto: 'sem variação' } : { texto: `${sinal(d)}${n0(Math.abs(d))} desde o snapshot anterior`, bom: bom === undefined ? undefined : (d > 0) === bom }
}

/** Rede (do resumo do snapshot, com o snapshot anterior para a variação) e mercado (SICI, com o mês anterior da série). */
export function montarKpis(resumo: SnapshotSummary | null | undefined, anterior: SnapshotSummary | null | undefined, sici: SiciStats | null | undefined, dataSnapshot: string | null): { rede: KpiHome[]; mercado: KpiHome[] } {
  const r = resumo as (SnapshotSummary & Record<string, any>) | null | undefined
  const a = anterior as (SnapshotSummary & Record<string, any>) | null | undefined
  const rede: KpiHome[] = [
    { id: 'ases', tom: 'v4', rotulo: 'ASes brasileiros alocados', valor: r?.total_asns_br != null ? n0(r.total_asns_br) : null,
      variacao: deltaInteiro(r?.total_asns_br, a?.total_asns_br, true), fonte: 'Registro.br (estatística delegated do LACNIC)', dataRef: dataSnapshot },
    { id: 'ipv6', tom: 'v6', rotulo: 'ASes BR com IPv6 alocado ou anunciado', valor: r?.br_ipv6_pct != null ? `${n1(r.br_ipv6_pct)}%` : null,
      variacao: r?.br_ipv6_pct != null && a?.br_ipv6_pct != null ? (() => { const d = Math.round((r.br_ipv6_pct - a.br_ipv6_pct) * 10) / 10; return d === 0 ? { texto: 'sem variação' } : { texto: `${sinal(d)}${n1(Math.abs(d))} p.p. desde o snapshot anterior`, bom: d > 0 } })() : undefined,
      fonte: 'Registro.br, tabela global (RouteViews) e IX.br', dataRef: dataSnapshot },
    { id: 'ptts', tom: 'tecnico', rotulo: 'PTTs do IX.br com coleta', valor: r?.ixps_ok != null ? n0(r.ixps_ok) : null,
      variacao: deltaInteiro(r?.ixps_ok, a?.ixps_ok, true), fonte: 'looking glass do IX.br', dataRef: dataSnapshot },
    { id: 'usuarios', tom: 'estimado', rotulo: 'Usuários estimados nos ASes BR', valor: r?.br_apnic_users_total != null ? compacto(r.br_apnic_users_total) : null,
      variacao: undefined, fonte: 'APNIC (estimativa, não é censo)', dataRef: dataSnapshot, estimado: true },
  ]
  const serie = sici?.serie_total ?? []
  const ult = serie[serie.length - 1]
  const pen = serie[serie.length - 2]
  const fibra = sici && sici.total_acessos > 0 && sici.por_meio?.Fibra != null ? (100 * sici.por_meio.Fibra) / sici.total_acessos : null
  const mercado: KpiHome[] = [
    { id: 'acessos', tom: 'mercado', rotulo: 'Acessos de banda larga fixa', valor: sici ? compacto(sici.total_acessos) : null,
      variacao: ult && pen && pen.acessos > 0 ? (() => { const p = (100 * (ult.acessos - pen.acessos)) / pen.acessos; return { texto: `${sinal(p)}${n1(Math.abs(p))}% desde ${pen.mes.slice(5)}/${pen.mes.slice(0, 4)}`, bom: p > 0 } })() : undefined,
      fonte: 'SICI, Anatel (declarado pelas operadoras)', dataRef: sici?.mes_referencia ?? null },
    { id: 'fibra', tom: 'mercado', rotulo: 'Acessos em fibra', valor: fibra != null ? `${n0(fibra)}%` : null, fonte: 'SICI, Anatel', dataRef: sici?.mes_referencia ?? null },
    { id: 'operadoras', tom: 'mercado', rotulo: 'Operadoras que declararam acessos', valor: sici ? n0(sici.operadoras_ativas) : null, fonte: 'SICI, Anatel', dataRef: sici?.mes_referencia ?? null },
    { id: 'municipios', tom: 'mercado', rotulo: 'Municípios com banda larga fixa declarada', valor: sici ? n0(sici.municipios_atendidos) : null, fonte: 'SICI, Anatel', dataRef: sici?.mes_referencia ?? null },
  ]
  return { rede, mercado }
}
