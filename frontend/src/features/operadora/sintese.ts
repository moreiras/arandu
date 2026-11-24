// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { Selo } from '../../components/entidade'
import type { OperadoraCtx } from './contexto'
import { credenciamentoSmp, siglasComOutorga } from './servicos'

/**
 * Frase-síntese da operadora: regras fixas, sem modelo de linguagem, como a do AS (`features/asn/sintese.ts`). Cada frase sai de campos do snapshot, leva o selo e
 * a versão das regras. Regra sem dado não gera frase. **Nunca** diz que uma empresa "tem problema": só o que a fonte declara ou mede.
 */
export const REGRAS_VERSAO = 'sintese-operadora-2'

export interface Frase { id: string; texto: string; selo: Selo }

const n = (v: number) => v.toLocaleString('pt-BR', { maximumFractionDigits: 0 })
const p1 = (v: number) => v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })
const lista = (xs: string[]) => (xs.length < 2 ? xs.join('') : `${xs.slice(0, -1).join(', ')} e ${xs[xs.length - 1]}`)
const plural = (q: number, um: string, varios: string) => `${n(q)} ${q === 1 ? um : varios}`

export function sinteseOperadora(nome: string, c: OperadoraCtx): Frase[] {
  const f: Frase[] = []
  // sintese-operadora-2: serviços só pelo cadastro de outorgas (`servicosDaOperadora`); ASN ou acesso declarado não é outorga, e
  // credenciamento de rede virtual vira frase própria, nunca "outorga SMP".
  const servicos = siglasComOutorga(c.servicos ?? [])
  const cred = credenciamentoSmp(c.servicos ?? [])
  if (servicos.length) f.push({ id: 'outorgas', selo: 'fato', texto: `${nome} tem outorga da Anatel para ${lista(servicos)}.` })
  if (cred) f.push({ id: 'rede-virtual', selo: 'fato', texto: `No SMP, é credenciada de rede virtual${cred.origem?.nome ? ` de ${cred.origem.nome}` : ''} (sem outorga SMP própria).` })
  if (!servicos.length && !cred) f.push({ id: 'sem-outorga', selo: 'fato', texto: 'Sem outorga registrada na Anatel neste snapshot.' })
  const i = c.indicadores
  if (i?.acessos != null) {
    f.push({
      id: 'acessos', selo: 'fato',
      texto: `Declarou ${n(i.acessos)} acessos de banda larga fixa ao SICI em ${i.mes_referencia}`
        + (i.share_br != null ? `, ${i.share_br.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}% dos acessos declarados no país` : '')
        + (i.posicao_br != null ? ` (${n(i.posicao_br)}º por acessos).` : '.'),
    })
    if (i.var_aa?.pct != null) f.push({ id: 'variacao', selo: 'fato', texto: `Em 12 meses, os acessos declarados variaram ${i.var_aa.pct > 0 ? '+' : ''}${p1(i.var_aa.pct)}%.` })
    if (i.em_declinio && i.meses_declinio) f.push({ id: 'declinio', selo: 'fato', texto: `Os acessos declarados caíram por ${plural(i.meses_declinio, 'mês seguido', 'meses seguidos')}.` })
  } else if (i?.sem_declaracao) {
    f.push({ id: 'sem-declaracao', selo: 'fato', texto: `Tem outorga SCM, mas não declarou acessos ao SICI em ${i.mes_referencia}.` })
  }
  const d = c.data
  if (d?.municipios) f.push({ id: 'municipios', selo: 'fato', texto: `Declara acessos em ${plural(d.municipios, 'município', 'municípios')}${c.hasSici ? `; ${p1(c.b2cPct)}% dos acessos são de pessoa física (B2C).` : '.'}` })
  const asns = d?.asns?.length ? d.asns : (c.dataMovel?.asns ?? [])
  f.push({ id: 'asns', selo: 'fato', texto: asns.length ? `Tem ${plural(asns.length, 'ASN', 'ASNs')} no Registro.br.` : 'Não tem ASN próprio no Registro.br.' })
  return f
}

export interface KpiOp { id: string; rotulo: string; valor: string | null; referencia?: string }

export function kpisOperadora(c: OperadoraCtx): KpiOp[] {
  const i = c.indicadores
  const asns = c.data?.asns?.length ? c.data.asns : (c.dataMovel?.asns ?? [])
  return [
    { id: 'acessos', rotulo: `Acessos fixos${i ? ` (${i.mes_referencia})` : ''}`, valor: i?.acessos != null ? n(i.acessos) : null },
    { id: 'share', rotulo: 'Parcela no país', valor: i?.share_br != null ? `${i.share_br.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%` : null, referencia: i?.posicao_br ? `${n(i.posicao_br)}º por acessos` : undefined },
    { id: 'variacao', rotulo: 'Variação em 12 meses', valor: i?.var_aa?.pct != null ? `${i.var_aa.pct > 0 ? '+' : ''}${p1(i.var_aa.pct)}%` : null },
    { id: 'municipios', rotulo: 'Municípios com acessos', valor: c.data?.municipios != null ? n(c.data.municipios) : null },
    { id: 'asns', rotulo: 'ASNs', valor: n(asns.length) },
  ]
}
