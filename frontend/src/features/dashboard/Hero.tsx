// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** KPIs sobre o mapa (contagem animada) da Visão geral. */
import { useState, useEffect } from 'react'
import type { SnapshotSummary } from '../../types/api'
import { fmtLarge, fmtPct } from './formato'
import { corLegivel } from '../../lib/contraste'

// ─── Hero: KPIs com count-up sobre o mapa ─────────────────────────────────────

/** Anima de 0 até o alvo (easeOutCubic). Reinicia quando o alvo muda. */
export function useCountUp(target: number | null | undefined, duration = 900): number {
  // sem animação para quem pede movimento reduzido.
  if (typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) duration = 1
  const [val, setVal] = useState(0)
  useEffect(() => {
    if (target == null) { setVal(0); return }
    let raf = 0
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3)
      setVal(target * eased)
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, duration])
  return val
}

export function HeroStat({
  target,
  label,
  sub,
  isPct,
  color,
}: {
  target: number | null | undefined
  label: string
  sub?: string
  isPct?: boolean
  color: string
}) {
  const v = useCountUp(target)
  const display = target == null ? '—' : isPct ? fmtPct(v) : fmtLarge(Math.round(v))
  return (
    <div className="px-3 py-1">
      <div
        className="text-2xl sm:text-3xl font-extrabold tabular-nums leading-none"
        style={{ color: corLegivel(color) }}
      >
        {display}
      </div>
      <div className="text-xs sm:text-xs text-gray-700 mt-1 leading-tight font-medium">{label}</div>
      {sub && <div className="text-xs text-gray-400 leading-tight">{sub}</div>}
    </div>
  )
}

export function HeroKpis({ summary, scmTotal }: { summary: SnapshotSummary | null | undefined; scmTotal?: number | null }) {
  const s = summary
  const gt = s?.global_table
  const ixp = s?.ixp_aggregate
  const pctBrInIxp =
    ixp?.br_asns_origin_union_count != null && gt?.br_asns_in_ft
      ? (ixp.br_asns_origin_union_count / gt.br_asns_in_ft) * 100
      : null
  const pctAsnV4 =
    s?.br_asns_ft_v4 != null && gt?.br_asns_in_ft
      ? (s.br_asns_ft_v4 / gt.br_asns_in_ft) * 100
      : null
  const pctAsnV6 =
    s?.br_asns_ft_v6 != null && gt?.br_asns_in_ft
      ? (s.br_asns_ft_v6 / gt.br_asns_in_ft) * 100
      : null

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 divide-x divide-y lg:divide-y-0 divide-gray-100">
        <HeroStat target={s?.total_asns_br} label="ASNs brasileiros" sub="alocados Registro.br" color="#2563eb" />
        <HeroStat target={s?.br_apnic_users_total} label="usuários BR estimados" sub="por medições do APNIC" color="#0891b2" />
        <HeroStat target={gt?.br_asns_in_ft} label="ASNs BR na full table" sub="tabela global de roteamento" color="#0369a1" />
        <HeroStat target={pctAsnV6} isPct label="visíveis com IPv6" sub="dos ASNs BR na tabela global" color="#8b5cf6" />
        <HeroStat target={pctAsnV4} isPct label="visíveis com IPv4" sub="dos ASNs BR na tabela global" color="#0ea5e9" />
        <HeroStat target={pctBrInIxp} isPct label="ASNs BR no IX.br" sub="dos visíveis na tabela global" color="#d97706" />
        <HeroStat target={scmTotal ?? null} label="outorgas SCM" sub="prestadoras autorizadas Anatel" color="#7c3aed" />
      </div>
    </div>
  )
}
