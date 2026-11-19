// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { HistoricoBloco } from '../../types/api'
import type { BlocoProps } from '../entidade/registry'
import { LinhaDoTempo } from './LinhaDoTempo'

/** Blocos "Linha do tempo" registrados nas páginas de entidade (os registros são `.ts`, sem JSX). O dado vem do `include=historico` do perfil. */
type ComHistorico = { historico?: HistoricoBloco | null }
export const LinhaDoTempoAsn = ({ dados }: BlocoProps<ComHistorico>) => <LinhaDoTempo historico={dados.historico} escopo="asn" />
export const LinhaDoTempoPtt = ({ dados }: BlocoProps<ComHistorico>) => <LinhaDoTempo historico={dados.historico} escopo="ixp" />
export const LinhaDoTempoOperadora = ({ dados }: BlocoProps<ComHistorico>) => <LinhaDoTempo historico={dados.historico} escopo="operadora" />
export const LinhaDoTempoUf = ({ dados }: BlocoProps<ComHistorico>) => <LinhaDoTempo historico={dados.historico} escopo="uf" />
