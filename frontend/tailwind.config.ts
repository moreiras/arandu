// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { Config } from 'tailwindcss'
import colors from 'tailwindcss/colors'

/**
 * Sistema visual: as cores do site são **semânticas**. Nenhuma página usa o nome de uma cor da paleta do Tailwind
 * (blue, red…); usa o papel dela. As escalas abaixo reaproveitam as do Tailwind para o visual não mudar na troca; mudar um papel
 * de cor é mudar uma linha aqui. Um teste (`src/tokens.test.ts`) falha se uma família fora dos papéis voltar a aparecer.
 *
 * Papéis:
 * - primario: ação, link e foco · v4 / v6: famílias de endereço IPv4 e IPv6 · mercado / tecnico: lentes do site
 * - ok / aviso / perigo / alerta: estados · fato / inferido / estimado: selos de honestidade semântica
 * A `v6` coincide com o roxo dos mapas de IPv6; as escalas de mapa (daltonismo) estão em `src/components/maps/mapTheme.ts`
 * e em `src/lib/escalasMapa.ts` (escalas novas, seguras para daltonismo).
 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primario: colors.blue,
        v4: colors.blue,
        v6: colors.purple,
        mercado: colors.emerald,
        tecnico: colors.sky,
        ok: colors.green,
        aviso: colors.amber,
        perigo: colors.red,
        alerta: colors.orange,
        fato: colors.emerald,
        inferido: colors.amber,
        estimado: colors.violet,
        ixbr: colors.yellow,          // colunas do IX.br na matriz de CDNs
      },
      // Quatro níveis de título e piso de 12 px para qualquer texto (nada de 9 a 11 px).
      fontSize: {
        // Entrelinha de 1,5 nos tamanhos de texto corrido (NBR 17225 5.12.1). O padrão do Tailwind dá 1,33 e 1,43.
        xs: ['0.75rem', { lineHeight: '1.125rem' }],
        sm: ['0.875rem', { lineHeight: '1.3125rem' }],
        // Título de página (T5): 24 px, o tamanho que 29 das 31 páginas já usavam com `text-2xl font-bold`.
        'titulo-1': ['1.5rem', { lineHeight: '2rem', fontWeight: '700' }],
        'titulo-2': ['1.25rem', { lineHeight: '1.75rem', fontWeight: '600' }],
        'titulo-3': ['1rem', { lineHeight: '1.5rem', fontWeight: '600' }],
        'titulo-4': ['0.875rem', { lineHeight: '1.25rem', fontWeight: '600' }],
      },
    },
  },
  plugins: [],
} satisfies Config
