// Servidor msw dos testes: respostas REAIS da API sobre o dataset sintético (Arandurápolis).
// Regerar: python -m tests.synth.export_front_fixtures
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import snapshots from './fixtures/snapshots.json'
import ixps from './fixtures/ixps.json'
import asnsPage1 from './fixtures/asns_page1.json'
import asnDetail from './fixtures/asn_detail.json'
import health from './fixtures/health.json'

export const fixtures = { snapshots, ixps, asnsPage1, asnDetail, health }

/** Cabeçalhos da última requisição a cada caminho (os testes conferem X-Arandu-Area etc.). */
export const seenHeaders: Record<string, Record<string, string>> = {}

function seen(path: string, request: Request) {
  seenHeaders[path] = Object.fromEntries(request.headers.entries())
}

export const handlers = [
  http.get('*/health', ({ request }) => { seen('/health', request); return HttpResponse.json(health) }),
  http.get('*/api/v1/brasil/snapshots', ({ request }) => { seen('/api/v1/brasil/snapshots', request); return HttpResponse.json(snapshots) }),
  http.get('*/api/v1/ixps', () => HttpResponse.json(ixps)),
  http.get('*/api/v1/asns', ({ request }) => {
    const u = new URL(request.url)
    if (Number(u.searchParams.get('page') ?? '1') > 1) {
      return HttpResponse.json({ detail: 'Esta ação exige login.', login_required: true, reason: 'lista-expandida' }, { status: 401 })
    }
    return HttpResponse.json(asnsPage1)
  }),
  http.get('*/api/v1/asns/:asn/contacts', () =>
    HttpResponse.json({ detail: 'Esta ação exige login.', login_required: true }, { status: 401 })),
  http.get('*/api/v1/asns/:asn', () => HttpResponse.json(asnDetail)),
  http.get('*/api/v1/map/asns', () =>
    HttpResponse.json({ detail: 'Limite atingido', anon_limit_reached: true }, { status: 403, headers: { 'X-Anon-Limit-Reached': 'true' } })),
  http.get('*/api/v1/ixps/:code', () => new HttpResponse('boom', { status: 500 })),
  // cadastro de telecom: sem cadastro na maioria dos testes (204 com `opcional=1`); os que precisam sobrescrevem
  http.get('*/api/v1/empresas/*', () => new HttpResponse(null, { status: 204 })),
  // crédito público e sanções: sem registro na maioria dos testes (204 com `opcional=1`)
  http.get('*/api/v1/financiamento/*', () => new HttpResponse(null, { status: 204 })),
  // contratos públicos: sem leitura na maioria dos testes (204 com `opcional=1`)
  http.get('*/api/v1/contratos/*', () => new HttpResponse(null, { status: 204 })),
]

export const server = setupServer(...handlers)
