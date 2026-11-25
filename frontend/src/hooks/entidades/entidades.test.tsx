// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { server, fixtures } from '../../test/server'
import { useAppStore } from '../../store/app'
import { AuthProvider } from '../../auth/AuthContext'
import { chaves, useAsn, useFontes, useGrupo, useIxp, useOperadoraPerfil, useUfPerfil } from '.'

const DATA = '2026-09-20'
let qc: QueryClient
const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={qc}><MemoryRouter>{children}</MemoryRouter></QueryClientProvider>
)

beforeEach(() => {
  qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  useAppStore.setState({ activeDate: null, latestSnapshot: DATA })
})

describe('hooks por entidade', () => {
  it('useAsn busca o documento e grava no cache com a MESMA chave que a página usa', async () => {
    const { result } = renderHook(() => useAsn(64496), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.asn).toBe(64496)
    expect(qc.getQueryData(chaves.asn(64496, DATA))).toBe(result.current.data)
    expect(qc.getQueryData(['asn', 64496, DATA])).toBeDefined()
  })

  it('sem identificador (ou sem data) não chama a API', async () => {
    const { result } = renderHook(() => useAsn(undefined), { wrapper })
    expect(result.current.fetchStatus).toBe('idle')
    useAppStore.setState({ latestSnapshot: null })
    const r2 = renderHook(() => useAsn(64496), { wrapper })
    expect(r2.result.current.fetchStatus).toBe('idle')
  })

  it('erro da API chega como isError (a tela decide a mensagem; 401 já abre o modal no cliente)', async () => {
    const { result } = renderHook(() => useIxp('sp'), { wrapper })   // o servidor de teste responde 500 para /ixps/:code
    await waitFor(() => expect(result.current.isError).toBe(true))
  })

  it('a data da URL vence a data mais recente', async () => {
    let pedida = ''
    server.use(http.get('*/api/v1/asns/:asn', ({ request }) => { pedida = new URL(request.url).searchParams.get('date') ?? ''; return HttpResponse.json(fixtures.asnDetail) }))
    useAppStore.setState({ activeDate: '2026-08-01' })
    const { result } = renderHook(() => useAsn(64496), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(pedida).toBe('2026-08-01')
  })

  it('useOperadoraPerfil e useUfPerfil chamam os perfis', async () => {
    const vistos: string[] = []
    server.use(
      http.get('*/api/v1/operadoras/:cnpj', ({ request }) => { vistos.push(new URL(request.url).pathname); return HttpResponse.json({ snapshot_date: DATA, cnpj: '12345678000190', scm: { acessos: 5 }, smp: null, rede: { n: 1 } }) }),
      http.get('*/api/v1/ufs/:uf', ({ request }) => { vistos.push(new URL(request.url).pathname); return HttpResponse.json({ snapshot_date: DATA, uf: 'SP', totais: {} }) }),
    )
    const a = renderHook(() => useOperadoraPerfil('12345678000190'), { wrapper })
    const b = renderHook(() => useUfPerfil('sp'), { wrapper })
    await waitFor(() => expect(a.result.current.isSuccess && b.result.current.isSuccess).toBe(true))
    expect(vistos[0]).toBe('/api/v1/operadoras/12345678000190')
    expect(a.result.current.dados?.data).toMatchObject({ cnpj: '12345678000190', acessos: 5, rede: { n: 1 } })   // envelope e rede de volta
    expect(a.result.current.dados?.dataMovel).toBeUndefined()
    expect(vistos.join()).toContain('/api/v1/ufs/SP')
  })

  it('useUfPerfil exige sigla de 2 letras', () => {
    const { result } = renderHook(() => useUfPerfil('sao-paulo'), { wrapper })
    expect(result.current.fetchStatus).toBe('idle')
  })

  it('useGrupo acha o grupo na lista e informa se a lista chegou', async () => {
    server.use(http.get('*/api/v1/grupos', () => HttpResponse.json({ snapshot_date: DATA, total: 1, grupos: [{ grupo_id: 'g1', nome: 'G' }] })))
    const { result } = renderHook(() => useGrupo('g1'), { wrapper })
    await waitFor(() => expect(result.current.listaCarregada).toBe(true))
    expect(result.current.data?.grupo_id).toBe('g1')
    const r2 = renderHook(() => useGrupo('inexistente'), { wrapper })
    await waitFor(() => expect(r2.result.current.listaCarregada).toBe(true))
    expect(r2.result.current.data).toBeUndefined()
  })

  it('useFontes devolve sources[] do manifesto; sem manifesto, undefined (proveniência não inventa data)', async () => {
    server.use(http.get('*/api/v1/brasil/snapshots/:date', () => HttpResponse.json({ date: DATA, summary: null, manifest: { sources: [{ id: 'x', as_of: DATA }] } })))
    const a = renderHook(() => useFontes(), { wrapper })
    await waitFor(() => expect(a.result.current.fontes?.[0].id).toBe('x'))
    expect(a.result.current.snapshot).toBe(DATA)

    qc.clear()
    server.use(http.get('*/api/v1/brasil/snapshots/:date', () => HttpResponse.json({ date: DATA, summary: null, manifest: null })))
    const b = renderHook(() => useFontes(), { wrapper })
    await waitFor(() => expect(qc.getQueryState(chaves.snapshot(DATA))?.status).toBe('success'))
    expect(b.result.current.fontes).toBeUndefined()
  })

  it('perfil pede a série histórica inteira só com login (outra URL, que a API reserva a quem entrou)', async () => {
    const pedidos: string[] = []
    const montar = (autenticado: boolean) => {
      server.use(
        http.get('*/auth/me', () => HttpResponse.json(autenticado
          ? { authenticated: true, email: 'a@exemplo.test', name: 'A', provider: 'google' }
          : { authenticated: false, anon: { active_seconds: 0, limit_seconds: 600, limit_reached: false, heartbeat_interval_seconds: 60, inactivity_timeout_seconds: 120 } })),
        http.get('*/api/v1/ufs/:uf', ({ request }) => { pedidos.push(new URL(request.url).searchParams.get('include') ?? ''); return HttpResponse.json({ snapshot_date: DATA, uf: 'SP', totais: {} }) }),
      )
      qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
      const comAuth = ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={qc}><MemoryRouter><AuthProvider>{children}</AuthProvider></MemoryRouter></QueryClientProvider>
      )
      return renderHook(() => useUfPerfil('sp'), { wrapper: comAuth })
    }
    const anon = montar(false)
    await waitFor(() => expect(anon.result.current.isSuccess).toBe(true))
    expect(pedidos[pedidos.length - 1]?.split(',')).toContain('historico')
    expect(pedidos.join()).not.toContain('historico_completo')
    anon.unmount()
    pedidos.length = 0
    const logado = montar(true)
    await waitFor(() => expect(pedidos.some((i) => i.split(',').includes('historico_completo'))).toBe(true))
    logado.unmount()
  })
})
