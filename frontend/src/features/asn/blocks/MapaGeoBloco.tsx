// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { ASNGeoMap } from '../../../components/maps/ASNGeoMap'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'

export function MapaGeoBloco({ dados }: BlocoProps<AsnCtx>) {
  const { doc, date } = dados
  return (
    <div>
      <h2 className="text-base font-semibold text-gray-800 mb-3">
        Distribuição geográfica de prefixos
      </h2>
      <ASNGeoMap asn={doc.asn} date={date ?? undefined} ixpPresence={doc.ixp_presence ?? {}} />
    </div>
  )
}
