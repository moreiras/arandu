// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useEffect, useState } from 'react'
import { coletaDaFamilia, type IXPIndexAfi } from '../../types/api'
import { corLegivel } from '../../lib/contraste'

export function num(v: number | null | undefined, decimals = 0): string {
  if (v == null) return '—'
  return v.toLocaleString('pt-BR', { maximumFractionDigits: decimals })
}

export function pct(v: number | null | undefined, decimals = 2): string {
  if (v == null) return '—'
  return `${v.toFixed(decimals)}%`
}

/** Anima de 0 até o alvo (easeOutCubic). Reinicia quando o alvo muda; com `prefers-reduced-motion: reduce` vai direto ao alvo. */
export function useCountUp(target: number | null | undefined, duration = 900): number {
  const [val, setVal] = useState(0)
  useEffect(() => {
    if (target == null) { setVal(0); return }
    // Movimento reduzido (WCAG 2.2, 2.3.3): o número final, sem animar.
    if (typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { setVal(target); return }
    let raf = 0
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      setVal(target * (1 - Math.pow(1 - t, 3)))
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, duration])
  return val
}

export function HeroStat({
  target, label, sub, color, isPct,
}: {
  target: number | null | undefined
  label: string
  sub?: string
  color: string
  isPct?: boolean
}) {
  const v = useCountUp(target)
  const display =
    target == null ? '—'
      : isPct ? `${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`
      : Math.round(v).toLocaleString('pt-BR')
  return (
    <div className="px-3 py-1">
      <div className="text-2xl sm:text-3xl font-extrabold tabular-nums leading-none" style={{ color: corLegivel(color) }}>
        {display}
      </div>
      <div className="text-xs sm:text-xs text-gray-700 mt-1 leading-tight font-medium">{label}</div>
      {sub && <div className="text-xs text-gray-400 leading-tight">{sub}</div>}
    </div>
  )
}

export function getIndexAfi(afi: unknown): IXPIndexAfi | null {
  if (!afi || typeof afi !== 'object') return null
  if (!('total_routes' in (afi as object))) return null
  if (coletaDaFamilia(afi as IXPIndexAfi) !== 'ok') return null       // tabela vazia do looking glass: sem medida, não 0%
  return afi as IXPIndexAfi
}

// ---- Componente de célula de métrica ----------------------------------------

export function MetCell({
  label,
  value,
  tooltip,
  color,
}: {
  label: string
  value: string
  tooltip?: string
  color?: string
}) {
  return (
    <div
      className="bg-white rounded border border-gray-200 px-3 py-2 min-w-0"
      title={tooltip}
    >
      <div className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-0.5 break-words">
        {label}
      </div>
      <div className={`text-base font-bold tabular-nums truncate ${color ?? 'text-gray-900'}`}>
        {value}
      </div>
    </div>
  )
}

// ---- Seção de grupo de métricas ---------------------------------------------

export function MetGroup({
  title,
  borderClass,
  titleClass,
  children,
}: {
  title: string
  borderClass: string
  titleClass: string
  children: React.ReactNode
}) {
  return (
    <div className={`rounded-lg border ${borderClass} px-4 py-3`}>
      <div className={`text-xs font-semibold uppercase tracking-widest mb-2 ${titleClass}`}>
        {title}
      </div>
      <div className="grid grid-cols-2 min-[420px]:grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
        {children}
      </div>
    </div>
  )
}

// ---- CoverageBar inline -----------------------------------------------------

export function PctCell({
  label,
  value,
  tooltip,
}: {
  label: string
  value: number | null | undefined
  tooltip?: string
}) {
  const v = value ?? null
  // cor única: a porcentagem é um fato, sem faixa de "bom" ou "ruim" (IXP-E10)
  const color = v == null ? 'text-gray-400' : 'text-gray-800'
  const barColor = v == null ? 'bg-gray-200' : 'bg-primario-300'
  return (
    <div className="bg-white rounded border border-gray-200 px-3 py-2 min-w-0" title={tooltip}>
      <div className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-0.5 break-words">
        {label}
      </div>
      <div className={`text-base font-bold tabular-nums ${color}`}>
        {v != null ? `${v.toFixed(2)}%` : '—'}
      </div>
      <div className="mt-1 h-1 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${barColor}`}
          style={{ width: `${Math.min(v ?? 0, 100)}%` }}
        />
      </div>
    </div>
  )
}
