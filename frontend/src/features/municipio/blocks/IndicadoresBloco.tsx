// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../../components/layout/LinkDatado'
import type { BlocoProps } from '../../entidade/registry'
import type { MunicipioCtx } from '../contexto'
import { fmtCnpj } from '../../operadora/ui'

const n = (v: number) => v.toLocaleString('pt-BR')
// quem não declarou no mês pode vir sem nome em snapshots antigos (MUN-E1): o CNPJ, com link, no lugar do vazio
const quem = (e: { cnpj: string; empresa: string }) => <Link to={`/operadora/${e.cnpj}`} className="text-primario-700 hover:underline">{e.empresa || `CNPJ ${fmtCnpj(e.cnpj)}`}</Link>
const pct = (v: number | null | undefined) => (v == null ? '—' : `${v > 0 ? '+' : ''}${v.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%`)

/** Variação dos acessos fixos declarados no município e quem mais ganhou e perdeu em 12 meses. Dado declarado; sem juízo sobre a causa. */
export function IndicadoresBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const i = dados.indicadores!
  return (
    <div className="space-y-2 text-sm">
      <dl className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div><dt className="text-xs text-gray-500">Acessos declarados ({i.mes_referencia})</dt><dd className="text-lg font-semibold tabular-nums">{n(i.acessos)}</dd></div>
        <div><dt className="text-xs text-gray-500">Variação contra o mês anterior</dt><dd className="text-lg font-semibold tabular-nums">{pct(i.var_mm_pct)}</dd></div>
        <div><dt className="text-xs text-gray-500">Variação em 12 meses</dt><dd className="text-lg font-semibold tabular-nums">{pct(i.var_aa_pct)}</dd></div>
        <div><dt className="text-xs text-gray-500">Operadoras declarantes</dt><dd className="text-lg font-semibold tabular-nums">{n(i.n_operadoras)}</dd></div>
      </dl>
      {i.ganho_aa && <p className="text-xs text-gray-600">Maior ganho em 12 meses: {quem(i.ganho_aa)} (+{n(i.ganho_aa.acessos)} acessos).</p>}
      {i.perda_aa && <p className="text-xs text-gray-600">Maior perda em 12 meses: {quem(i.perda_aa)} ({n(i.perda_aa.acessos)} acessos).</p>}
    </div>
  )
}
