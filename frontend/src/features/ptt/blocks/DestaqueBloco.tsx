// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { HeroStat, num, pct } from '../ui'
import type { BlocoProps } from '../../entidade/registry'
import type { PttCtx } from '../contexto'

export function DestaqueBloco({ dados }: BlocoProps<PttCtx>) {
  const { v6, v6idx, v4, v4idx, par, brOriginUnion, cbrAsns, estUsers, usuariosBrTotal } = dados
  return (
    <div className="rounded-xl border border-gray-200 bg-gradient-to-br from-gray-50 to-white px-4 py-3">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-x-3 gap-y-2 sm:divide-x divide-gray-200">
        <HeroStat
          target={estUsers?.estimated_users}
          label="usuários brasileiros visíveis via este IXP"
          sub={`de ${num(usuariosBrTotal)} usuários totais estimados por medições do APNIC`}
          color="#0891b2"
        />
        <HeroStat
          target={par}
          label="participantes"
          sub="registrados no IX.br"
          color="#d97706"
        />
        <HeroStat
          target={brOriginUnion}
          label="originadores BR"
          sub={cbrAsns != null ? `${pct(cbrAsns, 1)} dos AS BR` : 'AS BR com prefixo aqui'}
          color="#2563eb"
        />
        <HeroStat
          target={v6idx?.br_prefix_coverage_pct ?? v6?.br_prefix_coverage_pct}
          label="cobertura IPv6 BR"
          sub="do espaço BR visível aqui"
          color="#8b5cf6"
          isPct
        />
        {/* a cobertura IPv4 ao lado da IPv6 (IPv6 primeiro). */}
        <HeroStat
          target={v4idx?.br_prefix_coverage_pct ?? v4?.br_prefix_coverage_pct}
          label="cobertura IPv4 BR"
          sub="do espaço BR visível aqui"
          color="#2563eb"
          isPct
        />
      </div>
    </div>
  )
}
