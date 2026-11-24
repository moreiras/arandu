// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { useLocation } from 'react-router-dom'
import { Link } from './LinkDatado'
import { GRUPOS_MENU, ITENS_AVULSOS, grupoAtivo, itemAtivo, type GrupoMenu, type ItemMenu } from './menu'

/**
 * Gaveta do celular (☰), aberta pelo botão do cabeçalho de uma linha. Traz o login e o seletor de snapshot (`topo`) e os grupos
 * do menu em acordeão (um aberto por vez; começa aberto o grupo da página atual). Esc, o fundo e a navegação a fecham, a rolagem
 * da página fica travada enquanto está aberta e o foco volta ao botão ao fechar. Só aparece abaixo de `sm`.
 */
export function GavetaMenu({ topo, grupos = GRUPOS_MENU, avulsos = ITENS_AVULSOS }: { topo?: ReactNode; grupos?: GrupoMenu[]; avulsos?: ItemMenu[] }) {
  const { pathname, search } = useLocation()
  const [aberta, setAberta] = useState(false)
  const [grupo, setGrupo] = useState<string | null>(null)
  const botao = useRef<HTMLButtonElement>(null)
  const painel = useRef<HTMLDivElement>(null)

  const abrir = () => { setGrupo(grupos.find((g) => grupoAtivo(g, pathname, search))?.id ?? null); setAberta(true) }
  const fechar = () => { setAberta(false); botao.current?.focus() }

  useEffect(() => { setAberta(false) }, [pathname, search])

  useEffect(() => {
    if (!aberta) return
    const anterior = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    painel.current?.querySelector<HTMLElement>('button, a')?.focus()
    const tecla = (e: KeyboardEvent) => { if (e.key === 'Escape') { setAberta(false); botao.current?.focus() } }
    document.addEventListener('keydown', tecla)
    return () => { document.body.style.overflow = anterior; document.removeEventListener('keydown', tecla) }
  }, [aberta])

  return (
    <div className="sm:hidden">
      <button ref={botao} type="button" onClick={abrir} aria-label="Abrir menu" aria-haspopup="dialog" aria-expanded={aberta}
        className="flex h-11 w-11 items-center justify-center rounded text-gray-700 hover:bg-gray-100">
        <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" /></svg>
      </button>
      {aberta && createPortal(
        <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label="Menu">
          <div className="absolute inset-0 bg-black/40" onClick={fechar} aria-hidden="true" />
          <div ref={painel} className="relative flex h-full w-[85vw] max-w-sm flex-col overflow-y-auto bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-gray-100 px-3 py-2">
              <span className="text-sm font-medium text-gray-700">Menu</span>
              <button type="button" onClick={fechar} aria-label="Fechar menu" className="flex h-11 w-11 items-center justify-center rounded text-gray-600 hover:bg-gray-100">
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
              </button>
            </div>
            {topo && <div className="flex flex-wrap items-center gap-3 border-b border-gray-100 px-4 py-3">{topo}</div>}
            <nav aria-label="Menu (gaveta)" className="flex-1 px-2 py-2">
              <Link to="/" className="block min-h-11 rounded px-3 py-2.5 text-sm text-gray-800 hover:bg-gray-100">Início</Link>
              {grupos.map((g) => {
                const aberto = grupo === g.id
                const ativo = grupoAtivo(g, pathname, search)
                return (
                  <div key={g.id}>
                    <button type="button" aria-expanded={aberto} aria-controls={`gaveta-${g.id}`} onClick={() => setGrupo(aberto ? null : g.id)}
                      className={`flex min-h-11 w-full items-center justify-between rounded px-3 py-2.5 text-left text-sm ${ativo ? 'font-medium text-primario-700' : 'text-gray-800'} hover:bg-gray-100`}>
                      {g.rotulo}<span aria-hidden="true" className="text-gray-400">{aberto ? '▾' : '▸'}</span>
                    </button>
                    <ul id={`gaveta-${g.id}`} hidden={!aberto} className="mb-1 ml-3 border-l border-gray-100 pl-2">
                      {g.itens.map((i) => {
                        const cls = `block min-h-11 rounded px-3 py-2.5 text-sm ${itemAtivo(i, pathname, search) ? 'bg-primario-100 font-medium text-primario-700' : 'text-gray-700 hover:bg-gray-100'}`
                        return <li key={i.to}>{i.externo ? <a href={i.to} className={cls}>{i.rotulo}</a> : <Link to={i.to} className={cls}>{i.rotulo}</Link>}</li>
                      })}
                    </ul>
                  </div>
                )
              })}
              {avulsos.map((i) => (
                <Link key={i.to} to={i.to} className={`block min-h-11 rounded px-3 py-2.5 text-sm ${itemAtivo(i, pathname, search) ? 'bg-primario-100 font-medium text-primario-700' : 'text-gray-800 hover:bg-gray-100'}`}>{i.rotulo}</Link>
              ))}
            </nav>
          </div>
        </div>,
        document.body,
      )}
    </div>
  )
}
