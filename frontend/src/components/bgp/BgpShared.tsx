import { Dica } from '../ui/Dica'

/** Explicação de um termo (a `Dica` acessível do site: hover, foco, toque e Esc). */
export function Tip({ text }: { text: string }) {
  return <Dica texto={text} rotulo="este item" />
}

export type SortDir = 'asc' | 'desc'

export function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <span className="text-gray-300 ml-0.5 select-none">↕</span>
  return <span className="text-primario-600 ml-0.5 select-none">{dir === 'asc' ? '↑' : '↓'}</span>
}
