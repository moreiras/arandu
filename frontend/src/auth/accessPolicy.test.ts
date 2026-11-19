import { describe, expect, it } from 'vitest'
import { isHistoricalDate, LOGIN_REASONS, PREVIEW_LIMIT, routeAccess } from './accessPolicy'

describe('routeAccess (espelho de api/auth/access_policy.py)', () => {
  it.each(['/', '/login', '/sobre', '/privacidade', '/ixps', '/ases', '/scms', '/smps', '/stfcs', '/seacs', '/grupos'])(
    'página de entrada %s é open', (p) => expect(routeAccess(p)).toBe('open'))

  it('barra final não muda a classe', () => {
    expect(routeAccess('/ixps/')).toBe('open')
    expect(routeAccess('/snapshots///')).toBe('login')
  })

  it('histórico exige login', () => expect(routeAccess('/snapshots')).toBe('login'))

  it.each(['/mapa', '/bgp', '/estatisticas', '/ixps/sp', '/ases/64496', '/operadora/123', '/comparar'])(
    'avançada %s é metered (rota não listada cai aqui)', (p) => expect(routeAccess(p)).toBe('metered'))
})

describe('snapshots históricos', () => {
  const snaps = ['2026-09-06', '2026-09-13', '2026-09-20']
  it('os 2 mais recentes são atuais, o resto é histórico', () => {
    expect(isHistoricalDate('2026-09-20', snaps)).toBe(false)
    expect(isHistoricalDate('2026-09-13', snaps)).toBe(false)
    expect(isHistoricalDate('2026-09-06', snaps)).toBe(true)
  })
  it('sem data ou sem lista não é histórico', () => {
    expect(isHistoricalDate(null, snaps)).toBe(false)
    expect(isHistoricalDate('2026-01-01', [])).toBe(false)
  })
  it('ordem da lista não importa', () => expect(isHistoricalDate('2026-09-06', [...snaps].reverse())).toBe(true))
})

it('prévia de 100 linhas e motivos de login definidos', () => {
  expect(PREVIEW_LIMIT).toBe(100)
  for (const k of ['lista-expandida', 'historico', 'contatos', 'exportar', 'esgotado', 'geral']) {
    expect(LOGIN_REASONS[k]).toBeTruthy()
  }
})
