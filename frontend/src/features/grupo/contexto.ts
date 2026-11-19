// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { GrupoDetalhe } from '../../types/api'

/** O que um bloco da página de grupo recebe: a resposta consolidada de `GET /grupos/{grupo_id}`. */
export interface GrupoCtx { grupo: GrupoDetalhe }
