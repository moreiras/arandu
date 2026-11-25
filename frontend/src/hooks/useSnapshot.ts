import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '../store/app'
import { useAuth } from '../auth/AuthContext'
import { fetchSnapshots } from '../services/api'

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

/**
 * As datas dos snapshots: a lista inteira com login, só as atuais sem login (D9: `/snapshots` é `login`). A chave inclui o nível, para a lista
 * curta de quem ainda não entrou nunca ficar no lugar da inteira. Enquanto o `/auth/me` não responde vale a lista aberta (barata e sempre liberada).
 */
export function useSnapshots() {
  const { user } = useAuth()
  const completo = !!user
  return useQuery({ queryKey: ['snapshots', completo], queryFn: () => fetchSnapshots(completo), staleTime: Infinity, gcTime: Infinity })
}
