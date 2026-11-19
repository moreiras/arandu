import { useEffect } from 'react'
import { useAuth } from '../auth/AuthContext'
import { LOGIN_REASONS } from '../auth/accessPolicy'

/** Modal de login disparado por ações restritas (paginar, histórico, CSV...).
 * Não navega: a página fica como estava; o login volta para `next`. */
export function LoginModal() {
  const { loginPrompt, closeLoginPrompt, user } = useAuth()

  useEffect(() => {
    if (!loginPrompt) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && closeLoginPrompt()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [loginPrompt, closeLoginPrompt])

  if (!loginPrompt || user) return null
  const message = LOGIN_REASONS[loginPrompt.reason] ?? LOGIN_REASONS.geral
  const next = encodeURIComponent(loginPrompt.next)

  return (
    <div
      className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/40 px-4"
      onClick={closeLoginPrompt}
      role="dialog"
      aria-modal="true"
      aria-label="Entrar"
    >
      <div
        className="bg-white rounded-xl shadow-lg border border-gray-200 p-7 w-full max-w-sm text-center"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-base font-semibold text-gray-800 mb-2">Entre para continuar</h2>
        <p className="text-sm text-gray-600 leading-relaxed mb-5">{message}</p>
        <a
          href={`/login?next=${next}`}
          className="block w-full px-4 py-2.5 rounded-lg text-sm text-white bg-[#0c1e45] hover:bg-primario-900 transition-colors"
        >
          Entrar
        </a>
        <button
          onClick={closeLoginPrompt}
          className="mt-3 text-xs text-gray-500 hover:text-gray-700 hover:underline"
        >
          Agora não
        </button>
      </div>
    </div>
  )
}
