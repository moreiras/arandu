import { useEffect, useRef } from 'react'
import { Outlet, NavLink, useSearchParams, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchHealth } from '../../services/api'
import { useAppStore } from '../../store/app'
import { usePageTracker } from '../../auth/usePageTracker'
import { useAuth } from '../../auth/AuthContext'
import { SearchBar } from './SearchBar'
import { SnapshotSelector } from './SnapshotSelector'
import { BudgetChip } from '../BudgetChip'
import { GavetaMenu } from './GavetaMenu'
import { MenuTema } from './MenuTema'
import { useCorrecoesA11y } from './useCorrecoesA11y'
import { tituloDaRota } from './tituloRota'
import { useTabelasResponsivas } from './useTabelasResponsivas'
import { SITE } from '../../lib/site'
import { LeituraConfortavel } from './LeituraConfortavel'

export function AppLayout() {
  usePageTracker()
  useCorrecoesA11y()
  const { user, loading: authLoading } = useAuth()
  const [params] = useSearchParams()
  const location = useLocation()
  const isMapPage = location.pathname === '/mapa'
  const setActiveDate = useAppStore((s) => s.setActiveDate)
  const setLatestSnapshot = useAppStore((s) => s.setLatestSnapshot)
  const latestSnapshot = useAppStore((s) => s.latestSnapshot)

  const { data: health, isError: healthError } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 5 * 60 * 1000,
  })

  // Data resolvida: ?date na URL ou o latest da store (preenchido via /health).
  // Amarramos o gating ao `latestSnapshot` da store — que é exatamente o que
  // useActiveDate lê — para que o conteúdo só renderize quando as páginas puderem
  // disparar requisições JÁ DATADAS (nunca resolvendo "latest" no servidor); assim
  // o snapshot mais recente é cacheável por 7 dias e evitamos um fetch sem data.
  const resolvedDate = params.get('date') ?? latestSnapshot
  // Degrada para renderizar mesmo assim se o /health falhar ou não houver snapshot.
  const healthSettledWithoutDate =
    !resolvedDate && (healthError || (!!health && !health.latest_snapshot))
  const canRender = Boolean(resolvedDate) || healthSettledWithoutDate

  // `document.title` por rota, para cada página e aba ter título próprio.
  const conteudo = useRef<HTMLElement>(null)
  // Altura do cabeçalho fixo em `--altura-topo`: os cabeçalhos de tabela fixos ficam logo abaixo dele
  // em qualquer largura, em vez de um número escrito à mão em cada tabela (89 px, 117 px…).
  const topo = useRef<HTMLElement>(null)
  useEffect(() => {
    const el = topo.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(() => document.documentElement.style.setProperty('--altura-topo', `${el.offsetHeight}px`))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  useTabelasResponsivas(conteudo)
  useEffect(() => { document.title = tituloDaRota(location.pathname) }, [location.pathname])

  // Sincroniza ?date → activeDate no Zustand
  useEffect(() => {
    const dateParam = params.get('date')
    setActiveDate(dateParam)
  }, [params, setActiveDate])

  // Quando a API responde, registra o snapshot mais recente
  useEffect(() => {
    if (health?.latest_snapshot) {
      setLatestSnapshot(health.latest_snapshot)
    }
  }, [health, setLatestSnapshot])

  const navClass = ({ isActive }: { isActive: boolean }) =>
    `text-xs sm:text-sm px-2 sm:px-3 py-1 sm:py-1.5 rounded transition-colors whitespace-nowrap ${
      isActive
        ? 'bg-primario-100 text-primario-700 font-medium'
        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
    }`

  // Seletor de snapshot, orçamento e login: no cabeçalho a partir de sm e dentro da gaveta no celular.
  const blocoConta = (
    <>
      <SnapshotSelector />
      <BudgetChip />
      <LeituraConfortavel />
      {!authLoading && (
        user ? (
          <span className="flex items-center gap-2 text-xs text-gray-500">
            <NavLink to="/perfil" className="truncate max-w-[14ch] hover:text-primario-600" title="Perfil">{user.name || user.email}</NavLink>
            <a href="/auth/logout" className="text-xs text-gray-500 hover:text-perigo-500 transition-colors whitespace-nowrap">Sair</a>
          </span>
        ) : (
          <a href="/login" className="text-xs text-primario-600 hover:text-primario-800 transition-colors whitespace-nowrap">Entrar</a>
        )
      )}
    </>
  )

  return (
    <div className={isMapPage ? 'h-screen flex flex-col bg-gray-50' : 'min-h-screen bg-gray-50'}>
      {/* Pular para o conteúdo (NBR 17225): primeiro elemento focável, visível só no foco. */}
      <a href="#conteudo" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2 focus:text-sm focus:text-primario-800 focus:shadow focus:ring-2 focus:ring-primario-500">
        Pular para o conteúdo
      </a>
      {/* Cabeçalho. Celular: uma linha (logo, busca, ☰); snapshot, orçamento e login ficam na gaveta. */}
      <header ref={topo} className="bg-white border-b border-gray-200 sticky top-0 z-40 print:hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-10 xl:px-16 h-12 flex items-center gap-2 sm:justify-between">
          <NavLink to="/" className="flex items-center gap-2 sm:gap-3 flex-shrink-0 group" aria-label={`${SITE.nome}: página inicial`}>
            <img src="/arandu-mark.svg" alt="" className="h-8 w-8 sm:h-10 sm:w-10" />
            <span className="hidden sm:inline text-[#0c1e45] text-sm sm:text-base font-semibold tracking-wide group-hover:text-primario-800 transition-colors whitespace-nowrap">
              {SITE.nome}
            </span>
            <span className="text-gray-500 text-sm font-light hidden md:inline whitespace-nowrap">
              {SITE.nomeExtenso}
            </span>
          </NavLink>

          <div className="flex-1 min-w-0 sm:hidden"><SearchBar /></div>

          <div className="hidden sm:flex items-center gap-3 min-w-0">{blocoConta}</div>

          <GavetaMenu topo={blocoConta} />
        </div>

        {/* Linha 2 (a partir de sm): nav + busca */}
        <div className="hidden sm:block border-t border-gray-100">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-10 xl:px-16 h-10 flex items-center gap-4">
            <nav aria-label="Menu principal" className="flex items-center gap-0.5 overflow-x-auto flex-1 min-w-0 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
              <NavLink to="/" end className={navClass}>
                Home
              </NavLink>
              <MenuTema />
            </nav>
            <div className="flex-shrink-0"><SearchBar /></div>
          </div>
        </div>
      </header>

      {/* Status bar quando API está offline ou sem dados */}
      {health && health.snapshots_available === 0 && (
        <div className="bg-aviso-50 border-b border-aviso-200 px-4 py-2 text-xs text-aviso-700 text-center">
          Nenhum snapshot publicado disponível. Execute o pipeline completo para gerar dados.
        </div>
      )}

      {/* Conteúdo da página — só renderiza com data resolvida (chamadas sempre datadas) */}
      <main ref={conteudo} id="conteudo" tabIndex={-1} className={`outline-none ${isMapPage ? 'flex-1 overflow-hidden relative' : 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-10 xl:px-16 py-6'}`}>
        {canRender ? (
          <Outlet />
        ) : (
          <div role="status" className="flex items-center justify-center py-20 text-sm text-gray-500">
            <svg className="animate-spin h-5 w-5 mr-2 text-gray-300" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.4 0 0 5.4 0 12h4z" />
            </svg>
            Carregando snapshot…
          </div>
        )}
      </main>

      {!isMapPage && (
        <footer className="border-t border-gray-200 mt-12 py-4 text-center text-xs text-gray-400 print:hidden">
          {SITE.nome} — {SITE.nomeExtenso}.{' '}
          <a href="/sobre" className="underline hover:text-gray-600">
            Metodologia e fontes
          </a>
          {' · '}
          <a href="/privacidade" className="underline hover:text-gray-600">
            Política de Privacidade
          </a>
          {' · '}
          <a href="/uso-aceitavel" className="underline hover:text-gray-600">
            Uso Aceitável
          </a>
          {' · '}
          <a href="/acessibilidade" className="underline hover:text-gray-600">
            Acessibilidade
          </a>
          {' · '}
          <span title="Versão do sistema">v{__APP_VERSION__}</span>
        </footer>
      )}
    </div>
  )
}
