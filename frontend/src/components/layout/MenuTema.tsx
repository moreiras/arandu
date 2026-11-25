// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useLocation } from 'react-router-dom'
import { Link } from './LinkDatado'
import { GRUPOS_MENU, ITENS_AVULSOS, grupoAtivo, itemAtivo, type GrupoMenu, type ItemMenu } from './menu'

const BOTAO = 'text-xs sm:text-sm px-2 sm:px-3 py-1 sm:py-1.5 rounded transition-colors whitespace-nowrap flex items-center gap-1'
const BOTAO_ATIVO = 'bg-primario-100 text-primario-700 font-medium'
const BOTAO_INATIVO = 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'

/**
 * Grupos temáticos do menu. Um grupo aberto por vez; o painel vai para o `body` (a barra rola na horizontal e cortaria um painel
 * absoluto). Teclado: Enter/Espaço/↓ abre e foca o 1º item, ↑/↓ percorrem, Esc fecha e devolve o foco ao botão. Hover é CSS puro.
 */
export function MenuTema({ grupos = GRUPOS_MENU, avulsos = ITENS_AVULSOS }: { grupos?: GrupoMenu[]; avulsos?: ItemMenu[] }) {
  const { pathname, search } = useLocation()
  const [aberto, setAberto] = useState<string | null>(null)
  const [pos, setPos] = useState({ top: 0, left: 0 })
  const botoes = useRef<Record<string, HTMLButtonElement | null>>({})
  const painel = useRef<HTMLDivElement>(null)
  const focarAoAbrir = useRef(false)

  useEffect(() => { setAberto(null) }, [pathname, search])

  // O foco vai para o 1º item só depois que o painel existe no DOM (o portal monta no commit, não antes do próximo frame).
  useEffect(() => {
    if (aberto && focarAoAbrir.current) painel.current?.querySelector<HTMLElement>('a')?.focus()
    focarAoAbrir.current = false
  }, [aberto])

  useEffect(() => {
    if (!aberto) return
    const fora = (e: MouseEvent) => {
      const alvo = e.target as Node
      if (botoes.current[aberto]?.contains(alvo) || painel.current?.contains(alvo)) return
      setAberto(null)
    }
    document.addEventListener('mousedown', fora)
    return () => document.removeEventListener('mousedown', fora)
  }, [aberto])

  const abrir = (id: string, focarPrimeiro = false) => {
    const r = botoes.current[id]?.getBoundingClientRect()
    if (r) setPos({ top: r.bottom, left: r.left })
    setAberto(id)
    focarAoAbrir.current = focarPrimeiro
  }

  const tecladoBotao = (e: React.KeyboardEvent, id: string) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); abrir(id, true) }
    if (e.key === 'Escape') setAberto(null)
  }

  const tecladoPainel = (e: React.KeyboardEvent) => {
    const links = Array.from(painel.current?.querySelectorAll<HTMLElement>('a') ?? [])
    const i = links.indexOf(document.activeElement as HTMLElement)
    if (e.key === 'ArrowDown') { e.preventDefault(); links[(i + 1) % links.length]?.focus() }
    if (e.key === 'ArrowUp') { e.preventDefault(); links[(i - 1 + links.length) % links.length]?.focus() }
    if (e.key === 'Escape' && aberto) { const b = botoes.current[aberto]; setAberto(null); b?.focus() }
  }

  return (
    <>
      {grupos.map((g) => {
        const ativo = grupoAtivo(g, pathname, search)
        return (
          <div key={g.id} className="relative flex-shrink-0">
            <button
              ref={(el) => { botoes.current[g.id] = el }}
              type="button"
              aria-haspopup="true"
              aria-expanded={aberto === g.id}
              aria-controls={`menu-${g.id}`}
              onClick={() => (aberto === g.id ? setAberto(null) : abrir(g.id))}
              onKeyDown={(e) => tecladoBotao(e, g.id)}
              className={`${BOTAO} ${ativo ? BOTAO_ATIVO : BOTAO_INATIVO}`}
            >
              {g.rotulo}
              <svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
              </svg>
            </button>
            {aberto === g.id && createPortal(
              <div ref={painel} id={`menu-${g.id}`} role="menu" aria-label={g.rotulo} onKeyDown={tecladoPainel}
                style={{ position: 'fixed', top: pos.top, left: pos.left }} className="pt-1 z-50">
                <div className="bg-white border border-gray-200 rounded-lg shadow-lg py-1 w-72 max-w-[calc(100vw-1rem)]">
                  {g.itens.map((i) => {
                    const cls = `block px-3 py-1.5 ${itemAtivo(i, pathname, search) ? BOTAO_ATIVO : BOTAO_INATIVO}`
                    const descId = `desc-${g.id}-${i.to.replace(/\W+/g, '-')}`
                    const conteudo = (
                      <>
                        <span className="block text-sm">{i.rotulo}</span>
                        {i.descricao && <span id={descId} className="block text-xs font-normal text-gray-500">{i.descricao}</span>}
                      </>
                    )
                    // O nome acessível é só o rótulo; a descrição vem por aria-describedby (megamenu com uma linha por item).
                    const comum = { role: 'menuitem', className: cls, 'aria-label': i.rotulo, 'aria-describedby': i.descricao ? descId : undefined }
                    // arquivo estático (sitemap.xml): fora do roteador da SPA
                    return i.externo
                      ? <a key={i.to} href={i.to} {...comum}>{conteudo}</a>
                      : <Link key={i.to} to={i.to} {...comum}>{conteudo}</Link>
                  })}
                </div>
              </div>,
              document.body,
            )}
          </div>
        )
      })}
      {avulsos.map((i) => (
        <Link key={i.to} to={i.to} title={i.descricao} aria-label={i.rotulo} className={`${BOTAO} flex-shrink-0 ${itemAtivo(i, pathname, search) ? BOTAO_ATIVO : BOTAO_INATIVO}`}>{i.rotulo}</Link>
      ))}
    </>
  )
}
