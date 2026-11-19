// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { BlocoProps } from '../../entidade/registry'
import type { OperadoraCtx } from '../contexto'

const n = (v: number | undefined | null) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const pct = (v: number | null | undefined) => (v == null ? 'sem base de comparação' : `${v > 0 ? '+' : ''}${v.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%`)

/**
 * Indicadores do SICI da operadora: parcela dos acessos declarados, posição e variações. Dado declarado à Anatel; a parcela é sobre acessos
 * declarados, não sobre receita. Se o CNPJ tem outorga SCM sem declaração no mês, o bloco diz só o fato e o mês (política editorial).
 */
export function IndicadoresBloco({ dados }: BlocoProps<OperadoraCtx>) {
  const i = dados.indicadores!
  const sem = i.sem_declaracao
  return (
    <div className="space-y-3 text-sm">
      {i.acessos != null && (
        <dl className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div><dt className="text-xs text-gray-500">Acessos declarados ({i.mes_referencia})</dt><dd className="text-lg font-semibold tabular-nums">{n(i.acessos)}</dd></div>
          <div><dt className="text-xs text-gray-500">Parcela dos acessos declarados no país</dt><dd className="text-lg font-semibold tabular-nums">{i.share_br?.toLocaleString('pt-BR', { maximumFractionDigits: 3 })}%</dd></div>
          <div><dt className="text-xs text-gray-500">Posição por acessos</dt><dd className="text-lg font-semibold tabular-nums">{n(i.posicao_br)}º</dd></div>
          <div><dt className="text-xs text-gray-500">Variação em 12 meses</dt><dd className="text-lg font-semibold tabular-nums">{i.var_aa ? pct(i.var_aa.pct) : '—'}</dd>
            {i.var_aa && <dd className="text-xs text-gray-500 tabular-nums">{i.var_aa.abs > 0 ? '+' : ''}{n(i.var_aa.abs)} acessos</dd>}</div>
        </dl>
      )}
      {i.var_mm && <p className="text-xs text-gray-500">Variação contra o mês anterior: {pct(i.var_mm.pct)} ({i.var_mm.abs > 0 ? '+' : ''}{n(i.var_mm.abs)} acessos).</p>}
      {i.em_declinio && <p className="text-xs text-gray-600">Os acessos declarados caíram por {i.meses_declinio} meses seguidos até {i.mes_referencia}.</p>}
      {i.parou_de_declarar && (
        <p className="text-xs text-gray-600">
          Sem declaração ao SICI desde {i.parou_de_declarar.ultimo_mes_declarado} ({i.parou_de_declarar.meses_sem_declarar} meses); no último mês declarado eram {n(i.parou_de_declarar.acessos_no_ultimo_mes)} acessos.
        </p>
      )}
      {sem && (
        <p className="text-xs text-gray-600" data-testid="sem-declaracao">
          Outorga SCM sem acessos declarados ao SICI em {i.mes_referencia}
          {sem.usuarios_apnic != null && <>; usuários estimados (APNIC) nos ASNs do CNPJ: {n(sem.usuarios_apnic)}</>}
          {sem.grupo_declara && <>; outro CNPJ do mesmo grupo societário declarou no mês</>}.
        </p>
      )}
    </div>
  )
}
