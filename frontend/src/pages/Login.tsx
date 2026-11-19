import { useSearchParams } from 'react-router-dom'
import { useEffect } from 'react'
import { tituloDaRota } from '../components/layout/tituloRota'
import { SITE } from '../lib/site'

const ERROR_MESSAGES: Record<string, string> = {
  cancelled: 'Login cancelado.',
  invalid_state: 'Sessão inválida. Tente novamente.',
  conta_em_exclusao: 'Esta conta tem a exclusão solicitada e está desativada até o apagamento, em até 30 dias do pedido. Para cancelar, use o contato indicado na Política de Privacidade (/privacidade).',
  token_failed: 'Erro ao autenticar. Tente novamente.',
  no_email: 'Não foi possível obter o e-mail da conta.',
  email_nao_verificado: 'O provedor não confirmou o e-mail desta conta. Confirme o e-mail no provedor e tente de novo.',
  anon_limit: 'Tempo de navegação sem login esgotado. Faça login para continuar.',
}

export function Login() {
  const [params] = useSearchParams()
  // Fora do AppLayout, que é quem põe o título nas outras páginas (NBR 17225, 5.13.1: título único).
  useEffect(() => { document.title = tituloDaRota('/login') }, [])
  const next = params.get('next') || '/'
  const errorKey = params.get('error') || ''
  const errorMsg = ERROR_MESSAGES[errorKey] || (errorKey ? 'Erro ao fazer login.' : null)

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 w-full max-w-sm">
        <div className="text-center mb-8">
          <img src="/arandu-mark.svg" alt="" className="h-12 w-12 mx-auto mb-4" />
          <h1 className="text-xl font-light text-[#0c1e45] tracking-widest uppercase">
            {SITE.nome}
          </h1>
          <p className="text-sm text-gray-500 mt-3 leading-relaxed">
            Faça login para explorar análises da Internet brasileira.
          </p>
        </div>

        {errorMsg && (
          <div className="mb-5 text-sm text-perigo-600 bg-perigo-50 rounded-lg px-4 py-2 text-center">
            {errorMsg}
          </div>
        )}

        <p className="text-xs text-gray-400 text-center mb-4 leading-relaxed">
          Ao entrar, você concorda com a{' '}
          <a href="/privacidade" className="underline hover:text-gray-600">política de privacidade</a>,
          incluindo o recebimento de comunicações e ofertas.
        </p>

        <div className="flex flex-col gap-3">
          <a
            href={`/auth/google?next=${encodeURIComponent(next)}`}
            className="flex items-center justify-center gap-3 w-full px-4 py-3 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <GoogleIcon />
            Continuar com Google
          </a>
          <a
            href={`/auth/linkedin?next=${encodeURIComponent(next)}`}
            className="flex items-center justify-center gap-3 w-full px-4 py-3 rounded-lg text-sm text-white transition-colors"
            style={{ backgroundColor: '#0A66C2' }}
            onMouseOver={e => (e.currentTarget.style.backgroundColor = '#004182')}
            onMouseOut={e => (e.currentTarget.style.backgroundColor = '#0A66C2')}
          >
            <LinkedInIcon />
            Continuar com LinkedIn
          </a>
          <a
            href={`/auth/peeringdb?next=${encodeURIComponent(next)}`}
            className="flex items-center justify-center gap-3 w-full px-4 py-3 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <PeeringDBIcon />
            Continuar com PeeringDB
          </a>
        </div>
      </div>
    </main>
  )
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5 flex-shrink-0" aria-hidden>
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  )
}

function PeeringDBIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5 flex-shrink-0" aria-hidden fill="none">
      <circle cx="5"  cy="12" r="3" fill="#F97316"/>
      <circle cx="19" cy="5"  r="2" fill="#F97316"/>
      <circle cx="19" cy="19" r="2" fill="#F97316"/>
      <line x1="8"  y1="11" x2="17" y2="6.5" stroke="#F97316" strokeWidth="1.5"/>
      <line x1="8"  y1="13" x2="17" y2="17.5" stroke="#F97316" strokeWidth="1.5"/>
    </svg>
  )
}

function LinkedInIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5 flex-shrink-0" aria-hidden fill="white">
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
    </svg>
  )
}
