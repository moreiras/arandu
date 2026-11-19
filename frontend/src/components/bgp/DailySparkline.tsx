interface Props {
  values: number[]
  width?:  number
  height?: number
}

export function DailySparkline({ values, width = 70, height = 24 }: Props) {
  if (!values || values.length === 0) return null

  const max = Math.max(...values, 1)
  const w   = width / values.length
  const pad = 2

  return (
    <svg width={width} height={height} aria-hidden="true" className="inline-block">
      {values.map((v, i) => {
        const barH = Math.max(((v / max) * (height - pad)), 1)
        const x    = i * w
        const y    = height - barH
        const fill = v === max && max > 0 ? '#f97316' : '#93c5fd'
        return (
          <rect
            key={i}
            x={x + 1}
            y={y}
            width={Math.max(w - 2, 1)}
            height={barH}
            fill={fill}
            rx={1}
          >
            <title>{`Dia ${i + 1}: ${v} eventos`}</title>
          </rect>
        )
      })}
    </svg>
  )
}
