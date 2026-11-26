// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { Selo } from '../../components/entidade'
import type { OperadoraCtx } from './contexto'
import type { AsnVinculado } from '../../types/api'
import { formatarReferencia } from '../../components/entidade/proveniencia'
import { credenciamentoSmp, siglasComOutorga } from './servicos'

/**
 * Frase-síntese da operadora: regras fixas, sem modelo de linguagem, como a do AS (`features/asn/sintese.ts`). Cada frase sai de campos do snapshot, leva o selo e
 * a versão das regras. Regra sem dado não gera frase. **Nunca** diz que uma empresa "tem problema": só o que a fonte declara ou mede.
 */
export const REGRAS_VERSAO = 'sintese-operadora-4'

export interface Frase { id: string; texto: string; selo: Selo }
/** Frase com a fonte e a data de referência, que o resumo em texto manda para o bloco recolhido (PT-30). */
export interface FraseComFonte extends Frase { fonte: string; dataRef: string | null }

const n = (v: number) => v.toLocaleString('pt-BR', { maximumFractionDigits: 0 })
const p1 = (v: number) => v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })
const lista = (xs: string[]) => (xs.length < 2 ? xs.join('') : `${xs.slice(0, -1).join(', ')} e ${xs[xs.length - 1]}`)
const plural = (q: number, um: string, varios: string) => `${n(q)} ${q === 1 ? um : varios}`

export function sinteseOperadora(nome: string, c: OperadoraCtx): FraseComFonte[] {
  const f: FraseComFonte[] = []
  const snap = c.data?.snapshot_date ?? c.dataMovel?.snapshot_date ?? c.dataStfc?.snapshot_date ?? c.dataSeac?.snapshot_date ?? null
  const outorgasAnatel = { selo: 'fato' as const, fonte: 'Anatel (outorgas de SCM, SMP, STFC e SeAC)', dataRef: snap }
  // sintese-operadora-2: serviços só pelo cadastro de outorgas (`servicosDaOperadora`); ASN ou acesso declarado não é outorga, e
  // credenciamento de rede virtual vira frase própria, nunca "outorga SMP".
  const servicos = siglasComOutorga(c.servicos ?? [])
  const cred = credenciamentoSmp(c.servicos ?? [])
  if (servicos.length) f.push({ id: 'outorgas', ...outorgasAnatel, texto: `${nome} tem outorga da Anatel para ${lista(servicos)}.` })
  if (cred) f.push({ id: 'rede-virtual', ...outorgasAnatel, texto: `No SMP, a empresa é credenciada de rede virtual${cred.origem?.nome ? ` de ${cred.origem.nome}` : ''}, sem outorga SMP própria.` })
  if (!servicos.length && !cred) f.push({ id: 'sem-outorga', ...outorgasAnatel, texto: 'Este snapshot não registra outorga da Anatel para a empresa.' })
  const i = c.indicadores
  const mes = i?.mes_referencia ? formatarReferencia(i.mes_referencia) : null
  const sici = { selo: 'fato' as const, fonte: 'Anatel (SICI), declarado pela empresa', dataRef: i?.mes_referencia ?? null }
  if (i?.acessos != null) {
    f.push({
      id: 'acessos', ...sici,
      texto: `Em ${mes}, a empresa declarou ao SICI ${n(i.acessos)} acessos de banda larga fixa`
        + (i.share_br != null ? `, ${i.share_br.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}% dos acessos declarados no país.` : '.')
        + (i.posicao_br != null ? ` Isso a coloca em ${n(i.posicao_br)}º lugar por acessos.` : ''),
    })
    if (i.var_aa?.pct != null) f.push({ id: 'variacao', ...sici, texto: `Em 12 meses, os acessos declarados variaram ${i.var_aa.pct > 0 ? '+' : ''}${p1(i.var_aa.pct)}%.` })
    if (i.em_declinio && i.meses_declinio) f.push({ id: 'declinio', ...sici, texto: `Os acessos declarados caíram por ${plural(i.meses_declinio, 'mês seguido', 'meses seguidos')}.` })
  } else if (i?.sem_declaracao) {
    f.push({ id: 'sem-declaracao', ...sici, texto: `A empresa tem outorga SCM, mas não declarou acessos ao SICI em ${mes}.` })
  }
  const d = c.data
  if (d?.municipios) f.push({ id: 'municipios', ...sici, dataRef: i?.mes_referencia ?? snap, texto: `A empresa declara acessos em ${plural(d.municipios, 'município', 'municípios')}${c.hasSici ? `, e ${p1(c.b2cPct)}% dos acessos são de pessoa física (B2C).` : '.'}` })
  const asns = d?.asns?.length ? d.asns : (c.dataMovel?.asns ?? [])
  // sintese-operadora-3 (D5): o fato é o ASN no mesmo CNPJ; raiz, marca e AS estrangeiro vêm em frases à parte, com selo inferido
  f.push({
    id: 'asns', selo: 'fato', fonte: 'Registro.br (ASNs do mesmo CNPJ)', dataRef: snap,
    texto: asns.length ? `No Registro.br, ${plural(asns.length, 'ASN está registrado', 'ASNs estão registrados')} com este CNPJ.` : 'No Registro.br, nenhum ASN está registrado com este CNPJ.',
  })
  const vinc = d?.asns_vinculados ?? c.dataMovel?.asns_vinculados ?? []
  const as_ = (xs: AsnVinculado[]) => lista(xs.map((x) => `AS${x.asn}`))
  const raiz = vinc.filter((x) => x.vinculo === 'raiz')
  const vinculo = { selo: 'inferido' as const, fonte: 'Registro.br e tabela de marcas curada pelo projeto', dataRef: snap }
  if (raiz.length) f.push({ id: 'asns-raiz', ...vinculo, texto: `${raiz.length === 1 ? 'O' : 'Os'} ${as_(raiz)} ${raiz.length === 1 ? 'está registrado' : 'estão registrados'} em outro CNPJ da mesma raiz (matriz ou filial da mesma empresa).` })
  for (const tipo of ['marca', 'estrangeiro'] as const) {
    const xs = vinc.filter((x) => x.vinculo === tipo)
    if (!xs.length) continue
    const marca = xs[0].marca ? ` ${xs[0].marca}` : ''
    f.push({ id: `asns-${tipo}`, ...vinculo, texto: tipo === 'marca'
      ? `Pela marca${marca} (tabela curada do projeto), a empresa se associa a ${as_(xs)}, que é de outra empresa.`
      : `Pela marca${marca} (tabela curada do projeto), a empresa é atendida por um AS estrangeiro: ${as_(xs)}.` })
  }
  return f
}

export interface KpiOp { id: string; rotulo: string; valor: string | null; referencia?: string; selo: Selo; fonte: string; dataRef: string | null }

/**
 * Indicadores da ficha com a proveniência (PT-14). Acessos, parcela, posição, variação e municípios são o declarado pela empresa ao SICI (fato; parcela e
 * variação são aritmética sobre o declarado, no mês de referência); os ASNs são os do mesmo CNPJ no Registro.br, sem vínculo inferido.
 */
export function kpisOperadora(c: OperadoraCtx): KpiOp[] {
  const i = c.indicadores
  const asns = c.data?.asns?.length ? c.data.asns : (c.dataMovel?.asns ?? [])
  const mes = i?.mes_referencia ?? null
  const snap = c.data?.snapshot_date ?? c.dataMovel?.snapshot_date ?? null
  const sici = { selo: 'fato' as const, fonte: 'Anatel (SICI)', dataRef: mes }
  return [
    { id: 'acessos', rotulo: `Acessos fixos${i ? ` (${i.mes_referencia})` : ''}`, valor: i?.acessos != null ? n(i.acessos) : null, ...sici },
    { id: 'share', rotulo: 'Parcela no país', valor: i?.share_br != null ? `${i.share_br.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%` : null, referencia: i?.posicao_br ? `${n(i.posicao_br)}º por acessos` : undefined, ...sici },
    { id: 'variacao', rotulo: 'Variação em 12 meses', valor: i?.var_aa?.pct != null ? `${i.var_aa.pct > 0 ? '+' : ''}${p1(i.var_aa.pct)}%` : null, ...sici },
    { id: 'municipios', rotulo: 'Municípios com acessos', valor: c.data?.municipios != null ? n(c.data.municipios) : null, selo: 'fato', fonte: 'Anatel (SICI)', dataRef: mes ?? snap },
    { id: 'asns', rotulo: 'ASNs', valor: n(asns.length), selo: 'fato', fonte: 'Registro.br (mesmo CNPJ)', dataRef: snap },
  ]
}
