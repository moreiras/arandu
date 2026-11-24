// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

/** Texto fixo do MOAS indisponível (o mesmo da aba de `/bgp`). */
export const MOAS_INDISPONIVEL = 'A análise de origem múltipla (MOAS) não está disponível: a tabela global usada guarda uma origem por prefixo, então não detecta prefixos anunciados por mais de um AS. A ausência de dado aqui não indica ausência de MOAS.'

/**
 * MOAS (mais de uma origem): indisponível até haver coleta que guarde todas as origens de um prefixo. Não busca a análise de
 * roteamento (~14 MB): ela traria `moas` nulo, e uma lista vazia seria lida como "nenhuma origem múltipla".
 */
export function MoasBloco() {
  return <p className="text-sm text-gray-600" data-testid="moas-indisponivel">{MOAS_INDISPONIVEL}</p>
}
