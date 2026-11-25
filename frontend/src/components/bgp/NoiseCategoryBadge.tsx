import type { NoiseCategory } from '../../types/bgpStability'

/**
 * Faixas de updates por prefixo por dia relativas à mediana e à média do conjunto de ASes BR da semana (método do projeto, INFERIDO, não critério de
 * norma ou de operador). Paleta neutra em escala sequencial: a cor mais escura diz só "faixa mais alta", nunca "bom" ou "ruim" (política editorial, BGP-E9).
 */
const CONFIG: Record<NoiseCategory, { label: string; color: string; tip: string }> = {
  estavel: {
    label: 'Abaixo da mediana',
    color: 'bg-gray-50 text-gray-700 border-gray-200',
    tip:   'Updates por prefixo por dia abaixo da mediana do conjunto de ASes BR.',
  },
  inquieto: {
    label: 'Da mediana à média',
    color: 'bg-gray-100 text-gray-800 border-gray-300',
    tip:   'Updates por prefixo por dia entre a mediana e a média do conjunto de ASes BR.',
  },
  barulhento: {
    label: 'Acima da média',
    color: 'bg-gray-200 text-gray-900 border-gray-400',
    tip:   'Updates por prefixo por dia acima da média, até 100 vezes a mediana do conjunto de ASes BR.',
  },
  critico: {
    label: 'Acima de 100× a mediana',
    color: 'bg-gray-300 text-gray-900 border-gray-500',
    tip:   'Updates por prefixo por dia acima de 100 vezes a mediana do conjunto de ASes BR.',
  },
}

const fmt = (v: number) => (v < 1 ? v.toFixed(2) : v < 10 ? v.toFixed(1) : v.toFixed(0)).replace('.', ',')

/** Faixa em números (updates por prefixo por dia) de cada categoria, dada a mediana e a média do conjunto; sem as estatísticas, só a relação com a mediana. */
export function faixaNumerica(category: NoiseCategory, limites?: { median: number; mean: number } | null): string {
  if (!limites) return { estavel: '< mediana', inquieto: 'mediana a média', barulhento: 'média a 100× a mediana', critico: '> 100× a mediana' }[category]
  const { median: md, mean } = limites
  return {
    estavel: `< ${fmt(md)}`,
    inquieto: `${fmt(md)} a ${fmt(mean)}`,
    barulhento: `${fmt(mean)} a ${fmt(md * 100)}`,
    critico: `> ${fmt(md * 100)}`,
  }[category]
}

export const ROTULO_CATEGORIA: Record<NoiseCategory, string> = {
  estavel: CONFIG.estavel.label, inquieto: CONFIG.inquieto.label, barulhento: CONFIG.barulhento.label, critico: CONFIG.critico.label,
}

interface Props {
  category: NoiseCategory
  size?:    'sm' | 'xs'
  /** Mediana e média do conjunto: com elas o rótulo traz a faixa em números. */
  limites?: { median: number; mean: number } | null
}

export function NoiseCategoryBadge({ category, size = 'sm', limites }: Props) {
  const cfg = CONFIG[category]
  const px  = size === 'xs' ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-0.5 text-xs'
  const faixa = limites ? faixaNumerica(category, limites) : null
  return (
    <span
      title={`${cfg.tip} Faixa adotada pelo projeto (inferida), não um critério de norma.`}
      className={`inline-flex items-center rounded border font-medium whitespace-nowrap ${px} ${cfg.color}`}
    >
      {cfg.label}{faixa ? ` (${faixa})` : ''}
    </span>
  )
}
