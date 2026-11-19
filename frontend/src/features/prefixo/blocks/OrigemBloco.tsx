// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import type { BlocoProps } from '../../entidade/registry'
import type { PrefixoCtx } from '../contexto'

export function OrigemBloco({ dados }: BlocoProps<PrefixoCtx>) {
  const { info, asn, carregandoAsn } = dados
  const org = info.geo_org
  return (
    <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2 text-sm">
      <div><dt className="text-xs text-gray-500">AS de origem</dt>
        <dd>{info.origin_asn != null ? <Link to={`/asn/${info.origin_asn}`} className="font-mono text-primario-600 hover:underline">AS{info.origin_asn}</Link> : '—'}
          {asn?.name && <span className="ml-2 text-gray-600">{asn.name}</span>}{carregandoAsn && <span className="ml-2 text-xs text-gray-400">carregando…</span>}</dd></div>
      <div><dt className="text-xs text-gray-500">Organização</dt>
        <dd>{org?.name ? (org.cnpj ? <Link to={`/operadora/${org.cnpj}`} className="text-primario-600 hover:underline">{org.name}</Link> : org.name) : '—'}</dd></div>
      <div><dt className="text-xs text-gray-500">Família</dt><dd>IPv{info.ip_version}</dd></div>
    </dl>
  )
}
