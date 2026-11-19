// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { IXPGeoMap } from '../../../components/maps/IXPGeoMap'
import type { BlocoProps } from '../../entidade/registry'
import type { PttCtx } from '../contexto'

export function MapaGeoBloco({ dados }: BlocoProps<PttCtx>) {
  const { code, date } = dados
  return (
    <div>
      <h2 className="text-base font-semibold text-gray-800 mb-3">
        Distribuição geográfica
      </h2>
      <IXPGeoMap code={code!} date={date ?? undefined} />
    </div>
  )
}
