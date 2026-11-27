// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useEffect, useRef, type ReactNode } from 'react'

const FOCAVEIS = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

/**
 * Diálogo modal acessível (WCAG 2.2 AA; NBR 17225): `role="dialog"` com `aria-modal`, nome por `aria-labelledby`, foco inicial dentro,
 * foco preso enquanto aberto, Esc fecha e o foco volta ao elemento que o abriu. Clicar no fundo também fecha.
 * O título do diálogo é o elemento com o id dado em `idTitulo`.
 */
export function ModalAcessivel({ idTitulo, onClose, children, className = '' }: { idTitulo: string; onClose: () => void; children: ReactNode; className?: string }) {
  const painel = useRef<HTMLDivElement>(null)
  const aoFechar = useRef(onClose)
  aoFechar.current = onClose

  useEffect(() => {
    const origem = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const el = painel.current
    const focaveis = () => Array.from(el?.querySelectorAll<HTMLElement>(FOCAVEIS) ?? [])
    ;(focaveis()[0] ?? el)?.focus()
    const tecla = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.stopPropagation(); aoFechar.current(); return }
      if (e.key !== 'Tab' || !el) return
      const lista = focaveis()
      if (lista.length === 0) { e.preventDefault(); el.focus(); return }
      const primeiro = lista[0]
      const ultimo = lista[lista.length - 1]
      const ativo = document.activeElement
      if (e.shiftKey && (ativo === primeiro || ativo === el || !el.contains(ativo))) { e.preventDefault(); ultimo.focus() }
      else if (!e.shiftKey && (ativo === ultimo || !el.contains(ativo))) { e.preventDefault(); primeiro.focus() }
    }
    document.addEventListener('keydown', tecla)
    return () => {
      document.removeEventListener('keydown', tecla)
      if (origem && origem.isConnected && origem !== document.body) origem.focus()
    }
  }, [])

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" onClick={() => onClose()}>
      <div ref={painel} role="dialog" aria-modal="true" aria-labelledby={idTitulo} tabIndex={-1}
        className={`bg-white rounded-xl shadow-2xl p-5 flex gap-5 max-h-[90vh] ${className}`} onClick={(e) => e.stopPropagation()}>
        {children}
      </div>
    </div>
  )
}
