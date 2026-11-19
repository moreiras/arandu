// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Explicações reutilizadas em mais de uma página: um texto só para o mesmo conceito. */

/** "Prefixos / limite": a ocupação do limite de prefixos das sessões com os route servers do IX.br (`recebidas ÷ import_limit`, products/route_servers/build.py). */
export const DICA_PREFIXOS_LIMITE = 'Prefixos recebidos pelo route server nesta sessão ÷ limite de importação (max-prefix) configurado para ela, no pior caso entre as sessões. '
  + 'Perto de 100%, o route server pode derrubar a sessão ao passar do limite. Fonte: Alice-LG do IX.br.'
