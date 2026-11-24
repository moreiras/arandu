import { useMemo, useState } from 'react'
import type { SiciSeriePoint } from '../../types/api'

const PAD = { top: 10, right: 8, bottom: 20, left: 52 }

/**
 * Série mensal de acessos, com split B2C/B2B empilhado.
 *
 * SVG puro e sem dependência: a série tem no máximo algumas dezenas de pontos e o
 * projeto ainda não carrega biblioteca de gráficos no bundle da página do AS.
 */
export function AccessHistoryChart({
  serie,
  height = 180,
  meses = 24,
  soTotal = false,
}: {
  serie: SiciSeriePoint[]
  height?: number
  meses?: number
  /** A série só tem o total do mês (sem PF/PJ): sem área nem legenda B2C e sem B2C/B2B na dica (PANORAMA-E2). */
  soTotal?: boolean
}) {
  const [hover, setHover] = useState<number | null>(null)
  const pts = useMemo(() => serie.slice(-meses), [serie, meses])
  const width = 720

  const { max, path, areaPf, xs } = useMemo(() => {
    const max = Math.max(1, ...pts.map(p => p[1]))
    const iw = width - PAD.left - PAD.right
    const ih = height - PAD.top - PAD.bottom
    const x = (i: number) => PAD.left + (pts.length <= 1 ? iw / 2 : (i * iw) / (pts.length - 1))
    const y = (v: number) => PAD.top + ih - (v / max) * ih
    const path = pts.map((p, i) => `${i ? 'L' : 'M'}${x(i)},${y(p[1])}`).join('')
    const areaPf = pts.length
      ? `${pts.map((p, i) => `${i ? 'L' : 'M'}${x(i)},${y(p[2])}`).join('')}L${x(pts.length - 1)},${PAD.top + ih}L${x(0)},${PAD.top + ih}Z`
      : ''
    return { max, path, areaPf, xs: pts.map((_, i) => x(i)) }
  }, [pts, height])

  if (!pts.length) return <div className="text-sm text-gray-400">Sem série disponível.</div>

  const ih = height - PAD.top - PAD.bottom
  const yFor = (v: number) => PAD.top + ih - (v / max) * ih
  const fmt = (n: number) => n.toLocaleString('pt-BR')
  const h = hover != null ? pts[hover] : null

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full" style={{ height }}
           onMouseLeave={() => setHover(null)}>
        {[0, 0.5, 1].map(f => (
          <g key={f}>
            <line x1={PAD.left} x2={width - PAD.right} y1={yFor(max * f)} y2={yFor(max * f)}
                  stroke="#e5e7eb" strokeWidth={1} />
            <text x={PAD.left - 6} y={yFor(max * f) + 3} textAnchor="end"
                  fontSize={10} fill="#9ca3af">{fmt(Math.round(max * f))}</text>
          </g>
        ))}
        {!soTotal && <path d={areaPf} fill="#3b82f6" fillOpacity={0.18} />}
        <path d={path} fill="none" stroke="#1d4ed8" strokeWidth={1.8} />
        {pts.map((p, i) => (
          <rect key={p[0]} x={xs[i] - 6} y={PAD.top} width={12} height={ih}
                fill="transparent" onMouseEnter={() => setHover(i)} />
        ))}
        {hover != null && (
          <line x1={xs[hover]} x2={xs[hover]} y1={PAD.top} y2={PAD.top + ih}
                stroke="#94a3b8" strokeWidth={1} strokeDasharray="3 2" />
        )}
        <text x={PAD.left} y={height - 6} fontSize={10} fill="#9ca3af">{pts[0][0]}</text>
        <text x={width - PAD.right} y={height - 6} fontSize={10} fill="#9ca3af"
              textAnchor="end">{pts[pts.length - 1][0]}</text>
      </svg>
      <div className="text-xs text-gray-500 flex gap-4 mt-0.5">
        <span><span className="inline-block w-2.5 h-2.5 align-middle mr-1 rounded-sm" style={{ background: '#1d4ed8' }} />total</span>
        {!soTotal && <span><span className="inline-block w-2.5 h-2.5 align-middle mr-1 rounded-sm" style={{ background: '#3b82f6', opacity: 0.35 }} />B2C (pessoa física)</span>}
        {h && (
          <span className="ml-auto tabular-nums text-gray-700">
            {h[0]}: <strong>{fmt(h[1])}</strong>{!soTotal && <> · B2C {fmt(h[2])} · B2B {fmt(h[3])}</>}
          </span>
        )}
      </div>
    </div>
  )
}
