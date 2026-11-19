// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { BlocoProps } from '../../entidade/registry'
import type { PrefixoCtx } from '../contexto'

const CONFIANCA: Record<string, string> = {
  exact_address: 'endereço exato', cep_centroid: 'centro do CEP', city_centroid: 'centro do município', unknown: 'desconhecida',
}

export function GeoBloco({ dados }: BlocoProps<PrefixoCtx>) {
  const { info } = dados
  return (
    <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2 text-sm">
      <div><dt className="text-xs text-gray-500">Estado</dt><dd>{[info.uf, info.country].filter(Boolean).join(' · ') || '—'}</dd></div>
      <div><dt className="text-xs text-gray-500">Confiança</dt><dd>{CONFIANCA[info.geo_confidence ?? ''] ?? info.geo_confidence ?? '—'}</dd></div>
      <div><dt className="text-xs text-gray-500">Fonte</dt><dd>{info.geo_source ?? '—'}</dd></div>
    </dl>
  )
}
