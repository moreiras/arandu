/**
 * Utilitários para o Mapa de Espaço IPv4 baseado na Curva de Hilbert.
 * Funções puras — sem React, sem efeitos colaterais.
 *
 * Referência: https://en.wikipedia.org/wiki/Hilbert_curve#Applications_and_mapping_algorithms
 */

/** Converte índice linear d (0–n²-1) para coordenada (x, y) na grade de ordem n. */
export function d2xy(n: number, d: number): { x: number; y: number } {
  let rx: number, ry: number, s: number, t = d
  let x = 0,
    y = 0
  for (s = 1; s < n; s *= 2) {
    rx = 1 & Math.floor(t / 2)
    ry = 1 & (t ^ rx)
    if (ry === 0) {
      if (rx === 1) {
        x = s - 1 - x
        y = s - 1 - y
      }
      const tmp = x
      x = y
      y = tmp
    }
    x += s * rx
    y += s * ry
    t = Math.floor(t / 4)
  }
  return { x, y }
}

/** Cor de fundo para cada bloco /8 segundo categorias IANA. */
export function ianaColor(block: number): string {
  if (block === 0 || block === 127) return '#e2e8f0' // Loopback / This host
  if (block === 10) return '#bbf7d0' // Privado RFC 1918
  if (block === 100) return '#fef9c3' // Shared address space RFC 6598
  if (block === 169) return '#fde68a' // Link-local RFC 3927
  if (block === 172) return '#d1fae5' // Parcialmente privado (172.16-31)
  if (block === 192) return '#d1fae5' // Parcialmente privado (192.168)
  if (block >= 224 && block <= 239) return '#ede9fe' // Multicast Classe D
  if (block >= 240) return '#d1d5db' // Reservado / Experimental Classe E
  return '#bfdbfe' // Público / Alocado / Legado
}

/** Cor IANA como [r, g, b] (0-255). */
export function ianaColorRGB(block: number): [number, number, number] {
  const hex = ianaColor(block)
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return [r, g, b]
}

/** Descrição textual da categoria IANA de um bloco /8. */
export function ianaCategory(block: number): string {
  if (block === 0) return 'Esta rede neste host (RFC 1122)'
  if (block === 10) return 'Privado (RFC 1918)'
  if (block === 100) return 'Espaço compartilhado (RFC 6598)'
  if (block === 127) return 'Loopback'
  if (block === 169) return 'Link-local (RFC 3927)'
  if (block === 172) return 'Parcialmente privado: 172.16.0.0/12 (RFC 1918)'
  if (block === 192) return 'Parcialmente privado: 192.168.0.0/16 (RFC 1918)'
  if (block >= 224 && block <= 239) return 'Multicast (Classe D)'
  if (block >= 240) return 'Reservado / Experimental (Classe E)'
  return 'Público / Alocado / Legado'
}

/**
 * Dado uma lista de prefixos CIDR, retorna o conjunto de blocos /8 que eles cobrem.
 * Exemplo: ['177.0.0.0/8', '200.160.112.0/20'] → Set{177, 200}
 */
export function prefixesToBlocks(prefixes: string[]): Set<number> {
  const blocks = new Set<number>()
  for (const prefix of prefixes) {
    const firstOctet = parseInt(prefix.split('.')[0], 10)
    if (!isNaN(firstOctet) && firstOctet >= 0 && firstOctet <= 255) {
      blocks.add(firstOctet)
    }
  }
  return blocks
}

/** Pré-calcula todas as 256 posições (x, y) na grade 16×16 pela curva de Hilbert. */
export function buildGrid(n = 16): Array<{ block: number; x: number; y: number }> {
  return Array.from({ length: n * n }, (_, i) => ({ block: i, ...d2xy(n, i) }))
}

// ---------------------------------------------------------------------------
// Hilbert /16 — grade 256×256, 65536 blocos
// ---------------------------------------------------------------------------

/** Posições (x, y) pré-calculadas para todos os 65536 blocos /16. */
export const GRID16: ReadonlyArray<{ x: number; y: number }> = Array.from(
  { length: 65536 },
  (_, d) => d2xy(256, d),
)

/**
 * Mapa reverso: posição (y*256 + x) → índice de bloco d.
 * Usado para converter coordenada de mouse em bloco /16.
 */
export const POS_TO_D16: Uint16Array = (() => {
  const map = new Uint16Array(65536)
  for (let d = 0; d < 65536; d++) {
    const { x, y } = GRID16[d]
    map[y * 256 + x] = d
  }
  return map
})()

/**
 * Dado um density array de 65536 valores e uma posição de canvas (mouseX, mouseY),
 * retorna o índice do bloco /16 sob o cursor.
 */
export function mouseToBlock16(mouseX: number, mouseY: number, canvasSize: number): number {
  const cellSize = canvasSize / 256
  const gx = Math.min(255, Math.floor(mouseX / cellSize))
  const gy = Math.min(255, Math.floor(mouseY / cellSize))
  return POS_TO_D16[gy * 256 + gx]
}

/** Converte índice de bloco /16 para string "a.b.0.0/16". */
export function block16ToPrefix(d: number): string {
  const a = (d >> 8) & 0xff
  const b = d & 0xff
  return `${a}.${b}.0.0/16`
}

/** Primeiro octeto (bloco /8) de um índice /16. */
export function block16ToSlash8(d: number): number {
  return (d >> 8) & 0xff
}

/** Converte hex "#rrggbb" para [r, g, b]. */
export function hexToRGB(hex: string): [number, number, number] {
  return [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)]
}

// ---------------------------------------------------------------------------
// IPv6 Hilbert — 6 blocos RIR, granularidade /32
// ---------------------------------------------------------------------------

export interface V6BlockConfig {
  id:          string   // chave no payload da API
  label:       string   // e.g. "2001::/16"
  rir:         string   // e.g. "LACNIC"
  /** Primeiro grupo de 16 bits do endereço base (e.g. 0x2800 para LACNIC) */
  baseG1:      number
  baseLen:     number   // 16 ou 12
  unitLen:     32
  order:       number   // ordem da curva de Hilbert (8 ou 10)
  gridSize:    number   // 256 ou 1024
  totalCells:  number   // 2^(unitLen-baseLen) = 65536 ou 1048576
  /** Pixels físicos do canvas (gridSize*1 para /12, gridSize*2 para legado) */
  canvasPx:    number
}

export const V6_BLOCKS: ReadonlyArray<V6BlockConfig> = [
  { id: 'legacy',  label: '2001::/16', rir: 'Legado',   baseG1: 0x2001, baseLen: 16, unitLen: 32, order: 8,  gridSize: 256,  totalCells: 65536,   canvasPx: 512  },
  { id: 'lacnic',  label: '2800::/12', rir: 'LACNIC',   baseG1: 0x2800, baseLen: 12, unitLen: 32, order: 10, gridSize: 1024, totalCells: 1048576, canvasPx: 1024 },
  { id: 'arin',    label: '2600::/12', rir: 'ARIN',     baseG1: 0x2600, baseLen: 12, unitLen: 32, order: 10, gridSize: 1024, totalCells: 1048576, canvasPx: 1024 },
  { id: 'ripe',    label: '2a00::/12', rir: 'RIPE NCC', baseG1: 0x2a00, baseLen: 12, unitLen: 32, order: 10, gridSize: 1024, totalCells: 1048576, canvasPx: 1024 },
  { id: 'apnic',   label: '2400::/12', rir: 'APNIC',    baseG1: 0x2400, baseLen: 12, unitLen: 32, order: 10, gridSize: 1024, totalCells: 1048576, canvasPx: 1024 },
  { id: 'afrinic', label: '2c00::/12', rir: 'AFRINIC',  baseG1: 0x2c00, baseLen: 12, unitLen: 32, order: 10, gridSize: 1024, totalCells: 1048576, canvasPx: 1024 },
]

// Versão interna de d2xy usando shifts ao invés de Math.floor para melhor
// desempenho no loop de 1M células do grid order-10.
function _d2xy_fast(n: number, d: number): [number, number] {
  let rx: number, ry: number, t = d
  let x = 0, y = 0
  for (let s = 1; s < n; s <<= 1) {
    rx = (t >> 1) & 1
    ry = (t ^ rx) & 1
    if (ry === 0) {
      if (rx === 1) { x = s - 1 - x; y = s - 1 - y }
      const tmp = x; x = y; y = tmp
    }
    x += s * rx
    y += s * ry
    t >>= 2
  }
  return [x, y]
}

// Lazy grid order-10 (1024×1024 = 1M células).
// Uint16Array compacto: 2 MB cada, computado na primeira chamada (~50 ms).
let _grid1024x: Uint16Array | null = null
let _grid1024y: Uint16Array | null = null

export function getGrid1024(): { x: Uint16Array; y: Uint16Array } {
  if (_grid1024x) return { x: _grid1024x, y: _grid1024y! }
  const N = 1024 * 1024
  _grid1024x = new Uint16Array(N)
  _grid1024y = new Uint16Array(N)
  for (let d = 0; d < N; d++) {
    const [gx, gy] = _d2xy_fast(1024, d)
    _grid1024x[d] = gx
    _grid1024y[d] = gy
  }
  return { x: _grid1024x, y: _grid1024y! }
}

// Mapa reverso posição→d para hover no mapa /12 (4 MB, lazy).
let _posToD1024: Uint32Array | null = null

export function getPosToD1024(): Uint32Array {
  if (_posToD1024) return _posToD1024
  const { x, y } = getGrid1024()
  _posToD1024 = new Uint32Array(1024 * 1024)
  for (let d = 0; d < 1024 * 1024; d++) {
    _posToD1024[y[d] * 1024 + x[d]] = d
  }
  return _posToD1024
}

// Cache de buffer de fundo para cada tamanho de canvas (slate-200: #e2e8f0).
const _v6BgCache = new Map<number, Uint8ClampedArray>()
export function getV6BgPixels(canvasPx: number): Uint8ClampedArray {
  let bg = _v6BgCache.get(canvasPx)
  if (!bg) {
    bg = new Uint8ClampedArray(canvasPx * canvasPx * 4)
    for (let i = 0; i < bg.length; i += 4) {
      bg[i] = 226; bg[i + 1] = 232; bg[i + 2] = 240; bg[i + 3] = 255
    }
    _v6BgCache.set(canvasPx, bg)
  }
  return bg
}

/**
 * Converte índice de célula para string de prefixo IPv6 /32.
 * Não usa BigInt — basta aritmética nos primeiros 32 bits do endereço.
 */
export function cellIndexToV6Prefix(cellIdx: number, config: V6BlockConfig): string {
  if (config.baseLen === 16) {
    // Legado 2001::/16: segundo grupo = cellIdx (16 bits)
    return `${config.baseG1.toString(16)}:${cellIdx.toString(16).padStart(4, '0')}::/32`
  }
  // Bloco /12: 4 bits superiores de cellIdx (20 bits) completam o primeiro grupo
  const g1 = (config.baseG1 | (cellIdx >> 16)) & 0xffff
  const g2 = cellIdx & 0xffff
  return `${g1.toString(16)}:${g2.toString(16).padStart(4, '0')}::/32`
}

/** Converte posição de mouse no canvas IPv6 para índice de célula. */
export function mouseToBlockV6(
  mouseX: number, mouseY: number,
  canvasSize: number, config: V6BlockConfig,
): number {
  const cellPx = canvasSize / config.gridSize
  const gx = Math.min(config.gridSize - 1, Math.floor(mouseX / cellPx))
  const gy = Math.min(config.gridSize - 1, Math.floor(mouseY / cellPx))
  if (config.gridSize === 256) {
    return POS_TO_D16[gy * 256 + gx]
  }
  return getPosToD1024()[gy * 1024 + gx]
}

/**
 * Grade /8 para o overlay do mapa Hilbert.
 *
 * Os 256 blocos /8 mapeiam para células de 16×16 na grade 256×256
 * (16² = 256 = blocos /16 por /8). A grade de sobreposição é, portanto,
 * uma grade regular de 16 células. O label de cada célula (sx, sy)
 * é o primeiro octeto do bloco /8 que ocupa aquela super-célula.
 */
export const SLASH8_GRID: ReadonlyArray<{ block: number; sx: number; sy: number }> = (() => {
  const result: { block: number; sx: number; sy: number }[] = []
  for (let sy = 0; sy < 16; sy++) {
    for (let sx = 0; sx < 16; sx++) {
      const block = (POS_TO_D16[(sy * 16) * 256 + (sx * 16)] >> 8) & 0xff
      result.push({ block, sx, sy })
    }
  }
  return result
})()

/**
 * Lookup (sx,sy) → {idx, block} para detecção de clique num /8.
 * Chave: "sx,sy" (e.g. "3,7").
 */
export const SLASH8_POS_MAP: ReadonlyMap<string, { idx: number; block: number }> = new Map(
  SLASH8_GRID.map(({ sx, sy, block }, idx) => [`${sx},${sy}`, { idx, block }]),
)

/** Retorna true se algum bloco /16 dentro do quadrado /8 (sx,sy) tem densidade > 0. */
export function slash8HasData(sx: number, sy: number, density: number[]): boolean {
  for (let dy = 0; dy < 16; dy++) {
    for (let dx = 0; dx < 16; dx++) {
      if (density[POS_TO_D16[(sy * 16 + dy) * 256 + (sx * 16 + dx)]] > 0) return true
    }
  }
  return false
}

/**
 * Buffer de fundo IANA para o canvas 512×512 dos mapas IPv4 (singleton).
 * Cada célula 2×2 pixels recebe a cor da categoria IANA do bloco /8 correspondente.
 */
let _ianaPixels512: Uint8ClampedArray | null = null
export function getIanaPixels512(): Uint8ClampedArray {
  if (_ianaPixels512) return _ianaPixels512
  const canvasPx = 512
  const cell = canvasPx / 256
  const px = new Uint8ClampedArray(canvasPx * canvasPx * 4)
  for (let d = 0; d < 65536; d++) {
    const { x, y } = GRID16[d]
    const [r, g, b] = ianaColorRGB(block16ToSlash8(d))
    for (let cy = 0; cy < cell; cy++) {
      for (let cx = 0; cx < cell; cx++) {
        const idx = ((y * cell + cy) * canvasPx + (x * cell + cx)) * 4
        px[idx] = r; px[idx + 1] = g; px[idx + 2] = b; px[idx + 3] = 255
      }
    }
  }
  _ianaPixels512 = px
  return px
}
