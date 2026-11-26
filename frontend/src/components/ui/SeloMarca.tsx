// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { DESCRICAO_SELO, ROTULO_SELO, type Selo } from '../entidade/proveniencia'

/**
 * Aparência de cada selo (PT-30): cor, forma e sigla. A forma e a sigla garantem que o selo não dependa só da cor (WCAG 1.4.1);
 * o texto de cada selo vem de `proveniencia.ts`, a mesma fonte que a página Sobre usa. Selo novo no vocabulário sem entrada aqui
 * cai no aspecto neutro.
 */
const ASPECTO: Record<Selo, { cor: string; forma: 'circulo' | 'losango' | 'triangulo' }> = {
  fato: { cor: 'bg-fato-50 text-fato-700', forma: 'circulo' },
  inferido: { cor: 'bg-inferido-50 text-inferido-700', forma: 'losango' },
  estimado: { cor: 'bg-estimado-50 text-estimado-700', forma: 'triangulo' },
}
const NEUTRO = { cor: 'bg-gray-100 text-gray-700', forma: 'circulo' as const }

/** Selos do vocabulário, na ordem em que a legenda os lista. */
export const SELOS = Object.keys(ROTULO_SELO) as Selo[]

/** Sigla do selo: a inicial do rótulo ("F" de Fato). */
export const siglaSelo = (selo: Selo) => (ROTULO_SELO[selo] ?? String(selo)).charAt(0).toUpperCase()

function Forma({ forma }: { forma: 'circulo' | 'losango' | 'triangulo' }) {
  return (
    <svg viewBox="0 0 10 10" width="10" height="10" aria-hidden="true" focusable="false" fill="currentColor">
      {forma === 'circulo' && <circle cx="5" cy="5" r="4" />}
      {forma === 'losango' && <polygon points="5,0.5 9.5,5 5,9.5 0.5,5" />}
      {forma === 'triangulo' && <polygon points="5,0.8 9.5,9.2 0.5,9.2" />}
    </svg>
  )
}

/** Selo pequeno: forma, sigla e, para leitor de tela, o nome por extenso (`legivel` mostra o nome também na tela). */
export function SeloMarca({ selo, legivel = false, className = '' }: { selo: Selo; legivel?: boolean; className?: string }) {
  const a = ASPECTO[selo] ?? NEUTRO
  return (
    <span className={`inline-flex items-center gap-1 rounded px-1.5 text-xs font-medium leading-4 ${a.cor} ${className}`} title={DESCRICAO_SELO[selo]} data-selo={selo}>
      <Forma forma={a.forma} />
      {legivel
        ? <span>{ROTULO_SELO[selo]}</span>
        : <><span aria-hidden="true">{siglaSelo(selo)}</span><span className="sr-only">{ROTULO_SELO[selo]}</span></>}
    </span>
  )
}
