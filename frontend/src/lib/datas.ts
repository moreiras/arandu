// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { formatarReferencia } from '../components/entidade/proveniencia'

/** Único formato de data da interface: DD/MM/AAAA (ou MM/AAAA quando o dado é mensal). Valor ausente ou desconhecido vira "—". */
export const formatarData = formatarReferencia
