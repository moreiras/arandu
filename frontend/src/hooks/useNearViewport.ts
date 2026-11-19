// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useCallback, useEffect, useState } from 'react'

/**
 * `[ref, perto]`: `perto` vira `true` assim que o elemento ligado a `ref` chega perto da área visível (`margem` px antes de
 * entrar) e continua `true` depois. Serve para só buscar dados pesados quando o visitante está prestes a ver a seção. O `ref` é
 * uma função (o elemento pode aparecer depois do primeiro render, como numa página que espera dados). Sem `IntersectionObserver`
 * (testes, navegadores antigos) `perto` é `true` de imediato, para o dado nunca deixar de carregar.
 */
export function useNearViewport(margem = 800): [(el: Element | null) => void, boolean] {
  const [el, setEl] = useState<Element | null>(null)
  const [perto, setPerto] = useState(typeof IntersectionObserver === 'undefined')
  const ref = useCallback((e: Element | null) => setEl(e), [])
  useEffect(() => {
    if (perto || !el) return
    const obs = new IntersectionObserver((entradas) => {
      if (entradas.some((e) => e.isIntersecting)) { setPerto(true); obs.disconnect() }
    }, { rootMargin: `${margem}px 0px` })
    obs.observe(el)
    return () => obs.disconnect()
  }, [perto, el, margem])
  return [ref, perto]
}
