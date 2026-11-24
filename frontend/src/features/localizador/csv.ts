// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** CSV da lista de entidades do Localizador (com participação em IXes). `montarCsv` é puro e testado. */
import { MAJOR_IX, asnsDoRaio } from './tipos'
import type { Entity } from './tipos'
import type { PresencaIx } from './calculos'

const esc = (v: string | number | boolean | null | undefined) => {
  if (v == null) return ''
  const s = String(v)
  return /[",\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}
const yn = (b: boolean) => (b ? 'sim' : 'não')

export const CABECALHO_CSV = [
  'asns', 'cnpj', 'nome', 'uf', 'cidade', 'tem_asn', 'tem_scm', 'sede_as_no_raio', 'sede_scm_no_raio',
  'prefixos_v4', 'prefixos_v6', 'acessos_sici_no_raio', 'municipios_sici_no_raio',
  'ix_mais_proximo', 'participa_ix_proximo',
  'participa_sp', 'participa_fortaleza', 'participa_rio', 'participa_brasilia', 'participa_poa',
  'participa_outro_ix', 'membro_ixes', 'anuncia_ixes',
]

/** Texto do CSV (com BOM, para o Excel) da lista de entidades. */
export function montarCsv(entities: Entity[], ixOf: (asn: number) => PresencaIx, nearestIx: string | null, ixLabel: (code: string) => string): string {
  const named = new Set<string>([...(nearestIx ? [nearestIx] : []), ...MAJOR_IX])
  const rows = entities.map(e => {
    const hasAsn = e.asns.length > 0
    // presença em PTT só dos ASNs no raio: os do mesmo CNPJ fora dele não entram (LOC-E3)
    const doRaio = asnsDoRaio(e)
    const m = [...new Set(doRaio.flatMap(a => ixOf(a).m))]
    const o = [...new Set(doRaio.flatMap(a => ixOf(a).o))]
    const ms = new Set(m)
    const ynAs = (b: boolean) => (hasAsn ? yn(b) : '')
    return [
      doRaio.join(' '), e.cnpj ?? '', e.name ?? '', e.uf ?? '', e.city ?? '',
      yn(hasAsn), yn(e.scm), yn(e.fromHq), yn(e.scmHq),
      yn(e.v4), yn(e.v6), e.sici?.acessos ?? '', e.sici?.municipios ?? '',
      hasAsn && nearestIx ? ixLabel(nearestIx) : '',
      ynAs(!!nearestIx && ms.has(nearestIx)),
      ynAs(ms.has('sp')), ynAs(ms.has('ce')), ynAs(ms.has('rj')), ynAs(ms.has('df')), ynAs(ms.has('rs')),
      ynAs(m.some(c => !named.has(c))),
      m.join(' '), o.join(' '),
    ].map(esc).join(',')
  })
  return '﻿' + [CABECALHO_CSV.join(','), ...rows].join('\n')
}

export function baixarCsv(texto: string, nearestIx: string | null) {
  const blob = new Blob([texto], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `localizador${nearestIx ? '-' + nearestIx : ''}.csv`
  link.click()
  URL.revokeObjectURL(url)
}
