// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MetGroup, MetCell, num } from '../ui'
import type { BlocoProps } from '../../entidade/registry'
import type { PttCtx } from '../contexto'

export function PotencialBloco({ dados }: BlocoProps<PttCtx>) {
  const { potential } = dados
  return (
    <MetGroup title="Potencial" borderClass="border-gray-200" titleClass="text-gray-500">
      <MetCell
        label="+ ASes op. perto (80km)"
        value={num(potential?.nearby_asn_count)}
        tooltip="ASes com sede ou prefixos anunciados a até 80km de algum ponto deste PTT que ainda não participam diretamente nem originam prefixos nele"
      />
      <MetCell
        label="Potencial de IPv6 (/48s)"
        value={num(potential?.v6_prefixes_48)}
        tooltip="Prefixos IPv6 já anunciados neste PTT, mais todos os prefixos IPv6 geolocalizados a até 80 km de algum PIX, agregados e contados em equivalentes a /48"
      />
      <MetCell
        label="Potencial de IPv4 (/24s)"
        value={num(potential?.v4_prefixes_24)}
        tooltip="Prefixos IPv4 já anunciados neste PTT, mais todos os prefixos IPv4 geolocalizados a até 80 km de algum PIX, agregados e contados em equivalentes a /24"
      />
      <MetCell
        label="Potencial de usuários finais"
        value={num(potential?.estimated_users_total)}
        tooltip="Para cada AS BR com prefixos IPv4 na união, estima usuários proporcionalmente à fração do espaço anunciado do AS coberta pela união (mesma metodologia do indicador 'Usuários visíveis')"
      />
    </MetGroup>
  )
}
