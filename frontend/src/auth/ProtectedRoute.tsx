import { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'
import { routeAccess } from './accessPolicy'
import { AccessPanel } from '../components/AccessPanel'

/** Porta de acesso de uma página avançada (`metered`) ou restrita (`login`).
 *
 * - logado ou IP isento (`user` preenchido): sempre passa;
 * - anônimo em página `metered`: passa enquanto houver orçamento de uso; ao
 *   esgotar, o painel de login substitui SÓ esta página (a entrada segue aberta);
 * - anônimo em página `login`: painel de login com o motivo.
 * O servidor aplica a mesma regra nas chamadas de API (gate do nginx). */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, anon, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-gray-400 text-sm">
        Carregando...
      </div>
    )
  }
  if (user) return <>{children}</>

  const access = routeAccess(location.pathname)
  if (access === 'login') {
    return <AccessPanel reason="historico" />
  }
  if (access === 'metered' && anon?.limitReached) {
    return <AccessPanel reason="esgotado" />
  }
  return <>{children}</>
}
