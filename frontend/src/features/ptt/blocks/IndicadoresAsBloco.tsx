// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MetGroup, MetCell, PctCell, num } from '../ui'
import type { BlocoProps } from '../../entidade/registry'
import type { PttCtx } from '../contexto'

export function IndicadoresAsBloco({ dados }: BlocoProps<PttCtx>) {
  const { v4, v6, par, dir, org, cbrAsns, cftAsns, totalBrASNs, totalGlobalASNs } = dados
  return (
    <MetGroup title="AS" borderClass="border-gray-200" titleClass="text-gray-500">
      <MetCell
        label="Participantes"
        value={num(par)}
        tooltip="Membros registrados neste IXP no dashboard IX.br — inclui participantes que não usam Route Servers"
      />
      <MetCell
        label="Peers diretos"
        value={num(dir)}
        tooltip="ASNs com sessão com o Route Server deste PTT — união de v6 e v4"
      />
      <MetCell
        label="Originadores"
        value={num(org)}
        tooltip="ASNs que originam algum prefixo visível neste IXP — aprox. o maior entre IPv6 e IPv4"
      />
      <PctCell
        label="Cobertura Registro.br"
        value={cbrAsns}
        tooltip={`% dos ${num(totalBrASNs)} ASNs brasileiros (Registro.br) que aparecem como originadores neste IXP (união IPv6 ∪ IPv4)`}
      />
      <PctCell
        label="Cobertura full table"
        value={cftAsns}
        tooltip={`% dos ${num(totalGlobalASNs)} ASNs presentes na full table global que aparecem como originadores neste IXP`}
      />
    </MetGroup>
  )
}
