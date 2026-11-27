// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Contagens da camada de outorgas SCM por declaração ao SICI (PT-26, MAPA 5.4): total, com e sem acessos declarados, com ASN e a divisão por UF. */
export interface ResumoScm {
  mes: string
  total: number
  com: number
  sem: number
  /** Feições sem o campo `sici_ativo` (snapshot antigo): nada é afirmado sobre elas. */
  semInformacao: number
  comAsn: number
  porUf: Array<{ uf: string; total: number; com: number; sem: number; comAsn: number }>
}

const verdadeiro = (v: unknown) => v === true || v === 'true'

/** Conta sobre as feições que chegaram (o recorte já aplicado); UFs em ordem alfabética, sem ordenar por volume. */
export function resumirScm(fc: GeoJSON.FeatureCollection | null | undefined): ResumoScm | null {
  if (!fc || !Array.isArray(fc.features) || fc.features.length === 0) return null
  const r: ResumoScm = { mes: '', total: 0, com: 0, sem: 0, semInformacao: 0, comAsn: 0, porUf: [] }
  const por = new Map<string, { uf: string; total: number; com: number; sem: number; comAsn: number }>()
  for (const f of fc.features) {
    const p = (f.properties ?? {}) as Record<string, unknown>
    const uf = typeof p.uf === 'string' && p.uf ? p.uf : '—'
    const u = por.get(uf) ?? { uf, total: 0, com: 0, sem: 0, comAsn: 0 }
    por.set(uf, u)
    r.total++; u.total++
    if (p.sici_ativo === undefined || p.sici_ativo === null) r.semInformacao++
    else if (verdadeiro(p.sici_ativo)) { r.com++; u.com++ } else { r.sem++; u.sem++ }
    if (!r.mes && typeof p.sici_mes_referencia === 'string') r.mes = p.sici_mes_referencia
    if (verdadeiro(p.has_asn)) { r.comAsn++; u.comAsn++ }
  }
  r.porUf = [...por.values()].sort((a, b) => a.uf.localeCompare(b.uf, 'pt-BR'))
  return r
}
