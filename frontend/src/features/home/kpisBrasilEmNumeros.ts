// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { TomKpi } from '../../components/ui'
import type { Selo } from '../../components/entidade/proveniencia'
import type { SiciStats, SnapshotSummary } from '../../types/api'
import { rotuloDe } from '../../lib/universos'

/** Um indicador da faixa "o Brasil em números": valor, variação desde a comparação anterior, a fonte e a data a que o número se refere. */
export interface KpiHome {
  id: string
  rotulo: string
  valor: string | null
  variacao?: { texto: string; bom?: boolean }
  /** Natureza do dado, exibida por extenso sob o valor (classificação inicial do PT-14; regra em `DESCRICAO_SELO`). */
  selo: Selo
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

/** % dos ASNs brasileiros (delegados pela LACNIC ao Brasil) com ao menos um prefixo IPv6 na tabela global. */
function pctV6(r: (SnapshotSummary & Record<string, any>) | null | undefined): number | null {
  return r?.br_asns_ft_v6 != null && r.total_asns_br > 0 ? (100 * r.br_asns_ft_v6) / r.total_asns_br : null
}

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
    { id: 'ases', selo: 'fato', tom: 'v4', rotulo: rotuloDe('asnsLacnic'), valor: r?.total_asns_br != null ? n0(r.total_asns_br) : null,
      variacao: deltaInteiro(r?.total_asns_br, a?.total_asns_br, true), fonte: 'LACNIC (delegated-extended)', dataRef: dataSnapshot },
    // Anúncio, não alocação: quase todo AS recebe bloco IPv6 com a designação, e `has_ipv6` (alocado ou anunciado) passa de 97%.
    { id: 'ipv6', selo: 'fato', tom: 'v6', rotulo: rotuloDe('asnsAnunciamV6'), valor: pctV6(r) != null ? `${n1(pctV6(r)!)}%` : null,
      variacao: (() => { const p = pctV6(r), q = pctV6(a); if (p == null || q == null) return undefined; const d = Math.round((p - q) * 10) / 10; return d === 0 ? { texto: 'sem variação' } : { texto: `${sinal(d)}${n1(Math.abs(d))} p.p. desde o snapshot anterior`, bom: d > 0 } })(),
      fonte: 'tabela global (RouteViews), sobre os ASNs delegados pela LACNIC ao Brasil', dataRef: dataSnapshot },
    { id: 'ptts', selo: 'fato', tom: 'tecnico', rotulo: 'PTTs do IX.br com coleta', valor: r?.ixps_ok != null ? n0(r.ixps_ok) : null,
      variacao: deltaInteiro(r?.ixps_ok, a?.ixps_ok, true), fonte: 'looking glass do IX.br', dataRef: dataSnapshot },
    { id: 'usuarios', selo: 'estimado', tom: 'estimado', rotulo: rotuloDe('usuariosPais'), valor: r?.br_apnic_users_total != null ? compacto(r.br_apnic_users_total) : null,
      variacao: undefined, fonte: 'APNIC (estimativa, não é censo)', dataRef: dataSnapshot },
  ]
  const serie = sici?.serie_total ?? []
  const ult = serie[serie.length - 1]
  const pen = serie[serie.length - 2]
  const fibra = sici && sici.total_acessos > 0 && sici.por_meio?.Fibra != null ? (100 * sici.por_meio.Fibra) / sici.total_acessos : null
  const mercado: KpiHome[] = [
    { id: 'acessos', selo: 'fato', tom: 'mercado', rotulo: 'Acessos de banda larga fixa', valor: sici ? compacto(sici.total_acessos) : null,
      variacao: ult && pen && pen.acessos > 0 ? (() => { const p = (100 * (ult.acessos - pen.acessos)) / pen.acessos; return { texto: `${sinal(p)}${n1(Math.abs(p))}% desde ${pen.mes.slice(5)}/${pen.mes.slice(0, 4)}`, bom: p > 0 } })() : undefined,
      fonte: 'SICI, Anatel (declarado pelas operadoras)', dataRef: sici?.mes_referencia ?? null },
    { id: 'fibra', selo: 'fato', tom: 'mercado', rotulo: 'Acessos em fibra', valor: fibra != null ? `${n0(fibra)}%` : null, fonte: 'SICI, Anatel', dataRef: sici?.mes_referencia ?? null },
    { id: 'operadoras', selo: 'fato', tom: 'mercado', rotulo: rotuloDe('declarantesFixo'), valor: sici ? n0(sici.operadoras_ativas) : null, fonte: 'SICI, Anatel', dataRef: sici?.mes_referencia ?? null },
    { id: 'municipios', selo: 'fato', tom: 'mercado', rotulo: 'Municípios (tabela do IBGE) com banda larga fixa declarada', valor: sici ? n0(sici.municipios_atendidos) : null, fonte: 'SICI, Anatel', dataRef: sici?.mes_referencia ?? null },
  ]
  return { rede, mercado }
}
