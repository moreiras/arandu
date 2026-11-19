// Fingerprint de dispositivo — usado apenas como fallback de identidade da
// sessão anônima quando o cookie é bloqueado/apagado (ver AuthContext).
// O backend nunca recebe nem armazena isto em texto claro: ele aplica um
// hash (SHA-256) antes de persistir.

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
