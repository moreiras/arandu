import type { Classification, Severity } from '../../types/bgpStability'

const CONFIG: Record<Classification, { label: string; color: string; tip: string }> = {
  chronic_flapper: {
    label: 'Flapper crônico',
    color: 'bg-perigo-100 text-perigo-800 border-perigo-200',
    tip:   'Mesmo prefixo oscila repetidamente (anúncio→retirada→anúncio) ao longo dos dias, com tempo de vida curto entre mudanças.',
  },
  burst_event: {
    label: 'Explosão pontual',
    color: 'bg-aviso-100 text-aviso-800 border-aviso-200',
    tip:   'Concentração alta de updates em um curto intervalo de tempo, seguida de estabilidade. Pode indicar manutenção ou incidente.',
  },
  attribute_oscillator: {
    label: 'Oscilador de atributos',
    color: 'bg-alerta-100 text-alerta-800 border-alerta-200',
    tip:   'Prefixo permanece anunciado mas atributos (MED, communities, AS_PATH) mudam frequentemente. Tipicamente configuração de roteamento instável.',
  },
  more_specific_injection: {
    label: 'Injeção de mais-específicos',
    color: 'bg-v6-100 text-v6-800 border-v6-200',
    tip:   'Anúncio repetido de prefixos mais específicos (ex.: /25–/30). Pode ser mecanismo de mitigação DDoS automatizado mal calibrado.',
  },
  noisy: {
    label: 'Ruidoso',
    color: 'bg-gray-100 text-gray-700 border-gray-200',
    tip:   'Volume alto de updates sem padrão dominante identificado.',
  },
}

const SEVERITY_DOT: Record<Severity, string> = {
  critical: 'bg-perigo-500',
  high:     'bg-alerta-400',
  medium:   'bg-aviso-400',
  low:      'bg-gray-300',
}

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
      title={cfg.tip}
      className={`inline-flex items-center gap-1 rounded border font-medium whitespace-nowrap ${px} ${cfg.color}`}
    >
      {severity && (
        <span className={`inline-block w-1.5 h-1.5 rounded-full flex-shrink-0 ${SEVERITY_DOT[severity]}`} />
      )}
      {cfg.label}
    </span>
  )
}
