// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { caminhoDoPrefixo, ehIp, ehPrefixo } from '../../lib/prefixo'
import { lembrarBusca, lerRecentes, limparRecentes, type Recente } from '../../lib/buscaRecentes'
import { fetchBusca, type GrupoBusca, type ItemBusca } from '../../services/api'
import { useActiveDate } from '../../hooks/useSnapshot'

/** Item da lista navegável por teclado (acerto do servidor ou busca recente). */
interface Linha { id: string; titulo: string; detalhe: string; url: string; selo?: string | null }

const MIN = 2
const ESPERA_MS = 150

/**
 * Busca universal: AS, operadora, grupo, município, UF, PTT, CDN, datacenter, prefixo e página, agrupados por tipo
 * (`GET /api/v1/busca`). Sem texto, mostra as últimas buscas (só no navegador). Teclado: ↑ ↓ percorrem, Enter abre, Esc fecha, `/` foca.
 * No celular a lista ocupa a tela abaixo do cabeçalho. `grande` (home) é a versão de destaque: campo maior, lista logo abaixo dele e `exemplos` clicáveis. IP e prefixo vão direto à página do prefixo, sem consultar o servidor.
 */
export function SearchBar({ grande = false, exemplos = [] }: { grande?: boolean; exemplos?: string[] }) {
  const [consulta, setConsulta] = useState('')
  const [grupos, setGrupos] = useState<GrupoBusca[]>([])
  const [recentes, setRecentes] = useState<Recente[]>([])
  const [aberta, setAberta] = useState(false)
  const [carregando, setCarregando] = useState(false)
  const [semResultado, setSemResultado] = useState(false)
  const [ativa, setAtiva] = useState(-1)
  const date = useActiveDate()
  const navigate = useNavigate()
  const raiz = useRef<HTMLDivElement>(null)
  const campo = useRef<HTMLInputElement>(null)
  const idLista = useId()
  const seq = useRef(0)

  const q = consulta.trim()
  const linhas: Linha[] = useMemo(() => {
    if (q.length < MIN) return recentes.map((r) => ({ id: `r:${r.url}`, titulo: r.titulo, detalhe: r.detalhe, url: r.url }))
    return grupos.flatMap((g) => g.itens.map((i: ItemBusca) => ({ id: `${g.tipo}:${i.url}`, titulo: i.titulo, detalhe: i.detalhe, url: i.url, selo: i.selo })))
  }, [q, grupos, recentes])

  useEffect(() => {
    if (q.length < MIN) { setGrupos([]); setSemResultado(false); setCarregando(false); return }
    const minha = ++seq.current
    const t = setTimeout(async () => {
      setCarregando(true)
      try {
        const r = await fetchBusca(q, { limite: 4, date: date ?? undefined })
        if (minha !== seq.current) return
        setGrupos(r.grupos); setSemResultado(r.grupos.length === 0); setAtiva(r.grupos.length ? 0 : -1); setAberta(true)
      } catch {
        if (minha === seq.current) { setGrupos([]); setSemResultado(false) }
      } finally {
        if (minha === seq.current) setCarregando(false)
      }
    }, ESPERA_MS)
    return () => clearTimeout(t)
  }, [q, date])

  useEffect(() => {
    function fora(e: MouseEvent) { if (raiz.current && !raiz.current.contains(e.target as Node)) setAberta(false) }
    function atalho(e: KeyboardEvent) {
      const alvo = e.target as HTMLElement | null
      const digitando = alvo && (alvo.tagName === 'INPUT' || alvo.tagName === 'TEXTAREA' || alvo.isContentEditable)
      if (e.key === '/' && !digitando && !e.metaKey && !e.ctrlKey) {
        const visivel = campo.current && campo.current.offsetParent !== null
        if (visivel) { e.preventDefault(); campo.current!.focus() }
      }
    }
    document.addEventListener('mousedown', fora)
    document.addEventListener('keydown', atalho)
    return () => { document.removeEventListener('mousedown', fora); document.removeEventListener('keydown', atalho) }
  }, [])

  const abrir = useCallback((l: Linha | { titulo: string; detalhe: string; url: string }) => {
    setRecentes(lembrarBusca({ titulo: l.titulo, detalhe: l.detalhe, url: l.url }))
    navigate(l.url)
    setConsulta(''); setAberta(false); setGrupos([]); campo.current?.blur()
  }, [navigate])

  function aoFocar() {
    setRecentes(lerRecentes())
    setAberta(true)
  }

  function aoTeclar(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Escape') { setAberta(false); campo.current?.blur(); return }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      if (!linhas.length) return
      e.preventDefault(); setAberta(true)
      setAtiva((a) => (e.key === 'ArrowDown' ? (a + 1) % linhas.length : (a <= 0 ? linhas.length - 1 : a - 1)))
      return
    }
    if (e.key !== 'Enter') return
    if (ehPrefixo(q) || ehIp(q)) { abrir({ titulo: q, detalhe: 'prefixo', url: caminhoDoPrefixo(q) }); return }
    const escolhida = linhas[ativa] ?? (q.length >= MIN ? linhas[0] : undefined)
    if (escolhida) abrir(escolhida)
  }

  const mostrarLista = aberta && (linhas.length > 0 || semResultado || (q.length < MIN && recentes.length > 0))
  const idOpcao = (i: number) => `${idLista}-o${i}`
  let n = -1

  return (
    <div ref={raiz} className={`relative w-full ${grande ? '' : 'sm:w-auto'}`}>
      <div className={`flex items-center gap-1 border border-gray-200 rounded-lg bg-white focus-within:border-primario-500 focus-within:ring-1 focus-within:ring-primario-200 ${grande ? 'px-3 py-2.5 gap-2 shadow-sm' : 'px-2 py-1'}`}>
        <svg aria-hidden="true" className={`${grande ? 'w-5 h-5' : 'w-3.5 h-3.5'} text-gray-400 flex-shrink-0`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          ref={campo}
          type="search"
          role="combobox"
          aria-label="Buscar no site"
          aria-expanded={mostrarLista}
          aria-controls={idLista}
          aria-autocomplete="list"
          aria-activedescendant={mostrarLista && ativa >= 0 ? idOpcao(ativa) : undefined}
          autoComplete="off"
          value={consulta}
          onChange={(e) => { setConsulta(e.target.value); setAberta(true); setAtiva(-1) }}
          onKeyDown={aoTeclar}
          onFocus={aoFocar}
          placeholder="Buscar AS, operadora, município, prefixo…"
          className={`bg-transparent outline-none flex-1 min-w-0 placeholder-gray-400 [&::-webkit-search-cancel-button]:hidden ${grande ? 'text-base sm:text-lg' : 'text-sm sm:w-56'}`}
        />
        {carregando
          ? <div role="status" aria-label="Buscando" className="w-3 h-3 border border-gray-300 border-t-primario-500 rounded-full animate-spin" />
          : <kbd aria-hidden="true" className={`${grande ? 'hidden' : 'hidden sm:inline'} text-xs text-gray-400 border border-gray-200 rounded px-1`}>/</kbd>}
      </div>

      {grande && exemplos.length > 0 && (
        <p className="mt-2 text-sm text-gray-500 flex flex-wrap gap-x-2 gap-y-1 items-baseline">
          <span>Por exemplo:</span>
          {exemplos.map((e) => (
            <button key={e} type="button" className="text-primario-700 hover:underline" onClick={() => { setConsulta(e); setAberta(true); campo.current?.focus() }}>{e}</button>
          ))}
        </p>
      )}

      {mostrarLista && (
        <div
          id={idLista}
          role="listbox"
          aria-label={q.length < MIN ? 'Últimas buscas' : 'Resultados da busca'}
          className={grande
            ? 'absolute left-0 right-0 top-[3.5rem] bg-white z-50 overflow-y-auto max-h-[60vh] rounded-lg border border-gray-200 shadow-lg'
            : 'fixed inset-x-0 top-12 bottom-0 bg-white z-50 overflow-y-auto border-t border-gray-200 sm:absolute sm:inset-x-auto sm:top-full sm:bottom-auto sm:left-0 sm:mt-1 sm:w-[26rem] sm:max-h-[70vh] sm:rounded-lg sm:border sm:shadow-lg'}
        >
          {q.length < MIN && (
            <div className="flex items-center justify-between px-3 pt-2 pb-1 text-xs text-gray-500">
              <span>Últimas buscas</span>
              <button type="button" className="text-primario-700 hover:underline" onMouseDown={(e) => e.preventDefault()} onClick={() => { limparRecentes(); setRecentes([]) }}>limpar</button>
            </div>
          )}
          {q.length < MIN && recentes.map((r) => { n += 1; const i = n; return (
            <Opcao key={r.url} id={idOpcao(i)} ativa={ativa === i} titulo={r.titulo} detalhe={r.detalhe} onEscolher={() => abrir(r)} onPassar={() => setAtiva(i)} />
          ) })}
          {q.length >= MIN && grupos.map((g) => (
            <div key={g.tipo} role="group" aria-label={g.rotulo}>
              <div className="px-3 pt-2 pb-1 text-xs font-medium text-gray-500 uppercase tracking-wide">{g.rotulo}</div>
              {g.itens.map((it) => { n += 1; const i = n; return (
                <Opcao key={it.url} id={idOpcao(i)} ativa={ativa === i} titulo={it.titulo} detalhe={it.detalhe} selo={it.selo} mono={g.tipo === 'asn'}
                       onEscolher={() => abrir({ titulo: it.titulo, detalhe: it.detalhe, url: it.url })} onPassar={() => setAtiva(i)} />
              ) })}
              {g.total > g.itens.length && <div className="px-3 pb-1 text-xs text-gray-400">e mais {g.total - g.itens.length} em {g.rotulo.toLowerCase()}; refine a busca</div>}
            </div>
          ))}
          {q.length >= MIN && semResultado && !carregando && (
            <p className="px-3 py-3 text-sm text-gray-500">Nada encontrado para “{q}”. Tente o nome, o número do AS, o CNPJ ou o código IBGE.</p>
          )}
        </div>
      )}
    </div>
  )
}

function Opcao({ id, ativa, titulo, detalhe, selo, mono, onEscolher, onPassar }: {
  id: string; ativa: boolean; titulo: string; detalhe: string; selo?: string | null; mono?: boolean; onEscolher: () => void; onPassar: () => void
}) {
  return (
    <div
      id={id}
      role="option"
      aria-selected={ativa}
      tabIndex={-1}
      onMouseDown={(e) => e.preventDefault()}
      onClick={onEscolher}
      onMouseMove={onPassar}
      className={`px-3 py-2 cursor-pointer flex items-baseline gap-2 text-sm ${ativa ? 'bg-primario-50' : ''}`}
    >
      <span className={`flex-shrink-0 text-primario-700 ${mono ? 'font-mono' : 'font-medium'}`}>{titulo}</span>
      <span className="text-gray-600 truncate flex-1 min-w-0">{detalhe}</span>
      {selo && <span className="text-xs bg-gray-100 text-gray-600 rounded px-1 flex-shrink-0">{selo}</span>}
    </div>
  )
}
