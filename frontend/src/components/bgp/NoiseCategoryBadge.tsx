import type { NoiseCategory } from '../../types/bgpStability'

const CONFIG: Record<NoiseCategory, { label: string; color: string; tip: string }> = {
  estavel: {
    label: 'Estável',
    color: 'bg-ok-100 text-ok-800 border-ok-200',
    tip:   'Updates/prefixo/dia abaixo da mediana do universo BR.',
  },
  inquieto: {
    label: 'Inquieto',
    color: 'bg-aviso-100 text-aviso-800 border-aviso-200',
    tip:   'Updates/prefixo/dia entre a mediana e a média do universo BR.',
  },
  barulhento: {
    label: 'Barulhento',
    color: 'bg-alerta-100 text-alerta-800 border-alerta-200',
    tip:   'Updates/prefixo/dia acima da média, até 100× a mediana do universo BR.',
  },
  critico: {
    label: 'Crítico',
    color: 'bg-perigo-100 text-perigo-800 border-perigo-200',
    tip:   'Updates/prefixo/dia acima de 100× a mediana do universo BR.',
  },
}

interface Props {
  category: NoiseCategory
  size?:    'sm' | 'xs'
}

export function NoiseCategoryBadge({ category, size = 'sm' }: Props) {
  const cfg = CONFIG[category]
  const px  = size === 'xs' ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-0.5 text-xs'
  return (
    <span
      title={cfg.tip}
      className={`inline-flex items-center rounded border font-medium whitespace-nowrap ${px} ${cfg.color}`}
    >
      {cfg.label}
    </span>
  )
}
