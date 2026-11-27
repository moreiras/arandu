// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { TEXTO_ZERO_REGISTRADO, estadoMargem } from './margem'
import { celula, TEMAS, type EntradaCetic, type Pesquisa } from './sinteseCetic'

const p1 = (v: number) => v.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

/** Um cartão de Uso da Internet: o valor com a margem, o universo, a pesquisa e a edição, e a tabela de onde sai (PT-22 / uso-da-internet 5.2). */
export interface CartaoCetic {
  id: string
  pesquisa: Pesquisa
  tabela: string
  /** O que o número conta, com o universo ("dos domicílios têm acesso à Internet"). */
  rotulo: string
  valor: string
  /** Margem de erro de 95% já escrita, ou o aviso de margem zero registrada ou não publicada. */
  margem: string
  /** Pesquisa, edição e tabela, na ordem da citação. */
  fonte: string
  edicao: string
  /** Frase de leitura (classe social, denominador); opcional. */
  nota?: string
}

function valorEMargem(l: { proporcao: number | null; margem_proporcao: number | null }): { valor: string; margem: string } {
  const v = l.proporcao as number
  const estado = estadoMargem(v, l.margem_proporcao, 'proporcao')
  if (estado === 'zero_registrado') return { valor: `${p1(v)}%`, margem: TEXTO_ZERO_REGISTRADO }
  const m = l.margem_proporcao
  return { valor: `${p1(v)}%`, margem: m == null ? 'margem não publicada' : `±${p1(m)}${estado === 'precisao_baixa' ? '; precisão baixa' : ''}` }
}

/**
 * Os cartões de Uso da Internet, lidos das MESMAS linhas das tabelas oficiais que a página mostra e dos mesmos temas da síntese (`temasSintese.json`): acesso à Internet
 * (A4), banda larga fixa entre os domicílios com Internet (A5, com o universo no rótulo), acesso na classe social DE (A4), provedores no IX.br (E1A) e com sistema
 * autônomo (C1). A escolha dos cinco é editorial (acesso, conexão e interconexão; nenhum ordenado por melhor ou pior). O que a edição não traz não gera cartão.
 */
export function cartoesCetic(dom: EntradaCetic | undefined, prov: EntradaCetic | undefined): CartaoCetic[] {
  const t = (p: Pesquisa, id: string) => TEMAS[p].find((x) => x.id === id)!
  const out: CartaoCetic[] = []
  const d = (id: string, rotulo: string, nota?: string) => {
    const tema = t('domicilios', id)
    const l = dom && celula(dom.linhas, tema)
    if (l && dom) out.push({ id, pesquisa: 'domicilios', tabela: tema.tabela, rotulo, ...valorEMargem(l), fonte: `TIC Domicílios ${dom.edicao}, tabela ${tema.tabela}`, edicao: String(dom.edicao), nota })
  }
  const p = (id: string, rotulo: string) => {
    const tema = t('provedores', id)
    const l = prov && celula(prov.linhas, tema)
    if (l && prov) out.push({ id, pesquisa: 'provedores', tabela: tema.tabela, rotulo, ...valorEMargem(l), fonte: `TIC Provedores ${prov.edicao}, tabela ${tema.tabela} (autodeclaração)`, edicao: String(prov.edicao) })
  }
  d('a4', 'dos domicílios têm acesso à Internet')
  d('a5_banda_larga_fixa', 'dos domicílios com acesso à Internet usam banda larga fixa', 'Universo: domicílios com acesso à Internet, não todos os domicílios.')
  d('a4_classe_de', 'dos domicílios da classe social DE têm acesso à Internet', 'Duas estimativas só diferem de modo claro quando as faixas não se sobrepõem.')
  p('e1a', 'das empresas provedoras declaram participar do IX.br')
  p('c1', 'das empresas provedoras declaram ter sistema autônomo')
  return out
}
