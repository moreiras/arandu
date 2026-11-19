// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { ASNStabilityPanel } from '../../../components/bgp/ASNStabilityPanel'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'

export function EstabilidadeBloco({ dados }: BlocoProps<AsnCtx>) {
  const { doc, asnStability, stabilityData, asnWeeks } = dados
  return (
    <ASNStabilityPanel
      stability={asnStability}
      eppdStats={stabilityData?.epppd_stats}
      timestamps={stabilityData?.hourly_global.timestamps}
      weeks={asnWeeks}
    />
  )
}
