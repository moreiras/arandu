// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useEffect, type RefObject } from 'react'
import { CONSULTA_CELULAR, rotularTabelas } from '../../lib/tabelasResponsivas'

/** Rotula as tabelas do conteúdo para o modo cartão (só no celular), inclusive as que aparecem depois (páginas carregadas sob demanda). */
export function useTabelasResponsivas(raiz: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = raiz.current
    if (!el || typeof window.matchMedia !== 'function') return
    const mq = window.matchMedia(CONSULTA_CELULAR)
    let quadro = 0
    const rodar = () => { quadro = 0; if (mq.matches) rotularTabelas(el) }
    const agendar = () => { if (!quadro) quadro = window.requestAnimationFrame(rodar) }
    const obs = new MutationObserver(agendar)
    obs.observe(el, { childList: true, subtree: true })
    mq.addEventListener('change', agendar)
    agendar()
    return () => { obs.disconnect(); mq.removeEventListener('change', agendar); if (quadro) window.cancelAnimationFrame(quadro) }
  }, [raiz])
}
