// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { BlocoProps } from '../../entidade/registry'
import type { PrefixoCtx } from '../contexto'
import { FONTE_ORIGEM } from '../sintese'

/** O que o Registro.br e a tabela global dizem deste prefixo, pela resposta do servidor (não pelo documento de um AS). */
export function RegistroBloco({ dados }: BlocoProps<PrefixoCtx>) {
  const { info } = dados
  const alocado = info.escopo === 'alocacao_registro_br'
    ? `sim, ao AS${info.registro_asn}`
    : info.escopo === 'rota_dentro_de_alocacao' ? `dentro de ${info.alocacao_registro_br} (AS${info.registro_asn})`
      : info.escopo === 'registro_br_indisponivel' ? 'sem dado do Registro.br neste snapshot' : 'não consta'
  const orig = info.observed_origin_asn
  return (
    <ul className="text-sm space-y-1">
      <li>Alocação do Registro.br: <strong>{alocado}</strong></li>
      <li>Anunciado como está: <strong>{orig != null ? `sim, ${FONTE_ORIGEM[info.observed_origin_fonte ?? ''] ?? 'na tabela de roteamento coletada'}, origem AS${orig}` : 'não, neste snapshot'}</strong></li>
    </ul>
  )
}
