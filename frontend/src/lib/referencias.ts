// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/**
 * Referências normativas citadas na tela (D11): um texto só para cada regra, com ato e data conferidos em fonte primária.
 * Só entra aqui o que `analise-obint/referencias-normativas.md` marca como confirmado; faixa ou critério sem referência confirmada
 * aparece sem citação. As faixas e classificações são "método do projeto", sem tom de regra legal. Nenhum texto qualifica infração.
 */
import type { FaixaHhi } from '../types/api'

/**
 * Nome do sistema de coleta. O rótulo "SICI" permanece na interface, na API e no MCP (nome de uso consolidado nos produtos, nas
 * collections e nos links); onde a norma aparece, a base vigente é citada: desde 2022 os acessos são declarados no sistema Coleta de Dados.
 */
export const COLETA_ANATEL = 'sistema Coleta de Dados da Anatel (antigo SICI)'

/** Norma da coleta de acessos (Resolução Anatel nº 774/2025; periodicidade nos manuais de coleta e despachos decisórios por serviço). */
export const NOTA_COLETA_ANATEL = `As prestadoras declaram os acessos mensalmente à Anatel no ${COLETA_ANATEL}, conforme a Resolução Anatel nº 774/2025 e os despachos decisórios de cada serviço. `
  + 'O OBINT mostra o que foi declarado e não avalia o cumprimento da norma.'

/** Acessos de credenciado de rede virtual (RGST, Resolução Anatel nº 777/2025). */
export const NOTA_REDE_VIRTUAL = 'Acessos de credenciados de rede virtual (MVNO) são declarados pela prestadora de origem, identificados pelo CNPJ do credenciado '
  + '(Manual de Coleta de Acessos SMP da Anatel; Regulamento Geral dos Serviços de Telecomunicações, Resolução Anatel nº 777/2025).'

/** Atualização dos valores de multa (RASA, Resolução Anatel nº 589/2012, arts. 34 e 36; Lei nº 10.522/2002, art. 37-A). */
export const NOTA_ATUALIZACAO_MULTAS = 'Os valores de multa são atualizados pela Selic, com multa moratória de 0,33% ao dia até 20% em caso de atraso '
  + '(RASA, Resolução Anatel nº 589/2012, arts. 34 e 36; Lei nº 10.522/2002, art. 37-A). O saldo atualizado é o informado pela Anatel; o OBINT não o recalcula.'

/** Multa constituída é a registrada pela Anatel; ainda pode estar em discussão administrativa ou judicial. */
export const NOTA_MULTA_CONSTITUIDA = 'Multa constituída não é condenação definitiva.'

/** Limites de faixa de HHI (método do projeto, coincidente com o Guia H do CADE, 2016; o HHI municipal é cálculo do projeto). */
export const NOTA_FAIXAS_HHI = 'Faixas de HHI adotadas pelo OBINT (método do projeto): abaixo de 1.500, de 1.500 a 2.499 e 2.500 ou mais. '
  + 'São os mesmos limiares do Guia para Análise de Atos de Concentração Horizontal do CADE (2016). '
  + 'Aplicar o HHI ao município ou à UF, sobre acessos declarados, é cálculo do projeto; a faixa não é classificação do CADE nem da Anatel.'

export const ROTULO_FAIXA_HHI: Record<FaixaHhi, string> = {
  competitivo: 'HHI abaixo de 1.500',
  moderado: 'HHI de 1.500 a 2.499',
  concentrado: 'HHI de 2.500 ou mais',
}

/** Faixa do projeto para um HHI (0 a 10.000), a mesma regra de `products/sici_indicadores/build.py` (`faixa_hhi`). */
export function faixaHhi(hhi: number): FaixaHhi {
  return hhi < 1500 ? 'competitivo' : hhi < 2500 ? 'moderado' : 'concentrado'
}

export const rotuloFaixaHhi = (f: string | null | undefined) => (f ? ROTULO_FAIXA_HHI[f as FaixaHhi] ?? f : '—')
