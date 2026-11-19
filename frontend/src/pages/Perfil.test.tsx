// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Perfil da conta: a chave aparece uma vez, a exclusão informa os 30 dias e anônimo é convidado a entrar. */
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { server } from '../test/server'
import { Perfil } from './Perfil'

let usuario: unknown = { email: 'a@example.org', name: 'A', provider: 'google' }
vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: usuario, anon: null, loading: false }) }))

const perfilBase = { email: 'a@example.org', nome: 'A', provedor: 'google', criada_em: '2026-11-01', ultimo_acesso: '2026-11-12', chave_mcp: { disponivel: true, ativa: null }, uso: [{ dia: '2026-11-12', chamadas: 7 }] }
const montar = () => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><Perfil /></MemoryRouter></QueryClientProvider>)

describe('/perfil', () => {
  it('visitante sem login é convidado a entrar', () => {
    usuario = null
    server.use(http.get('*/auth/perfil', () => new HttpResponse(null, { status: 401 })))
    montar()
    expect(screen.getByText(/Entre com a sua conta/)).toBeInTheDocument()
    usuario = { email: 'a@example.org', name: 'A', provider: 'google' }
  })

  it('gera a chave, mostra-a uma vez com as instruções e depois só o id', async () => {
    let ativa: unknown = null
    const chave = 'arandu_mcp_' + 'KKKKKKKK' + '_' + 'S'.repeat(52)
    server.use(
      http.get('*/auth/perfil', () => HttpResponse.json({ ...perfilBase, chave_mcp: { disponivel: true, ativa } })),
      http.post('*/auth/perfil/chave-mcp', ({ request }) => {
        expect(request.headers.get('X-Arandu-Acao')).toBe('1')
        ativa = { id: 'KKKKKKKK', criada_em: '2026-11-12T10:00:00+00:00', ultimo_uso_dia: null, rotulo: null }
        return HttpResponse.json({ chave, id: 'KKKKKKKK' })
      }),
    )
    montar()
    fireEvent.click(await screen.findByRole('button', { name: 'Gerar chave' }))
    const aviso = await screen.findByTestId('chave-nova')
    expect(aviso).toHaveTextContent(chave)
    expect(aviso).toHaveTextContent(/claude mcp add/)
    expect(aviso).toHaveTextContent(/não será mostrada de novo/)
    expect(screen.getByText(/7 chamadas/)).toBeInTheDocument()
  })

  it('a exclusão informa que não é imediata (30 dias) e mostra a data', async () => {
    server.use(
      http.get('*/auth/perfil', () => HttpResponse.json(perfilBase)),
      http.post('*/auth/perfil/excluir', () => HttpResponse.json({ exclusao_efetiva_em: '2026-12-12', prazo_dias: 30 })),
    )
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    montar()
    fireEvent.click(await screen.findByRole('button', { name: 'Solicitar exclusão da conta' }))
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(/12\/12\/2026 \(30 dias\)/))
  })

  it('chave de MCP ainda indisponível: texto explicativo, sem botão', async () => {
    server.use(http.get('*/auth/perfil', () => HttpResponse.json({ ...perfilBase, chave_mcp: { disponivel: false, ativa: null } })))
    montar()
    expect(await screen.findByText(/ainda não está disponível/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Gerar chave' })).toBeNull()
  })
})
