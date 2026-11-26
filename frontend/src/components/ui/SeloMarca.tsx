// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { nomeAcessivelSelo, ROTULO_SELO, type Selo } from '../entidade/proveniencia'
import { aspectoDoSelo, type AspectoSelo } from '../../lib/paletaSelos'

/** Selos do vocabulário, na ordem em que a legenda os lista. */
export const SELOS = Object.keys(ROTULO_SELO) as Selo[]

/** Só a forma, sem letra: círculo, losango ou triângulo, na cor do selo (`lib/paletaSelos.ts`). Decorativa: quem a usa dá o nome. */
export function FormaSelo({ selo, tamanho = 12, className = '' }: { selo: Selo; tamanho?: number; className?: string }) {
  const a = aspectoDoSelo(selo)
  return (
    <svg viewBox="0 0 10 10" width={tamanho} height={tamanho} aria-hidden="true" focusable="false" fill="currentColor" className={`flex-shrink-0 ${a.classes.simbolo} ${className}`} data-forma={a.forma}>
      <Contorno forma={a.forma} />
    </svg>
  )
}

function Contorno({ forma }: { forma: AspectoSelo['forma'] }) {
  if (forma === 'losango') return <polygon points="5,0.5 9.5,5 5,9.5 0.5,5" />
  if (forma === 'triangulo') return <polygon points="5,0.8 9.5,9.2 0.5,9.2" />
  return <circle cx="5" cy="5" r="4.2" />
}

/**
 * Selo (PT-30): a forma e a cor, sem letra. Sem `legivel`, é uma imagem com o nome acessível por extenso ("Fato: dado declarado ou
 * medido na fonte"); com `legivel`, o nome aparece ao lado da forma, que então fica oculta para leitor de tela. O selo clicável do
 * cartão, com a dica de fonte e data, é o `SeloDica`.
 */
export function SeloMarca({ selo, legivel = false, className = '' }: { selo: Selo; legivel?: boolean; className?: string }) {
  if (legivel) {
    return (
      <span className={`inline-flex items-center gap-1.5 text-xs font-medium text-gray-800 ${className}`} data-selo={selo}>
        <FormaSelo selo={selo} />
        <span>{ROTULO_SELO[selo]}</span>
      </span>
    )
  }
  const a = aspectoDoSelo(selo)
  return (
    <span role="img" aria-label={nomeAcessivelSelo(selo)} className={`inline-flex flex-shrink-0 items-center ${a.classes.simbolo} ${className}`} data-selo={selo}>
      <FormaSelo selo={selo} />
    </span>
  )
}
