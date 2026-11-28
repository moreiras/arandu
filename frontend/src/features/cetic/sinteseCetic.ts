// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { CeticLinha } from '../../types/api'
import { limitar, type FraseSintese } from '../../lib/sintese'
import { TEXTO_ZERO_REGISTRADO, estadoMargem } from './margem'
import temas from './temasSintese.json'

export const REGRAS_SINTESE_CETIC = 'sintese-cetic-2'

export type Pesquisa = 'domicilios' | 'provedores'
export interface TemaCetic { id: string; tabela: string; dimensao: string; recorte: string; item: string; resposta: string }
export const TEMAS: Record<Pesquisa, TemaCetic[]> = { domicilios: temas.domicilios, provedores: temas.provedores }
/** Tabelas a buscar de cada pesquisa para a síntese (sem repetição). */
export const TABELAS_SINTESE: Record<Pesquisa, string[]> = {
  domicilios: [...new Set(TEMAS.domicilios.map((t) => t.tabela))],
  provedores: [...new Set(TEMAS.provedores.map((t) => t.tabela))],
}

/** O que a síntese recebe de cada pesquisa: edição e as linhas das tabelas citadas (as mesmas linhas que a tabela da página mostra). */
export interface EntradaCetic { edicao: number | string; linhas: CeticLinha[] }

const p1 = (v: number) => v.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

/** A célula do tema, por igualdade nos cinco campos; ausente se a edição não a tem. */
export function celula(linhas: CeticLinha[] | undefined, tema: TemaCetic): CeticLinha | undefined {
  return linhas?.find((l) => l.tabela === tema.tabela && l.dimensao === tema.dimensao && l.recorte === tema.recorte && l.item === tema.item && l.resposta === tema.resposta && l.proporcao != null)
}

/** "86,3% (±0,8)"; margem registrada como zero na planilha não vira "±0,0" (mesma regra da tabela da página). */
export function valorComMargem(l: CeticLinha): string {
  const v = l.proporcao as number
  const estado = estadoMargem(v, l.margem_proporcao, 'proporcao')
  if (estado === 'zero_registrado') return `${p1(v)}% (${TEXTO_ZERO_REGISTRADO})`
  const m = l.margem_proporcao
  return m == null ? `${p1(v)}% (margem não publicada)` : `${p1(v)}% (±${p1(m)}${estado === 'precisao_baixa' ? '; precisão baixa' : ''})`
}

/**
 * Síntese de Uso da Internet (PT-22, uso-da-internet 5.2): cinco números de acesso, conexão e interconexão, lidos das MESMAS linhas das tabelas oficiais que a página
 * mostra, cada um com a margem de erro, o universo (o denominador na frase), a pesquisa e a edição. São estimativas amostrais (selo estimado); duas estimativas só
 * diferem de modo claro quando as faixas não se sobrepõem, e a frase por classe social não afirma diferença. O que a edição não traz não gera frase.
 */
export function sinteseCetic(dom: EntradaCetic | undefined, prov: EntradaCetic | undefined): FraseSintese[] {
  const t = (p: Pesquisa, id: string) => TEMAS[p].find((x) => x.id === id)!
  const a4 = dom && celula(dom.linhas, t('domicilios', 'a4'))
  const a = dom && celula(dom.linhas, t('domicilios', 'a4_classe_a'))
  const de = dom && celula(dom.linhas, t('domicilios', 'a4_classe_de'))
  const a5 = dom && celula(dom.linhas, t('domicilios', 'a5_banda_larga_fixa'))
  const e1a = prov && celula(prov.linhas, t('provedores', 'e1a'))
  const c1 = prov && celula(prov.linhas, t('provedores', 'c1'))
  const fd = (tab: string) => `TIC Domicílios ${dom?.edicao}, tabela ${tab} (Cetic.br|NIC.br)`
  const fp = (tab: string) => `TIC Provedores ${prov?.edicao}, tabela ${tab} (Cetic.br|NIC.br, autodeclaração)`
  return limitar([
    a4 && dom && { id: 'a4', selo: 'estimado', fonte: fd('A4'), dataRef: String(dom.edicao),
      texto: `${valorComMargem(a4)} dos domicílios têm acesso à Internet${a && de ? `; na classe social DE a proporção é ${valorComMargem(de)} e na classe A, ${valorComMargem(a)}` : ''}.` },
    a5 && dom && { id: 'a5', selo: 'estimado', fonte: fd('A5'), dataRef: String(dom.edicao),
      texto: `${valorComMargem(a5)} dos domicílios com acesso à Internet usam banda larga fixa (o universo são os domicílios com acesso à Internet).` },
    e1a && prov && { id: 'e1a', selo: 'estimado', fonte: fp('E1A'), dataRef: String(prov.edicao),
      texto: `${valorComMargem(e1a)} das empresas provedoras declaram participar do IX.br.` },
    c1 && prov && { id: 'c1', selo: 'estimado', fonte: fp('C1'), dataRef: String(prov.edicao),
      texto: `${valorComMargem(c1)} das empresas provedoras declaram ter sistema autônomo.` },
  ])
}
