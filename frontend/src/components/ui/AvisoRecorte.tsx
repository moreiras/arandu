// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

/** Rótulos dos avisos de recorte (`core/avisos_agregado.py`, D6): só dizem o que está à vista, nada é suprimido nem reordenado. */
export const ROTULO_AVISO: Record<string, string> = { poucos_casos: 'poucos casos', maior_integrante: 'um integrante pesa muito' }
export const TITULO_AVISO: Record<string, string> = {
  poucos_casos: 'Menos de 5 casos neste recorte: a média muda muito com um caso a mais ou a menos. O valor continua à vista.',
  maior_integrante: 'Um integrante pesa 30% ou mais deste recorte: o valor é, em boa parte, o dele. O valor continua à vista.',
}

/** Peso do maior integrante em texto (`peso_top1` vai de 0 a 1). */
export const textoPeso = (peso: number | null | undefined) => (peso == null ? null : `maior: ${(peso * 100).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}%`)

/** Selos neutros dos avisos de um recorte; sem aviso, não desenha nada. */
export function AvisosRecorte({ avisos, className = '' }: { avisos?: string[] | null; className?: string }) {
  if (!avisos?.length) return null
  return (
    <>
      {avisos.map((a) => (
        <span key={a} data-testid={`aviso-${a}`} title={TITULO_AVISO[a] ?? a}
          className={`inline-block rounded border border-gray-300 bg-gray-50 px-1 text-xs leading-tight text-gray-600 ${className}`}>
          {ROTULO_AVISO[a] ?? a}
        </span>
      ))}
    </>
  )
}
