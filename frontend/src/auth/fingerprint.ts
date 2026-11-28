// Fingerprint de dispositivo — usado apenas como fallback de identidade da
// sessão anônima quando o cookie é bloqueado/apagado (ver AuthContext).
// O backend nunca armazena isto em texto claro: ele aplica um hash (SHA-256)
// antes de persistir.
//
// Dois níveis: o "forte" (UA inteiro, idioma, fuso, tela, núcleos, canvas, WebGL)
// e o "estável", sem os sinais que o modo privado do Safari e do Firefox altera
// (canvas e WebGL) nem a versão do navegador: só família do navegador e do sistema,
// idioma, fuso, tela e núcleos. O servidor tenta o forte e, se não achar sessão,
// o estável.

function safe<T>(fn: () => T, fallback: T): T {
  try {
    return fn()
  } catch {
    return fallback
  }
}

function canvasSignal(): string {
  return safe(() => {
    const canvas = document.createElement('canvas')
    canvas.width = 200
    canvas.height = 40
    const ctx = canvas.getContext('2d')
    if (!ctx) return ''
    ctx.textBaseline = 'top'
    ctx.font = '14px Arial'
    ctx.fillStyle = '#f60'
    ctx.fillRect(0, 0, 100, 20)
    ctx.fillStyle = '#069'
    ctx.fillText('arandurape-fp', 2, 2)
    return canvas.toDataURL()
  }, '')
}

function webglSignal(): string {
  return safe(() => {
    const canvas = document.createElement('canvas')
    const gl = (canvas.getContext('webgl') ||
      canvas.getContext('experimental-webgl')) as WebGLRenderingContext | null
    if (!gl) return ''
    const info = gl.getExtension('WEBGL_debug_renderer_info')
    if (!info) return ''
    return `${gl.getParameter(info.UNMASKED_VENDOR_WEBGL)}|${gl.getParameter(info.UNMASKED_RENDERER_WEBGL)}`
  }, '')
}

let cached: string | null = null

/** Combina sinais disponíveis no navegador numa string estável por sessão de página. */
export function getFingerprint(): string {
  if (cached !== null) return cached
  const parts = [
    safe(() => navigator.userAgent, ''),
    safe(() => navigator.language, ''),
    safe(() => Intl.DateTimeFormat().resolvedOptions().timeZone, ''),
    safe(() => `${screen.width}x${screen.height}x${screen.colorDepth}`, ''),
    safe(() => String(navigator.hardwareConcurrency ?? ''), ''),
    canvasSignal(),
    webglSignal(),
  ]
  cached = parts.join('||')
  return cached
}

/** Família do navegador e do sistema a partir do user-agent, sem versões (uma atualização do navegador não muda o valor). */
export function familiaDoNavegador(ua: string): string {
  const navegador = /Edg(?:e|A|iOS)?\//.test(ua) ? 'edge'
    : /OPR\/|Opera/.test(ua) ? 'opera'
    : /Firefox\/|FxiOS\//.test(ua) ? 'firefox'
    : /Chrome\/|CriOS\//.test(ua) ? 'chrome'
    : /Safari\//.test(ua) ? 'safari'
    : 'outro'
  const sistema = /iPhone|iPad|iPod/.test(ua) ? 'ios'
    : /Android/.test(ua) ? 'android'
    : /Windows/.test(ua) ? 'windows'
    : /Mac OS X|Macintosh/.test(ua) ? 'macos'
    : /Linux|X11/.test(ua) ? 'linux'
    : 'outro'
  return `${navegador}/${sistema}`
}

let cachedEstavel: string | null = null

/** Fingerprint estável: sobrevive à janela privada do Safari e do Firefox, que muda canvas e WebGL. Menos específico que o forte. */
export function getFingerprintEstavel(): string {
  if (cachedEstavel !== null) return cachedEstavel
  const parts = [
    familiaDoNavegador(safe(() => navigator.userAgent, '')),
    safe(() => navigator.language, ''),
    safe(() => Intl.DateTimeFormat().resolvedOptions().timeZone, ''),
    safe(() => `${screen.width}x${screen.height}x${screen.colorDepth}`, ''),
    safe(() => String(navigator.hardwareConcurrency ?? ''), ''),
  ]
  cachedEstavel = parts.join('||')
  return cachedEstavel
}
