import { beforeEach, describe, expect, it } from 'vitest'
import { carregarCamadasEstaticas, limparCamadasEstaticas, urlCamada } from './camadasEstaticas'

const resposta = (corpo: unknown, ok = true) => Promise.resolve({ ok, json: () => Promise.resolve(corpo) } as Response)

describe('camadas estáticas por hash', () => {
  beforeEach(limparCamadasEstaticas)

  it('usa a URL sem versão antes de carregar', () => {
    expect(urlCamada('submarine_cables', '/api/v1/map/submarine-cables')).toBe('/api/v1/map/submarine-cables')
  })

  it('passa a usar a URL com ?v= depois de carregar', async () => {
    await carregarCamadasEstaticas(() =>
      resposta({ camadas: { submarine_cables: { hash: 'abc', url: '/api/v1/map/submarine-cables?v=abc' } } }))
    expect(urlCamada('submarine_cables', 'x')).toBe('/api/v1/map/submarine-cables?v=abc')
    expect(urlCamada('itu_transmission', 'fallback')).toBe('fallback')
  })

  it('falha em silêncio e mantém o fallback', async () => {
    await carregarCamadasEstaticas(() => resposta({}, false))
    await carregarCamadasEstaticas(() => Promise.reject(new Error('rede')))
    expect(urlCamada('submarine_cables', 'fb')).toBe('fb')
  })
})
