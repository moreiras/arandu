// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { PrefixoInfo } from '../../services/api'
import type { ASNDocument } from '../../types/api'

/** O que um bloco da página de prefixo recebe: o prefixo geolocalizado e, quando já chegou, o documento do AS originador. */
export interface PrefixoCtx {
  prefix: string
  info: PrefixoInfo
  asn?: ASNDocument
  carregandoAsn: boolean
  date: string | null
}
