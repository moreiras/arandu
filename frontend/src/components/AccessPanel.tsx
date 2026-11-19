import { useLocation } from 'react-router-dom'
import { LOGIN_REASONS } from '../auth/accessPolicy'

/** Painel de login no lugar de uma página/bloco avançado. Preserva `next`. */
export function AccessPanel({ reason = 'geral', compact = false }: { reason?: string; compact?: boolean }) {
  const location = useLocation()
  const next = encodeURIComponent(location.pathname + location.search)
  const message = LOGIN_REASONS[reason] ?? LOGIN_REASONS.geral
  return (
    <div
      className={`mx-auto bg-white border border-gray-200 rounded-xl text-center ${
        compact ? 'p-5 max-w-md my-4' : 'p-8 max-w-lg my-16'
      }`}
      role="status"
    >
      <h2 className="text-base font-semibold text-gray-800 mb-2">Entre para continuar</h2>
      <p className="text-sm text-gray-600 leading-relaxed mb-5">{message}</p>
      <a
        href={`/login?next=${next}`}
        className="inline-block px-5 py-2 rounded-lg text-sm text-white bg-[#0c1e45] hover:bg-primario-900 transition-colors"
      >
        Entrar
      </a>
      <p className="text-xs text-gray-400 mt-4">
        As páginas de entrada, a busca e os mapas de visão geral continuam abertos.
      </p>
    </div>
  )
}
