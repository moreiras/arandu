// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/**
 * Corpo do exemplo de consulta (DADOS-E2). Quem atende uma UF está em `acessos_municipio` (uma linha por município e operadora, com `mes_referencia`
 * do SICI), não em `operadoras`, cuja `uf_sede` é a sede da empresa e não onde estão os clientes. `tests/products/test_t4_dados_exemplo.py` roda este
 * corpo sobre o dataset sintético.
 */
export const CORPO_EXEMPLO_CONSULTA = '{"filter":{"field":"uf","op":"eq","value":"ES"},"group_by":["empresa","mes_referencia"],"aggregate":[{"fn":"sum","field":"acessos"}],"sort":[{"field":"sum_acessos","dir":"desc"}],"limit":5}'
