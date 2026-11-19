import { createContext, useCallback, useContext, useEffect, useRef, useState, Dispatch, SetStateAction, ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { fetchAuthMe, postHeartbeat, onAnonLimitReached, onLoginRequired, setCurrentArea } from '../services/api'
import type { AnonInfo } from '../services/api'
import { routeAccess } from './accessPolicy'

export interface AuthUser {
  email: string | null
  name: string
  provider: string
}

interface AuthState {
  user: AuthUser | null
  anon: AnonInfo | null
  loading: boolean
}

/** Pedido de login em andamento (modal): motivo + para onde voltar. */
export interface LoginPrompt {
  reason: string
  next: string
}

interface AuthContextValue extends AuthState {
  loginPrompt: LoginPrompt | null
  /** Garante login para uma ação restrita. Devolve `true` se pode seguir (já
   * autenticado ou IP isento); senão abre o modal de login e devolve `false`. */
  requireLogin: (reason?: string) => boolean
  closeLoginPrompt: () => void
}

const noop = () => {}
const AuthContext = createContext<AuthContextValue>({
  user: null,
  anon: null,
  loading: true,
  loginPrompt: null,
  requireLogin: () => false,
  closeLoginPrompt: noop,
})

// Sinais de interação considerados para decidir se o usuário está "ativo".
// Combinados com a Page Visibility API — só conta se a aba está visível *e*
// houve um desses eventos dentro da janela de inatividade configurada.
const INTERACTION_EVENTS = ['mousemove', 'keydown', 'scroll', 'touchstart', 'click'] as const

/** Envia heartbeat periodicamente enquanto houver sessão anônima ativa (sem
 * login, fora de ALLOWED_IPS) e a aba estiver visível + com interação recente.
 * O backend calcula o tempo ativo por delta de timestamp — este hook só
 * decide *quando* vale a pena mandar o sinal, nunca conta tempo localmente.
 * A área da página (`open`/`metered`) vai no header: o relógio do orçamento só
 * corre em páginas avançadas. */
function useAnonHeartbeat(state: AuthState, setState: Dispatch<SetStateAction<AuthState>>) {
  const lastInteractionRef = useRef<number>(Date.now())
  const { user, anon, loading } = state

  useEffect(() => {
    const markActive = () => {
      lastInteractionRef.current = Date.now()
    }
    INTERACTION_EVENTS.forEach((evt) => window.addEventListener(evt, markActive, { passive: true }))
    return () => {
      INTERACTION_EVENTS.forEach((evt) => window.removeEventListener(evt, markActive))
    }
  }, [])

  useEffect(() => {
    if (loading || user || !anon || anon.limitReached) return

    const intervalMs = anon.heartbeatIntervalSeconds * 1000
    const inactivityMs = anon.inactivityTimeoutSeconds * 1000

    const tick = async () => {
      const isVisible = document.visibilityState === 'visible'
      const recentlyActive = Date.now() - lastInteractionRef.current < inactivityMs
      if (!isVisible || !recentlyActive) return

      const updated = await postHeartbeat()
      if (updated) {
        setState((s) => (s.user ? s : { ...s, anon: updated }))
      }
    }

    const id = window.setInterval(tick, intervalMs)
    return () => window.clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, user, anon?.heartbeatIntervalSeconds, anon?.inactivityTimeoutSeconds, anon?.limitReached])
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ user: null, anon: null, loading: true })
  const [loginPrompt, setLoginPrompt] = useState<LoginPrompt | null>(null)
  const location = useLocation()

  // Área da rota atual para o header X-Arandu-Area (orçamento só em `metered`).
  // Definida durante o render (antes dos efeitos dos filhos) para que as
  // primeiras chamadas da página já saiam com a área certa.
  setCurrentArea(routeAccess(location.pathname) === 'open' ? 'open' : 'metered')

  useEffect(() => {
    fetchAuthMe()
      .then((res) => {
        if (!res || !res.authenticated) {
          setState({ user: null, anon: res?.anon ?? null, loading: false })
          return
        }
        setState({
          user: { email: res.email ?? null, name: res.name ?? '', provider: res.provider ?? '' },
          anon: null,
          loading: false,
        })
      })
      .catch(() => setState({ user: null, anon: null, loading: false }))
  }, [])

  // Qualquer resposta de API (não só /auth/me e /auth/heartbeat) pode
  // sinalizar limite atingido via header — mantém o estado em sincronia
  // mesmo se o heartbeat ainda não rodou desde que o limite foi cruzado.
  useEffect(
    () =>
      onAnonLimitReached(() => {
        setState((s) => (s.anon && !s.anon.limitReached ? { ...s, anon: { ...s.anon, limitReached: true } } : s))
      }),
    [],
  )

  // 401 `login_required` (expandir lista, histórico...): abre o modal.
  useEffect(
    () =>
      onLoginRequired((reason) => {
        setLoginPrompt({
          reason: reason ?? 'geral',
          next: window.location.pathname + window.location.search,
        })
      }),
    [],
  )

  const requireLogin = useCallback(
    (reason: string = 'geral') => {
      if (state.user || state.loading) return true
      setLoginPrompt({ reason, next: window.location.pathname + window.location.search })
      return false
    },
    [state.user, state.loading],
  )
  const closeLoginPrompt = useCallback(() => setLoginPrompt(null), [])

  useAnonHeartbeat(state, setState)

  return (
    <AuthContext.Provider value={{ ...state, loginPrompt, requireLogin, closeLoginPrompt }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
