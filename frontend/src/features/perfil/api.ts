// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AccessError } from '../../services/api'

export interface PerfilConta {
  email: string
  nome: string | null
  provedor: string | null
  criada_em: string
  ultimo_acesso: string
  chave_mcp: { disponivel: boolean; ativa: { id: string; criada_em: string; ultimo_uso_dia: string | null; rotulo: string | null } | null }
  uso: { dia: string; chamadas: number }[]
}

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? ''
const ACAO = { 'X-Arandu-Acao': '1', 'Content-Type': 'application/json' }

async function chamar<T>(caminho: string, metodo = 'GET', corpo?: unknown): Promise<T> {
  const r = await fetch(`${BASE}/auth/perfil${caminho}`, { method: metodo, credentials: 'include', headers: metodo === 'GET' ? undefined : ACAO, body: corpo === undefined ? undefined : JSON.stringify(corpo) })
  if (r.status === 429) {
    const espera = Number(r.headers.get('Retry-After'))
    throw new AccessError('taxa', 'Muitas consultas em pouco tempo. Tente novamente em instantes.', { retryAfter: Number.isFinite(espera) && espera > 0 ? espera : null })
  }
  if (!r.ok) throw new Error(r.status === 401 ? 'login' : `HTTP ${r.status}`)
  return r.json()
}

/** `logado`: só consulta com sessão de conta; sem ela a rota responde 401, que o navegador registra no console. */
export const usePerfil = (logado = true) => useQuery<PerfilConta>({ queryKey: ['perfil'], queryFn: () => chamar<PerfilConta>(''), enabled: logado, retry: false, staleTime: 30_000 })

export function useAcoesPerfil() {
  const qc = useQueryClient()
  const atualizar = () => qc.invalidateQueries({ queryKey: ['perfil'] })
  return {
    gerarChave: useMutation({ mutationFn: (rotulo: string) => chamar<{ chave: string; id: string }>('/chave-mcp', 'POST', { rotulo: rotulo || null }), onSuccess: atualizar }),
    revogarChave: useMutation({ mutationFn: () => chamar<{ revogada: boolean }>('/chave-mcp', 'DELETE'), onSuccess: atualizar }),
    sairDeTodos: useMutation({ mutationFn: () => chamar<{ ok: boolean }>('/sair-de-todos', 'POST') }),
    excluir: useMutation({ mutationFn: () => chamar<{ exclusao_efetiva_em: string; prazo_dias: number }>('/excluir', 'POST') }),
  }
}
