import { useAuth } from '../auth/AuthContext'

/** Indicador do orçamento de uso avançado para anônimos ("restam N min"). */
export function BudgetChip() {
  const { user, anon, loading } = useAuth()
  if (loading || user || !anon) return null
  const left = Math.max(0, anon.limitSeconds - anon.activeSeconds)
  const min = Math.ceil(left / 60)
  // NBR 17225 5.16.2: o login desliga o limite; o aviso aparece em todas as larguras, inclusive no celular
  // e, a 2 minutos do fim, diz como continuar. `role=status` anuncia a mudança a leitores de tela.
  const perto = !anon.limitReached && left <= 120
  const text = anon.limitReached ? 'Uso avançado esgotado: entre gratuitamente para continuar' : perto ? `Restam ${min} min de uso avançado: entre gratuitamente para continuar sem limite` : `Uso avançado: restam ${min} min`
  // O minuto só é anunciado quando muda de faixa (perto do fim ou esgotado), não a cada minuto.
  return (
    <span className="inline-flex">
    <span role="status" className="sr-only">{anon.limitReached ? 'Uso avançado esgotado. Entre gratuitamente para continuar.' : perto ? 'Faltam menos de 2 minutos de uso avançado. Entre gratuitamente para continuar sem limite.' : ''}</span>
    <a
      href="/login"
      title="Entre para usar as páginas avançadas sem limite de tempo"
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs transition-colors ${
        anon.limitReached || perto
          ? 'border-aviso-300 bg-aviso-50 text-aviso-800'
          : 'border-gray-200 bg-white text-gray-500 hover:text-gray-700'
      }`}
    >
      {text}
    </a>
    </span>
  )
}
