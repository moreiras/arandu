// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useEffect, useRef } from 'react'

/**
 * Diálogo das entidades agregadas de um marcador do mapa (PT-22 / localizador 5.3): `role="dialog"` com nome, foco no botão de fechar ao abrir, Escape e clique no fundo
 * fecham, e o foco volta ao elemento que o tinha antes. O conteúdo (`html`) é o balão montado em `balloes.ts`, que escapa os campos de terceiros.
 */
export function ModalEntidades({ titulo, html, aoFechar }: { titulo: string; html: string; aoFechar: () => void }) {
  const fechar = useRef<HTMLButtonElement>(null)
  // `aoFechar` costuma ser uma função nova a cada renderização: o efeito guarda a mais recente e só roda ao abrir e ao fechar o diálogo
  const aoFecharAtual = useRef(aoFechar)
  aoFecharAtual.current = aoFechar
  useEffect(() => {
    const anterior = document.activeElement as HTMLElement | null
    fechar.current?.focus()
    const aoTeclar = (e: KeyboardEvent) => { if (e.key === 'Escape') aoFecharAtual.current() }
    document.addEventListener('keydown', aoTeclar)
    return () => { document.removeEventListener('keydown', aoTeclar); anterior?.focus?.() }
  }, [])
  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/40" onClick={aoFechar} data-testid="modal-entidades">
      <div role="dialog" aria-modal="true" aria-labelledby="modal-entidades-titulo" className="bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-80 flex flex-col"
        style={{ maxHeight: '70%' }} onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-700 flex-shrink-0">
          <h2 id="modal-entidades-titulo" className="text-xs font-semibold text-white leading-snug">{titulo}</h2>
          <button ref={fechar} type="button" aria-label="Fechar" className="ml-3 min-h-6 min-w-6 flex-shrink-0 text-gray-300 hover:text-white text-base leading-none" onClick={aoFechar}><span aria-hidden="true">✕</span></button>
        </div>
        <div className="overflow-y-auto p-3 text-xs text-gray-200 flex-1" dangerouslySetInnerHTML={{ __html: html }} />
      </div>
    </div>
  )
}
