// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { cobre } from '../../../lib/prefixo'
import type { BlocoProps } from '../../entidade/registry'
import type { PrefixoCtx } from '../contexto'

/** O que o Registro.br e a tabela global dizem deste prefixo, pelo documento do AS de origem. */
export function RegistroBloco({ dados }: BlocoProps<PrefixoCtx>) {
  const { prefix, asn } = dados
  if (!asn) return <p className="text-sm text-gray-500">Documento do AS de origem indisponível neste snapshot.</p>
  const rir = [...(asn.rir_prefixes_v4 ?? []), ...(asn.rir_prefixes_v6 ?? [])]
  const global = [...(asn.global_prefixes_v4 ?? []), ...(asn.global_prefixes_v6 ?? [])]
  const alocado = rir.includes(prefix)
  const alocadoMaior = !alocado ? rir.find((p) => cobre(p, prefix)) : undefined
  const visivel = global.includes(prefix)
  return (
    <ul className="text-sm space-y-1">
      <li>Alocado ao AS pelo Registro.br: <strong>{alocado ? 'sim' : alocadoMaior ? `dentro de ${alocadoMaior}` : 'não consta'}</strong></li>
      <li>Visível na tabela de rotas global: <strong>{visivel ? 'sim' : 'não'}</strong></li>
    </ul>
  )
}
