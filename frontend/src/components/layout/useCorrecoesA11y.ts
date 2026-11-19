// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurapé.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useEffect } from 'react'

const FOCAVEIS = 'a[href], button, input, select, textarea, summary, [tabindex]'

/**
 * Correções de acessibilidade que a biblioteca de gráficos e as tabelas largas não fazem sozinhas (auditoria com axe-core):
 *  - as partes decorativas do recharts (símbolos do scatter e setores da pizza) saem da árvore de acessibilidade: o gráfico já tem rótulo e tabela de dados (`aria-hidden`);
 *  - caixa que rola na horizontal e não tem nada focável dentro recebe `tabindex=0`, para quem usa só o teclado conseguir rolar a tabela.
 * Roda no máximo uma vez por quadro de animação e só mexe no que ainda não foi corrigido.
 */
export function corrigirA11y(raiz: ParentNode = document): void {
  raiz.querySelectorAll('.recharts-scatter-symbol[role="img"], .recharts-sector, .recharts-pie-sector path').forEach((e) => { if (e.getAttribute('aria-hidden') !== 'true') e.setAttribute('aria-hidden', 'true') })
  raiz.querySelectorAll<HTMLElement>('.overflow-x-auto').forEach((e) => {
    if (e.hasAttribute('tabindex') || e.scrollWidth <= e.clientWidth + 1 || e.querySelector(FOCAVEIS)) return
    e.setAttribute('tabindex', '0')
  })
}

export function useCorrecoesA11y(): void {
  useEffect(() => {
    let quadro = 0
    const agendar = () => { if (!quadro) quadro = requestAnimationFrame(() => { quadro = 0; corrigirA11y() }) }
    const obs = new MutationObserver(agendar)
    obs.observe(document.body, { childList: true, subtree: true })
    agendar()
    return () => { obs.disconnect(); if (quadro) cancelAnimationFrame(quadro) }
  }, [])
}
