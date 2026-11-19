// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { Selo } from '../../components/entidade'
import type { MunicipioCtx } from './contexto'

/**
 * Síntese do município: regras fixas, sem modelo de linguagem, como a do AS e a da operadora. Cada frase sai de campos do snapshot e leva o selo
 * (fato, inferido ou estimado); regra sem dado não gera frase. Só descreve o que a fonte declara ou mede: nunca diz que o município "é mal atendido".
 */
export const REGRAS_VERSAO = 'sintese-municipio-1'

export interface Frase { id: string; texto: string; selo: Selo }

const n = (v: number) => v.toLocaleString('pt-BR', { maximumFractionDigits: 0 })
const p1 = (v: number) => v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })
const plural = (q: number, um: string, varios: string) => `${n(q)} ${q === 1 ? um : varios}`

export function sinteseMunicipio(nome: string, c: MunicipioCtx): Frase[] {
  const f: Frase[] = []
  const x = c.fixo
  if (x) {
    f.push({ id: 'acessos', selo: 'fato', texto: `${nome} tem ${n(x.acessos)} acessos de banda larga fixa declarados ao SICI, de ${plural(x.operadores_count, 'operadora', 'operadoras')}.` })
    if (x.share_maior != null) f.push({ id: 'concentracao', selo: 'fato', texto: `A maior operadora responde por ${p1(x.share_maior)}% dos acessos (HHI ${n(x.hhi)}).` })
    if (x.fibra_pct != null) f.push({ id: 'fibra', selo: 'fato', texto: `${p1(x.fibra_pct)}% dos acessos fixos são em fibra.` })
  }
  const t = c.territorio
  if (t?.penetracao != null) f.push({ id: 'penetracao', selo: 'estimado', texto: `Estimativa: ${n(t.penetracao * 100)} acessos fixos para cada 100 domicílios (domicílios projetados a partir do Censo 2022).` })
  if (c.movel) f.push({ id: 'movel', selo: 'fato', texto: `Há ${n(c.movel.acessos)} acessos móveis declarados ao SICI, de ${plural(c.movel.operadores_count, 'operadora', 'operadoras')}.` })
  const ptt = c.proximos[0]
  if (ptt) f.push({ id: 'ptt', selo: 'estimado', texto: `O PTT do IX.br mais próximo é ${ptt.nome}, a cerca de ${n(ptt.km)} km em linha reta do centróide do município.` })
  return f
}
