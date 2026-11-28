import { afterEach, describe, expect, it, vi } from 'vitest'

const UA_FIREFOX = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0'
const UA_FIREFOX_NOVO = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0'

/** Carrega o módulo do zero (os valores ficam em cache) com o ambiente de um navegador simulado: o modo privado muda canvas e WebGL. */
async function carregar(ua: string, canvas: string, webgl: string, tela = { width: 1440, height: 900, colorDepth: 24 }) {
  vi.resetModules()
  vi.stubGlobal('navigator', { userAgent: ua, language: 'pt-BR', hardwareConcurrency: 8 })
  vi.stubGlobal('screen', tela)
  const ctx = { fillRect() {}, fillText() {}, textBaseline: '', font: '', fillStyle: '' }
  const gl = {
    getExtension: () => ({ UNMASKED_VENDOR_WEBGL: 1, UNMASKED_RENDERER_WEBGL: 2 }),
    getParameter: (p: number) => (p === 1 ? 'vendor' : webgl),
  }
  const original = HTMLCanvasElement.prototype.getContext
  HTMLCanvasElement.prototype.getContext = ((tipo: string) => (tipo === '2d' ? ctx : gl)) as unknown as HTMLCanvasElement['getContext']
  HTMLCanvasElement.prototype.toDataURL = () => canvas
  try {
    const m = await import('./fingerprint')
    return { forte: m.getFingerprint(), estavel: m.getFingerprintEstavel(), familia: m.familiaDoNavegador }
  } finally {
    HTMLCanvasElement.prototype.getContext = original
  }
}

afterEach(() => vi.unstubAllGlobals())

describe('fingerprint em dois níveis', () => {
  it('o estável não muda com canvas, WebGL nem versão do navegador; o forte muda', async () => {
    const normal = await carregar(UA_FIREFOX, 'canvas-normal', 'gpu-real')
    const privada = await carregar(UA_FIREFOX_NOVO, 'canvas-ruido', 'gpu-generica')
    expect(privada.forte).not.toBe(normal.forte)
    expect(privada.estavel).toBe(normal.estavel)
  })

  it('o estável não carrega canvas, WebGL nem o user-agent inteiro', async () => {
    const m = await carregar(UA_FIREFOX, 'canvas-normal', 'gpu-real')
    for (const proibido of ['canvas-normal', 'gpu-real', 'vendor', '132', 'Mozilla', 'Gecko']) expect(m.estavel).not.toContain(proibido)
    const partes = m.estavel.split('||')
    expect([partes[0], partes[1], partes[3], partes[4]]).toEqual(['firefox/macos', 'pt-BR', '1440x900x24', '8'])
    expect(m.forte).toContain('canvas-normal')
  })

  it('o estável distingue outro tamanho de tela', async () => {
    const a = await carregar(UA_FIREFOX, 'c', 'g')
    const b = await carregar(UA_FIREFOX, 'c', 'g', { width: 1920, height: 1080, colorDepth: 24 })
    expect(b.estavel).not.toBe(a.estavel)
  })

  it.each([
    ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36', 'chrome/windows'],
    ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0', 'edge/windows'],
    ['Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15', 'safari/macos'],
    ['Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/130.0.0.0 Mobile/15E148 Safari/604.1', 'chrome/ios'],
    ['Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0', 'firefox/linux'],
    ['Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36', 'chrome/android'],
  ])('familiaDoNavegador(%#) = %s', async (ua, esperado) => {
    const m = await import('./fingerprint')
    expect(m.familiaDoNavegador(ua)).toBe(esperado)
  })
})
