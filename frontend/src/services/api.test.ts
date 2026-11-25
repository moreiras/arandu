import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  AccessError, fetchASN, fetchASNContacts, fetchASNs, fetchIXP, fetchSnapshots, onAnonLimitReached,
  onLoginRequired, queryColecao, setCurrentArea,
} from './api'
import { fixtures, seenHeaders, server } from '../test/server'
import { http, HttpResponse } from 'msw'

beforeEach(() => setCurrentArea('open'))

describe('cliente da API sobre respostas reais do dataset sintético', () => {
  it('lista snapshots e devolve o formato da API', async () => {
    const r = await fetchSnapshots()
    expect(r.latest).toBe(fixtures.snapshots.latest)
    expect(r.snapshots.length).toBeGreaterThan(0)
  })

  it('envia a área de acesso e o fingerprint em todo pedido', async () => {
    setCurrentArea('metered')
    await fetchSnapshots()
    const h = seenHeaders['/api/v1/brasil/snapshots']
    expect(h['x-arandu-area']).toBe('metered')
    expect(Object.keys(h).some((k) => k.includes('fingerprint') || k.includes('device'))).toBe(true)
  })

  it('primeira página da lista de ASNs', async () => {
    const r = await fetchASNs({ page: 1, limit: 5 })
    expect(r.items.length).toBeLessThanOrEqual(5)
    expect(r.total).toBe(fixtures.asnsPage1.total)
  })

  it('documento de um ASN', async () => {
    const d = await fetchASN(64496)
    expect(d.asn).toBe(64496)
    expect(Array.isArray(d.ixps_direct)).toBe(true)
  })
})

describe('tratamento de acesso (regra: qualquer 401 abre o modal, nunca erro cru)', () => {
  it('401 de paginação notifica o login com o motivo e vira AccessError(login)', async () => {
    const cb = vi.fn()
    const off = onLoginRequired(cb)
    await expect(fetchASNs({ page: 2, limit: 10 })).rejects.toMatchObject({ name: 'AccessError', kind: 'login' })
    expect(cb).toHaveBeenCalledWith('lista-expandida')
    off()
  })

  it('401 em /contacts usa o motivo "contatos" mesmo sem reason no corpo', async () => {
    const cb = vi.fn()
    const off = onLoginRequired(cb)
    await expect(fetchASNContacts(64496)).rejects.toBeInstanceOf(AccessError)
    expect(cb).toHaveBeenCalledWith('contatos')
    off()
  })

  it('429 vira AccessError(taxa) com a mensagem da API, sem abrir login', async () => {
    const cb = vi.fn()
    const off = onLoginRequired(cb)
    const msg = 'Você atingiu o limite de consultas de contato para sua conta. Tente novamente em 9 min.'
    server.use(http.get('*/api/v1/asns/:asn/contacts', () => HttpResponse.json({ detail: msg }, { status: 429, headers: { 'Retry-After': '540' } })))
    await expect(fetchASNContacts(64496)).rejects.toMatchObject({ kind: 'taxa', message: msg })
    server.use(http.get('*/api/v1/asns/:asn/contacts', () => new HttpResponse('slow down', { status: 429 })))
    await expect(fetchASNContacts(64496)).rejects.toMatchObject({ kind: 'taxa' })
    expect(cb).not.toHaveBeenCalled()
    off()
  })

  it('403 com anon_limit_reached notifica o limite e vira AccessError(limit)', async () => {
    const cb = vi.fn()
    const off = onAnonLimitReached(cb)
    const { fetchMapAsns } = await import('./api')
    await expect(fetchMapAsns()).rejects.toMatchObject({ kind: 'limit' })
    expect(cb).toHaveBeenCalled()
    off()
  })

  it('429 com anon_limit_reached (orçamento, D9) é o mesmo estado do 403: AccessError(limit), avisa o limite e guarda o Retry-After', async () => {
    const limite = vi.fn()
    const login = vi.fn()
    const offL = onAnonLimitReached(limite)
    const offG = onLoginRequired(login)
    server.use(http.get('*/api/v1/asns/:asn', () => HttpResponse.json(
      { detail: 'Limite de navegação anônima atingido.', anon_limit_reached: true }, { status: 429, headers: { 'Retry-After': '3600' } })))
    await expect(fetchASN(64496)).rejects.toMatchObject({ name: 'AccessError', kind: 'limit', retryAfter: 3600 })
    expect(limite).toHaveBeenCalled()
    expect(login).not.toHaveBeenCalled()
    offL(); offG()
  })

  it('429 de taxa guarda o Retry-After (segundos ou data HTTP); sem cabeçalho usa o retry_after do corpo', async () => {
    server.use(http.get('*/api/v1/asns/:asn', () => HttpResponse.json({ detail: 'Tente novamente em 42 s.' }, { status: 429, headers: { 'Retry-After': '42' } })))
    await expect(fetchASN(64496)).rejects.toMatchObject({ kind: 'taxa', retryAfter: 42 })
    const daqui = new Date(Date.now() + 120_000).toUTCString()
    server.use(http.get('*/api/v1/asns/:asn', () => new HttpResponse('slow down', { status: 429, headers: { 'Retry-After': daqui } })))
    const e = await fetchASN(64496).catch((x) => x)
    expect(e.retryAfter).toBeGreaterThan(100)
    expect(e.retryAfter).toBeLessThanOrEqual(120)
    server.use(http.get('*/api/v1/asns/:asn', () => HttpResponse.json({ detail: 'x', retry_after: 7 }, { status: 429 })))
    await expect(fetchASN(64496)).rejects.toMatchObject({ kind: 'taxa', retryAfter: 7 })
    server.use(http.get('*/api/v1/asns/:asn', () => new HttpResponse('slow down', { status: 429 })))
    await expect(fetchASN(64496)).rejects.toMatchObject({ kind: 'taxa', retryAfter: null })
  })

  it('401 guarda o motivo da API no erro', async () => {
    await expect(fetchASNs({ page: 2, limit: 10 })).rejects.toMatchObject({ kind: 'login', reason: 'lista-expandida' })
  })

  it('erro 500 não vira AccessError nem abre login', async () => {
    const cb = vi.fn()
    const off = onLoginRequired(cb)
    const err = await fetchIXP('sp').catch((e) => e)
    expect(err).toBeInstanceOf(Error)
    expect(err).not.toBeInstanceOf(AccessError)
    expect(String(err.message)).toContain('HTTP 500')
    expect(cb).not.toHaveBeenCalled()
    off()
  })
})

describe('API ocupada (503 busy): espera e tenta de novo', () => {
  afterEach(() => vi.useRealTimers())

  it('repete depois do Retry-After e devolve o dado quando a fila anda', async () => {
    vi.useFakeTimers()
    let chamadas = 0
    server.use(http.get('*/api/v1/asns/:asn', () => {
      chamadas += 1
      return chamadas < 3
        ? HttpResponse.json({ detail: 'Servidor ocupado', busy: true }, { status: 503, headers: { 'Retry-After': '2' } })
        : HttpResponse.json(fixtures.asnDetail)
    }))
    const p = fetchASN(64496)
    await vi.advanceTimersByTimeAsync(20000)
    expect((await p).asn).toBe(64496)
    expect(chamadas).toBe(3)
  })

  it('desiste depois de BUSY_RETRIES e mostra o erro (nunca fica em laço)', async () => {
    vi.useFakeTimers()
    let chamadas = 0
    server.use(http.get('*/api/v1/asns/:asn', () => {
      chamadas += 1
      return HttpResponse.json({ detail: 'ocupado', busy: true }, { status: 503, headers: { 'Retry-After': '1' } })
    }))
    const p = fetchASN(64496).catch((e) => e)
    await vi.advanceTimersByTimeAsync(60000)
    expect((await p).message).toMatch(/HTTP 503/)
    expect(chamadas).toBe(4)          // 1 + 3 retentativas
  })

  it('503 que não é "ocupado" (ex.: erro real) não é repetido', async () => {
    let chamadas = 0
    server.use(http.get('*/api/v1/asns/:asn', () => { chamadas += 1; return new HttpResponse('falhou', { status: 503 }) }))
    await expect(fetchASN(64496)).rejects.toThrow(/HTTP 503/)
    expect(chamadas).toBe(1)
  })
})


describe('consulta genérica (queryColecao)', () => {
  it('vai por GET com o corpo na URL (cacheável) e por POST quando o corpo não cabe nela', async () => {
    const vistos: Array<{ metodo: string; corpo: string | null }> = []
    server.use(
      http.get('*/api/v1/query/operadoras', ({ request }) => {
        vistos.push({ metodo: 'GET', corpo: new URL(request.url).searchParams.get('corpo') })
        return HttpResponse.json({ items: [], total: 0 })
      }),
      http.post('*/api/v1/query/operadoras', async ({ request }) => {
        vistos.push({ metodo: 'POST', corpo: JSON.stringify(await request.json()) })
        return HttpResponse.json({ items: [], total: 0 })
      }),
    )
    const corpo = { select: ['empresa'], limit: 5 }
    await queryColecao('operadoras', corpo, '2026-11-15')
    expect(vistos[0]).toEqual({ metodo: 'GET', corpo: JSON.stringify(corpo) })
    const grande = { filter: { field: 'cnpj', op: 'in', value: Array.from({ length: 800 }, (_, i) => String(10000000000000 + i)) } }
    await queryColecao('operadoras', grande, '2026-11-15')
    expect(vistos[1].metodo).toBe('POST')
  })
})
