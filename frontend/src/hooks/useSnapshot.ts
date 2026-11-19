import { useSearchParams } from 'react-router-dom'
import { useAppStore } from '../store/app'

/**
 * Retorna a data ativa do snapshot, sempre concreta quando possível.
 * Prioridade: ?date na URL → activeDate no Zustand → latest conhecido via /health.
 *
 * O fallback para `latestSnapshot` garante que as chamadas à API sejam SEMPRE
 * datadas (e nunca resolvam "latest" no servidor), permitindo que o snapshot mais
 * recente seja cacheado por 7 dias. O AppLayout só renderiza o conteúdo quando há
 * uma data resolvida, evitando uma primeira requisição sem data.
 */
export function useActiveDate(): string | null {
  const [params] = useSearchParams()
  const activeDate = useAppStore((s) => s.activeDate)
  const latestSnapshot = useAppStore((s) => s.latestSnapshot)
  return params.get('date') ?? activeDate ?? latestSnapshot
}
