import type { Classification, Severity } from '../../types/bgpStability'

/**
 * Padrões observados nos updates de um AS. O rótulo descreve o que se vê no dado (anúncio e retirada repetidos, atributos que mudam, mais-específicos),
 * sem apontar causa nem intenção: a causa não é observável neste dado (política editorial, BGP-E9). Paleta neutra.
 */
const CONFIG: Record<Classification, { label: string; tip: string }> = {
  chronic_flapper: {
    label: 'Anúncio e retirada repetidos (padrão observado)',
    tip:   'O mesmo prefixo é anunciado e retirado repetidamente ao longo dos dias, com tempo curto entre as mudanças. A causa não é observável neste dado.',
  },
  burst_event: {
    label: 'Updates concentrados num curto intervalo',
    tip:   'Concentração alta de updates num curto intervalo, seguida de calma. A causa não é observável neste dado.',
  },
  attribute_oscillator: {
    label: 'Atributos alterados com frequência',
    tip:   'O prefixo permanece anunciado, mas atributos (MED, communities, AS_PATH) mudam com frequência. A causa não é observável neste dado.',
  },
  more_specific_injection: {
    label: 'Mais-específicos anunciados repetidamente',
    tip:   'Anúncio repetido de prefixos mais específicos (ex.: /25 a /30). A causa não é observável neste dado.',
  },
  noisy: {
    label: 'Volume alto de updates',
    tip:   'Volume alto de updates sem padrão dominante identificado.',
  },
}

/** Pontos em tons de cinza, do mais escuro (severidade calculada maior) ao mais claro: só ordenam, sem verde nem vermelho. */
const SEVERITY_DOT: Record<Severity, string> = {
  critical: 'bg-gray-800',
  high:     'bg-gray-600',
  medium:   'bg-gray-400',
  low:      'bg-gray-300',
}
const SEVERITY_LABEL: Record<Severity, string> = { critical: 'severidade calculada: crítica', high: 'severidade calculada: alta', medium: 'severidade calculada: média', low: 'severidade calculada: baixa' }

interface Props {
  classification: Classification
  severity?:      Severity
  size?:          'sm' | 'xs'
}

export function ClassificationBadge({ classification, severity, size = 'sm' }: Props) {
  const cfg   = CONFIG[classification]
  const px    = size === 'xs' ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-0.5 text-xs'
  return (
    <span
      title={severity ? `${cfg.tip} (${SEVERITY_LABEL[severity]})` : cfg.tip}
      className={`inline-flex items-center gap-1 rounded border border-gray-200 bg-gray-100 font-medium text-gray-800 whitespace-nowrap ${px}`}
    >
      {severity && (
        <span aria-hidden="true" className={`inline-block w-1.5 h-1.5 rounded-full flex-shrink-0 ${SEVERITY_DOT[severity]}`} />
      )}
      {cfg.label}
    </span>
  )
}
