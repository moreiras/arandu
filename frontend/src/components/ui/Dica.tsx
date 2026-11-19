// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

const LARGURA = 288   // 18rem
const MARGEM = 8

/**
 * Dica: explicação curta que abre no hover, no foco do teclado e no toque — o `title` nativo só
 * aparece com mouse. NBR 17225 5.1.8/5.1.9 (WCAG 1.4.13): fica aberta com o mouse em cima dela (atraso curto ao sair do gatilho),
 * fecha com Esc sem mover o ponteiro e com toque fora. O balão vai num portal com posição fixa, para não ser cortado por caixas com
 * rolagem (tabelas), e fica dentro da tela no celular. O estado é local ao componente (não re-renderiza a página).
 *
 * Sem `children` o gatilho é um ⓘ; com `children` o próprio conteúdo é o gatilho (sublinhado pontilhado), para selos e termos.
 * `rotulo` dá o nome acessível do ⓘ ("Sobre: Participantes").
 */
export function Dica({ texto, children, rotulo, className = '' }: { texto: ReactNode; children?: ReactNode; rotulo?: string; className?: string }) {
  const id = useId()
  const gatilho = useRef<HTMLButtonElement>(null)
  const balao = useRef<HTMLSpanElement>(null)
  const fechar = useRef<number>(0)
  const [aberta, setAberta] = useState(false)
  const [fixa, setFixa] = useState(false)          // aberta por toque/clique: só fecha com toque fora ou Esc
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null)

  const abrir = () => { window.clearTimeout(fechar.current); setAberta(true) }
  const agendarFechar = () => { window.clearTimeout(fechar.current); fechar.current = window.setTimeout(() => { if (!fixa) setAberta(false) }, 150) }

  useEffect(() => {
    if (!aberta) return
    const fora = (e: PointerEvent) => {
      const alvo = e.target as Node
      if (!gatilho.current?.contains(alvo) && !balao.current?.contains(alvo)) { setAberta(false); setFixa(false) }
    }
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') { setAberta(false); setFixa(false) } }
    const rolar = () => { if (!fixa) setAberta(false) }
    document.addEventListener('pointerdown', fora)
    document.addEventListener('keydown', esc)
    window.addEventListener('scroll', rolar, true)
    return () => { document.removeEventListener('pointerdown', fora); document.removeEventListener('keydown', esc); window.removeEventListener('scroll', rolar, true) }
  }, [aberta, fixa])
  useEffect(() => () => window.clearTimeout(fechar.current), [])

  // Posição: abaixo do gatilho (acima, se não couber), sem passar das bordas da tela.
  useLayoutEffect(() => {
    if (!aberta || !gatilho.current) { setPos(null); return }
    const r = gatilho.current.getBoundingClientRect()
    const larg = Math.min(LARGURA, window.innerWidth - 2 * MARGEM)
    const left = Math.max(MARGEM, Math.min(r.left, window.innerWidth - larg - MARGEM))
    const altura = balao.current?.offsetHeight ?? 0
    const abaixo = r.bottom + 6
    const top = altura && abaixo + altura > window.innerHeight - MARGEM && r.top - 6 - altura > MARGEM ? r.top - 6 - altura : abaixo
    setPos({ top, left })
  }, [aberta])

  return (
    <span className={`inline-flex items-baseline ${className}`}>
      <button
        ref={gatilho}
        type="button"
        aria-describedby={aberta ? id : undefined}
        aria-label={children ? undefined : `Sobre: ${rotulo ?? 'este item'}`}
        aria-expanded={aberta}
        onMouseEnter={abrir}
        onMouseLeave={agendarFechar}
        onFocus={abrir}
        onBlur={() => { if (!fixa) setAberta(false) }}
        onClick={(e) => { e.stopPropagation(); e.preventDefault(); if (fixa) { setFixa(false); setAberta(false) } else { setFixa(true); abrir() } }}
        className={`dica-gatilho ${children
          ? 'cursor-help border-b border-dotted border-current text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario-500'
          : 'ml-0.5 inline-flex h-6 w-6 cursor-help items-center justify-center rounded-full text-xs leading-none text-gray-500 hover:text-primario-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario-500'}`}
      >
        {children ?? <span aria-hidden="true">ⓘ</span>}
      </button>
      {aberta && typeof document !== 'undefined' && createPortal(
        <span
          ref={balao}
          id={id}
          role="tooltip"
          onMouseEnter={abrir}
          onMouseLeave={agendarFechar}
          style={{ position: 'fixed', top: pos?.top ?? -9999, left: pos?.left ?? -9999, maxWidth: `min(${LARGURA}px, calc(100vw - ${2 * MARGEM}px))` }}
          className="z-[1000] block w-max whitespace-normal rounded bg-gray-900 px-2.5 py-1.5 text-left text-xs font-normal normal-case leading-normal tracking-normal text-white shadow-lg"
        >
          {texto}
        </span>,
        document.body,
      )}
    </span>
  )
}
