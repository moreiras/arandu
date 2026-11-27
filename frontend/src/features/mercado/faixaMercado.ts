// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { MercadoMaiores, ResumoMercadoGrupos, SiciMovelStats, SiciStats } from '../../types/api'
import type { Selo } from '../../components/entidade/proveniencia'
import { compacto, n0, n1 } from '../../lib/sintese'
import { parcelaTresMaiores } from './sinteseMercado'

const SICI = 'SICI, Anatel (declarado pelas operadoras)'

/** Um cartão da faixa de mercado: o que o número conta, o mês a que se refere e a natureza do dado. */
export interface CartaoMercado {
  id: string
  rotulo: string
  valor: string
  referencia?: string
  variacao?: string
  selo: Selo
  fonte: string
  dataRef: string | null
  servico: 'fixo' | 'movel'
}

/** Mês 12 meses antes de 'AAAA-MM'. */
export function mesHa12(mes: string): string | null {
  const m = /^(\d{4})-(\d{2})$/.exec(mes)
  return m ? `${Number(m[1]) - 1}-${m[2]}` : null
}

/** Variação percentual em 12 meses sobre a série do próprio SICI; nula se o mês de 12 meses antes não está na série (ausência não vira zero). */
export function variacao12Meses(serie: Array<{ mes: string; acessos: number }> | undefined, mes: string | undefined): { pct: number; de: string } | null {
  const antes = mes ? mesHa12(mes) : null
  const atual = serie?.find((s) => s.mes === mes)?.acessos
  const ant = serie?.find((s) => s.mes === antes)?.acessos
  if (!antes || atual == null || !ant || ant <= 0) return null
  return { pct: (100 * (atual - ant)) / ant, de: antes }
}

const mesVisivel = (m: string) => `${m.slice(5, 7)}/${m.slice(0, 4)}`

/** Parte dos três maiores itens (empresa ou grupo inferido) do treemap de `/mercado/maiores`, em % do total; nula com menos de três. */
export function parcelaTresMaioresUnidades(m: MercadoMaiores | null | undefined): number | null {
  const u = m?.unidades
  if (!u || u.length < 3) return null
  const shares = [...u].sort((a, b) => b.acessos - a.acessos).slice(0, 3).map((x) => x.share)
  return shares.some((s) => s == null) ? null : shares.reduce<number>((t, s) => t + (s as number), 0)
}

/**
 * Faixa de cartões do Panorama de mercado (PT-22 / panorama-mercado 5.3): os números citáveis de banda larga fixa e móvel, cada serviço com o seu mês de
 * referência, e nunca a soma dos dois. Os números vêm dos objetos que as abas já buscam (`/acessos/stats`, `/acessos-movel/stats`, `/mercado/grupos`,
 * `/mercado/maiores`); cartão cujo dado falta não é gerado. "Três maiores" é ranking nominal implícito: a regra (acessos declarados, por CNPJ ou por
 * empresa ou grupo inferido) vai no próprio cartão e nenhuma empresa é nomeada.
 */
export function cartoesMercado(
  fixo: SiciStats | null | undefined, movel: SiciMovelStats | null | undefined,
  grupos: ResumoMercadoGrupos | null | undefined, maiores: MercadoMaiores | null | undefined,
): CartaoMercado[] {
  const out: CartaoMercado[] = []
  if (fixo && fixo.total_acessos > 0) {
    const v = variacao12Meses(fixo.serie_total, fixo.mes_referencia)
    out.push({ id: 'fixo-acessos', servico: 'fixo', rotulo: `Banda larga fixa, acessos declarados`, valor: compacto(fixo.total_acessos), selo: 'fato', fonte: SICI, dataRef: fixo.mes_referencia,
      referencia: `${n0(fixo.total_acessos)} acessos de ${n0(fixo.operadoras_ativas)} ${fixo.operadoras_ativas === 1 ? 'CNPJ' : 'CNPJs'}`,
      variacao: v ? `${v.pct >= 0 ? '+' : ''}${n1(v.pct)}% em 12 meses (sobre ${mesVisivel(v.de)})` : undefined })
    const tres = parcelaTresMaiores(fixo.top_operadoras, fixo.total_acessos)
    if (tres != null) out.push({ id: 'fixo-tres-cnpj', servico: 'fixo', rotulo: 'Três maiores CNPJs, banda larga fixa', valor: `${n1(tres)}%`, selo: 'fato', fonte: SICI, dataRef: fixo.mes_referencia,
      referencia: 'do total de acessos declarados, por CNPJ, sem agrupar' })
  }
  const tresU = parcelaTresMaioresUnidades(maiores)
  if (tresU != null) out.push({ id: 'fixo-tres-grupo', servico: 'fixo', rotulo: 'Três maiores empresas ou grupos, banda larga fixa', valor: `${n1(tresU)}%`, selo: 'inferido', fonte: 'SICI, Anatel; grupo inferido do quadro societário (Receita Federal)',
    dataRef: maiores?.mes_referencia ?? null, referencia: 'do total de acessos declarados; o grupo é inferido pelo projeto' })
  const hhi = grupos?.brasil?.hhi_cnpj
  if (hhi != null) {
    const conc = grupos?.resumo?.por_faixa_cnpj?.concentrado
    out.push({ id: 'fixo-hhi', servico: 'fixo', rotulo: 'HHI nacional por CNPJ, banda larga fixa', valor: n0(hhi), selo: 'inferido', fonte: 'cálculo do projeto sobre acessos declarados (SICI)', dataRef: grupos?.mes_referencia ?? fixo?.mes_referencia ?? null,
      referencia: conc != null ? `${n0(conc)} ${conc === 1 ? 'município com' : 'municípios com'} HHI local de 2.500 ou mais, por CNPJ` : undefined })
  }
  if (movel && movel.total_acessos > 0) {
    out.push({ id: 'movel-linhas', servico: 'movel', rotulo: 'Banda larga móvel, linhas declaradas (sem M2M)', valor: compacto(movel.total_acessos), selo: 'fato', fonte: SICI, dataRef: movel.mes_referencia,
      referencia: movel.acessos_m2m != null ? `${n0(movel.acessos_m2m)} acessos M2M à parte` : undefined })
    const tres = parcelaTresMaiores(movel.top_operadoras, movel.total_acessos)
    if (tres != null) out.push({ id: 'movel-tres-cnpj', servico: 'movel', rotulo: 'Três maiores CNPJs, banda larga móvel', valor: `${n1(tres)}%`, selo: 'fato', fonte: SICI, dataRef: movel.mes_referencia,
      referencia: 'do total de linhas declaradas, por CNPJ, sem agrupar' })
  }
  return out
}
