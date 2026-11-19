// Segunda visita à mesma página: com `?date=` imutável e camadas por hash, o que vem da REDE na
// segunda visita deve ser (quase) só o HTML. Mede via CDP o que NÃO foi servido do cache do navegador.
//   BASE_URL=http://<ambiente> XFF=<IP da ALLOWED_IPS> node segunda_visita.js [--max-api-bytes N]
// Sai com código 1 se a 2ª visita baixar mais de N bytes de GET em /api/ (padrão 20 KiB) ou qualquer camada estática.
// Limite conhecido: resposta GET acima do que o cache em memória do navegador de teste guarda (dezenas de MB) baixa de novo.
const { chromium } = require('playwright')

const BASE = process.env.BASE_URL || 'http://localhost:18080'
// IP de origem (X-Forwarded-For). Use um IP da ALLOWED_IPS do ambiente: fora dela cada execução gasta o orçamento de navegação anônima e,
// depois de algumas, as páginas avançadas passam a ser barradas (o teste falharia sem ser bug).
const XFF = process.env.XFF || '203.0.113.129'
const MAX_API = Number((process.argv.find((a) => a.startsWith('--max-api-bytes=')) || '=20480').split('=')[1])
const REVALIDACAO = 2048
// Resposta GET maior que isto não conta como falha: o cache do navegador (em memória, no Chromium de teste) pode não guardá-la, e o
// peso da rota é outro assunto. Fica listada como AVISO.
const GRANDE = 8 * 1024 * 1024
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

async function visita(ctx, path, acao) {
  const page = await ctx.newPage()
  const cdp = await ctx.newCDPSession(page)
  await cdp.send('Network.enable')
  // O MapLibre busca o GeoJSON num Web Worker, invisível para a sessão CDP da página: as camadas vêm dos eventos do contexto.
  const camadas = []
  const aoTerminar = async (r) => {
    if (!/\/api\/v1\/map\/(submarine|terrestrial|power)/.test(r.url())) return
    const sz = await r.sizes().catch(() => ({ responseBodySize: 0, responseHeadersSize: 0 }))
    camadas.push({ url: new URL(r.url()).pathname + new URL(r.url()).search, // o Playwright dá o corpo como transferido − cabeçalhos: acerto de cache vem negativo; corpo + cabeçalhos = tráfego real (0 no cache)
      bytes: Math.max(0, sz.responseBodySize + sz.responseHeadersSize) })
  }
  ctx.on('requestfinished', aoTerminar)
  const reqs = new Map()
  cdp.on('Network.requestWillBeSent', (e) => reqs.set(e.requestId, { url: e.request.url, method: e.request.method, cache: false, bytes: 0 }))
  cdp.on('Network.requestServedFromCache', (e) => { const r = reqs.get(e.requestId); if (r) r.cache = true })
  const pendentes = new Set()
  let ultima = Date.now()
  cdp.on('Network.requestWillBeSent', (e) => { pendentes.add(e.requestId); ultima = Date.now() })
  cdp.on('Network.loadingFailed', (e) => pendentes.delete(e.requestId))
  cdp.on('Network.loadingFinished', (e) => { pendentes.delete(e.requestId); const r = reqs.get(e.requestId); if (r) r.bytes = e.encodedDataLength })
  await page.goto(BASE + path, { waitUntil: 'networkidle', timeout: 90000 }).catch(() => {})
  const assentou = async () => { for (let i = 0; i < 180 && (pendentes.size > 0 || Date.now() - ultima < 3000); i++) await wait(500) }
  await assentou()
  if (acao) {
    await acao(page)
    await assentou()
  }
  // Fechar com resposta em andamento (ex.: 29 MB num nginx frio) aborta o download e nada vai ao cache do navegador.
  for (let i = 0; i < 120 && pendentes.size > 0; i++) await wait(500)
  if (process.env.DEPURAR) console.log('  [urls]', [...reqs.values()].filter((r) => r.url.includes('/api/')).map((r) => r.method + ' ' + r.url.replace(/^https?:\/\/[^/]+/, '') + ' ' + r.bytes).join(' | '))
  ctx.off('requestfinished', aoTerminar)
  await page.close()
  // POST (consultas do /query) nunca vão ao cache do navegador: contados à parte. Revalidação 304 (< REVALIDACAO B, ex.: /snapshots,
  // /map/layers, que não levam `date`) também é esperada e não conta.
  const out = { api: { n: 0, bytes: 0, post: 0, postBytes: 0, reval: 0 }, camadas: { n: camadas.length, bytes: camadas.reduce((a, c) => a + c.bytes, 0), urls: camadas.map((c) => c.url) }, lista: [], avisos: [] }
  for (const r of reqs.values()) {
    const u = new URL(r.url)
    if (!u.pathname.startsWith('/api/')) continue
    if (r.method !== 'GET') { out.api.post++; out.api.postBytes += r.bytes; continue }
    if (r.bytes > 0 && r.bytes < REVALIDACAO) { out.api.reval++; continue }
    const rede = r.bytes > 0
    if (rede && r.bytes > GRANDE) { out.avisos.push(`${u.pathname}${u.search.slice(0, 40)} ${r.bytes}`); continue }
    out.api.n++
    if (rede) out.api.bytes += r.bytes
    if (rede) out.lista.push(`${u.pathname}${u.search.slice(0, 40)} ${r.bytes}`)
  }
  return out
}

;(async () => {
  // WebGL por software: sem ele o MapLibre não inicia no Chromium headless e as camadas nunca são pedidas.
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] })
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, extraHTTPHeaders: { 'X-Forwarded-For': XFF } })
  const id = await (await ctx.request.get(BASE + '/api/v1/ixps')).json()
  const code = id.ixps[0].code
  const asns = (await (await ctx.request.get(BASE + '/api/v1/asns?limit=5')).json()).items
  const asn = (asns.find((a) => a.is_br) || asns[0]).asn
  const paginas = { home: '/', ptt: `/ixp/${code}`, asn: `/asn/${asn}`, mapa: '/mapa' }
  let falha = false
  for (const [nome, path] of Object.entries(paginas)) {
    const p1 = await visita(ctx, path)
    const p2 = await visita(ctx, path)
    const ok = p2.api.bytes <= MAX_API && p2.camadas.bytes === 0
    if (!ok) falha = true
    console.log(`${ok ? 'ok   ' : 'FALHA'} ${nome.padEnd(5)} 1ª: ${p1.api.n} GET, ${p1.api.bytes} B | 2ª: ${p2.api.n} GET, ${p2.api.bytes} B da rede, ${p2.api.reval} revalidações 304, ${p2.api.post} POST (${p2.api.postBytes} B), camadas ${p2.camadas.bytes} B`)
    for (const l of p2.lista.slice(0, 6)) console.log(`        rede na 2ª: ${l}`)
    for (const l of p2.avisos) console.log(`        AVISO resposta > 8 MiB baixada de novo (fora do critério): ${l}`)
  }
  // Camadas de infraestrutura ligadas pelo usuário (o MapLibre só as busca quando visíveis): a URL tem de ser a versionada
  // (`?v=<16 hex>`, sem data), e a 2ª visita não pode baixá-las de novo.
  // O MapLibre busca as fontes ao carregar; ligar as camadas garante que também as visíveis foram pedidas.
  const ligar = async (page) => {
    for (const r of ['Cabos submarinos', 'Enlaces terrestres (ITU)', 'Linhas de transmissão (ANEEL)']) {
      await page.getByText(r, { exact: true }).first().click({ timeout: 15000 }).catch(() => console.log(`  (não achei o controle "${r}")`))
    }
  }
  // Contexto novo: o cache do navegador é por contexto; sem isso a 1ª visita já viria do cache dos casos anteriores.
  const ctx2 = await browser.newContext({ viewport: { width: 1400, height: 900 }, extraHTTPHeaders: { 'X-Forwarded-For': XFF } })
  const c1 = await visita(ctx2, '/mapa', ligar)
  const c2 = await visita(ctx2, '/mapa', ligar)
  const versionadas = c1.camadas.urls.length > 0 && c1.camadas.urls.every((u) => /[?&]v=[0-9a-f]{16}$/.test(u) && !u.includes('date='))
  const okCamadas = versionadas && c1.camadas.bytes > 0 && c2.camadas.bytes === 0
  if (!okCamadas) falha = true
  console.log(`${okCamadas ? 'ok   ' : 'FALHA'} mapa+camadas 1ª: ${c1.camadas.n} camadas, ${c1.camadas.bytes} B | 2ª: ${c2.camadas.n} camadas, ${c2.camadas.bytes} B | URLs versionadas: ${versionadas}`)
  for (const u of c1.camadas.urls) console.log(`        ${u}`)
  await browser.close()
  process.exit(falha ? 1 : 0)
})()
