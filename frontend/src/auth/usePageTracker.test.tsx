import { renderHook } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const postAuthLog = vi.fn()
let usuario: { email: string | null; name: string; provider: string } | null = null

vi.mock('../services/api', () => ({ postAuthLog: (p: string) => postAuthLog(p) }))
vi.mock('./AuthContext', () => ({ useAuth: () => ({ user: usuario }) }))

import { usePageTracker } from './usePageTracker'

const comRota = ({ children }: { children: ReactNode }) => <MemoryRouter initialEntries={['/ases?q=1']}>{children}</MemoryRouter>

describe('usePageTracker: só conta registra navegação', () => {
  beforeEach(() => { postAuthLog.mockClear() })

  it('registra a página de quem tem conta', () => {
    usuario = { email: 'a@exemplo.invalid', name: 'A', provider: 'google' }
    renderHook(() => usePageTracker(), { wrapper: comRota })
    expect(postAuthLog).toHaveBeenCalledWith('/ases?q=1')
  })

  it('não chama /auth/log para o Visitante da allowlist (provider ip) nem para anônimo', () => {
    usuario = { email: null, name: 'Visitante', provider: 'ip' }
    renderHook(() => usePageTracker(), { wrapper: comRota })
    usuario = null
    renderHook(() => usePageTracker(), { wrapper: comRota })
    expect(postAuthLog).not.toHaveBeenCalled()
  })
})
