// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { Selo } from '../components/entidade/proveniencia'

/**
 * Paleta dos selos e das caixas de destaque dos números (PT-30), num lugar só. A cor indica a natureza do dado (fato, inferido,
 * estimado) e nunca um juízo: nada de verde "bom" nem vermelho "ruim". Cada selo tem uma escala (a mesma de `tailwind.config.ts`):
 * - `simbolo` (700): cor da forma do selo, com 3:1 ou mais sobre qualquer fundo abaixo (WCAG 1.4.11);
 * - `faixa` (600): faixa lateral da caixa;
 * - `tinta` (50): fundo bem claro da caixa.
 * As caixas alternam, pela posição na grade (CSS `:nth-child`, sem estado), entre a tinta do selo, o branco e um cinza claro, para a
 * grade não ficar toda da mesma cor. Os textos das caixas são sempre cinza 900 (valor) e cinza 600 (rótulo e referência).
 * As classes ficam escritas por extenso porque o Tailwind só gera o que encontra no código; `paletaSelos.test.ts` confere o contraste
 * de cada par e que as classes e os hexadecimais descrevem as mesmas cores.
 */
export interface AspectoSelo {
  forma: 'circulo' | 'triangulo' | 'losango'
  /** Passo da escala do papel (50 a 900) de cada uso. */
  passos: { simbolo: 700; faixa: 600; tinta: 50 }
  /** Hexadecimal correspondente a cada passo, para o teste de contraste. */
  hex: { simbolo: string; faixa: string; tinta: string }
  classes: { simbolo: string; faixa: string; fundoCiclo: string }
}

/** Uma forma por selo: o selo não depende só da cor (WCAG 1.4.1). */
export const PALETA_SELOS: Record<Selo, AspectoSelo> = {
  fato: {
    forma: 'circulo',
    passos: { simbolo: 700, faixa: 600, tinta: 50 },
    hex: { simbolo: '#047857', faixa: '#059669', tinta: '#ecfdf5' },
    classes: { simbolo: 'text-fato-700', faixa: 'border-l-fato-600', fundoCiclo: '[&:nth-child(3n+1)]:bg-fato-50 [&:nth-child(3n+2)]:bg-white [&:nth-child(3n)]:bg-gray-100' },
  },
  inferido: {
    forma: 'losango',
    passos: { simbolo: 700, faixa: 600, tinta: 50 },
    hex: { simbolo: '#b45309', faixa: '#d97706', tinta: '#fffbeb' },
    classes: { simbolo: 'text-inferido-700', faixa: 'border-l-inferido-600', fundoCiclo: '[&:nth-child(3n+1)]:bg-inferido-50 [&:nth-child(3n+2)]:bg-white [&:nth-child(3n)]:bg-gray-100' },
  },
  estimado: {
    forma: 'triangulo',
    passos: { simbolo: 700, faixa: 600, tinta: 50 },
    hex: { simbolo: '#6d28d9', faixa: '#7c3aed', tinta: '#f5f3ff' },
    classes: { simbolo: 'text-estimado-700', faixa: 'border-l-estimado-600', fundoCiclo: '[&:nth-child(3n+1)]:bg-estimado-50 [&:nth-child(3n+2)]:bg-white [&:nth-child(3n)]:bg-gray-100' },
  },
}

/** Aspecto de um selo desconhecido (vocabulário que crescer antes da paleta): neutro, em círculo. */
export const ASPECTO_NEUTRO: AspectoSelo = {
  forma: 'circulo',
  passos: { simbolo: 700, faixa: 600, tinta: 50 },
  hex: { simbolo: '#374151', faixa: '#4b5563', tinta: '#f9fafb' },
  classes: { simbolo: 'text-gray-700', faixa: 'border-l-gray-600', fundoCiclo: 'bg-white' },
}

/** Fundos neutros do ciclo e cores dos textos das caixas (usados pelo teste de contraste). */
export const FUNDOS_NEUTROS = { branco: '#ffffff', cinza: '#f3f4f6' } as const
export const TEXTOS_CAIXA = { valor: '#111827', rotulo: '#4b5563', referencia: '#4b5563' } as const

export const aspectoDoSelo = (selo: Selo): AspectoSelo => PALETA_SELOS[selo] ?? ASPECTO_NEUTRO
