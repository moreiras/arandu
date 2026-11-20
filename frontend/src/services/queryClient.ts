import { QueryClient } from '@tanstack/react-query'
import { AccessError } from './api'

/** Repete uma vez só falha de rede e 5xx. Erro 4xx (404, 422, política 401/403/429) é resposta definitiva: repetir só dobra a linha
 *  vermelha no console. O 503 "ocupado" já tem espera própria em `fetchComEspera`. */
export function deveRepetir(tentativas: number, erro: unknown): boolean {
  if (tentativas >= 1 || erro instanceof AccessError) return false
  return !/^HTTP 4\d\d\b/.test(erro instanceof Error ? erro.message : '')
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 min — snapshots são semanais
      retry: deveRepetir,
      refetchOnWindowFocus: false,
    },
  },
})
