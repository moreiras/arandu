// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../../components/layout/LinkDatado'
import type { BlocoProps } from '../../entidade/registry'
import type { MunicipioCtx } from '../contexto'
import { fmtCnpj } from '../ui'

/** ASNs próprios das operadoras que atendem o município (fixo e móvel), cada um com a operadora de origem. */
export function RedeBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const mapa = new Map<number, { empresa: string; cnpj: string }>()
  for (const o of [...(dados.fixo?.operadores ?? []), ...(dados.movel?.operadores ?? [])]) {
    for (const a of o.asns) if (!mapa.has(a)) mapa.set(a, { empresa: o.empresa || fmtCnpj(o.cnpj), cnpj: o.cnpj })
  }
  const lista = [...mapa.entries()].sort((a, b) => a[1].empresa.localeCompare(b[1].empresa))
  return (
    <div className="flex flex-wrap gap-2">
      {lista.map(([asn, o]) => (
        <Link key={asn} to={`/asn/${asn}`} title={o.empresa}
          className="px-2.5 py-1 rounded border border-primario-200 bg-primario-50 text-primario-700 text-xs hover:bg-primario-100">
          AS{asn} <span className="text-primario-500">· {o.empresa}</span>
        </Link>
      ))}
    </div>
  )
}
