// Diagnóstico dos erros de console por página: lista cada mensagem de erro, a URL que falhou e o status.
//   BASE_URL=http://host.docker.internal:18080 node console.js [--amostra N]
// --amostra N: além das páginas fixas, visita N entidades de cada tipo (ASNs BR e não-BR, operadoras, municípios, PTTs) escolhidas por
// semente fixa na lista do snapshot — é onde aparecem os 404 "esperados" (entidade sem aquele serviço).
// Mesmas páginas e mesmo contexto (IP da allowlist) do smoke.js. Sai com código 1 se alguma página tiver erro de console ou de página
// (meta: zero). Mensagens repetidas são agrupadas.
// IGNORAR_TILES=1: o nginx do E2E local não tem o basemap (data/tiles) nem as fontes; os 404 de /tiles/ e o erro do PMTiles que
// vem deles não são bug. Em ambiente real (ambiente de teste) rode sem a variável.
const { chromium } = require('playwright')

const BASE = process.env.BASE_URL || 'http://localhost:18080'
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

async function ids(ctx) {
  const get = async (p) => (await ctx.request.get(BASE + p)).json()
  const asns = (await get('/api/v1/asns?limit=5')).items
  const asn = (asns.find((a) => a.is_br) || asns[0]).asn
  const ixps = (await get('/api/v1/ixps')).ixps
  const scms = (await get('/api/v1/scms?limit=1')).items
  const mun = (await get('/api/v1/acessos/municipios')).items || []
  return {
    asn, code: ixps[0].code, cnpj: scms.length ? scms[0].cnpj : '00000000000191', uf: ixps[0].uf,
    prefixo: (await get('/api/v1/prefixes?limit=1')).items[0].prefix,
    ibge: mun.length ? String(mun[0].codigo_ibge || mun[0].ibge) : '3550308',
    ...(await instalacoes(get)),
  }
}

// uma instalação (a com mais redes), um ASN que está nela e um PTT externo; sem o produto publicado, essas páginas ficam de fora
async function instalacoes(get) {
  try {
    const f = (await get('/api/v1/facilities?limit=1')).items[0]
    const det = await get(`/api/v1/facilities/${f.id}`)
    const ext = ((await get('/api/v1/external-ixps')).ixps || [])[0]
    return { fac: f.id, asnFac: (det.redes.find((r) => r.is_br) || det.redes[0]).asn, extCode: ext ? ext.code : null }
  } catch (e) { return {} }
}

;(async () => {
  const browser = await chromium.launch()
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, extraHTTPHeaders: { 'X-Forwarded-For': '203.0.113.129' } })
  const id = await ids(ctx)
  const pages = {
    home: '/', explorar: '/explorar', fontes: '/fontes', dados: '/dados', dashboard: '/panorama/tecnico', asn: `/asn/${id.asn}`, ptt: `/ixp/${id.code}`,
    operadora: `/operadora/${id.cnpj}`, municipio: `/municipio/${id.ibge}`, uf: `/uf/${id.uf}`, prefixo: `/prefixo/${id.prefixo}`, mapa: '/mapa',
    ...(id.fac ? { instalacoes: '/instalacoes', instalacao: `/instalacao/${id.fac}`, asn_instalacoes: `/asn/${id.asnFac}`, ...(id.extCode ? { ptt_externo: `/ixp-externo/${id.extCode}` } : {}) } : {}),
    bgp: '/bgp', estatisticas: '/panorama/mercado', panorama_ipv6: '/panorama/ipv6', mudancas: '/mudancas', uso_da_internet: '/uso-da-internet', rankings: '/rankings', communities: '/communities', comparar_datas: '/comparar?modo=datas', operadoras: '/operadoras?servico=scm', localizador: '/localizador', estados: '/estados', mercado_ipv4: '/mercado-ipv4', regulatorio: '/regulatorio', seguranca_roteamento: '/seguranca-de-roteamento', regulatorio_multas: '/regulatorio?aba=multas', regulatorio_espectro: '/regulatorio?aba=espectro', regulatorio_satelites: '/regulatorio?aba=satelites', snapshots: '/snapshots',
    bgp: '/bgp', estatisticas: '/panorama/mercado', panorama_ipv6: '/panorama/ipv6', mudancas: '/mudancas', uso_da_internet: '/uso-da-internet', rankings: '/rankings', comparar_datas: '/comparar?modo=datas', operadoras: '/operadoras?servico=scm', localizador: '/localizador', estados: '/estados', mercado_ipv4: '/mercado-ipv4', regulatorio: '/regulatorio', seguranca_roteamento: '/seguranca-de-roteamento', regulatorio_multas: '/regulatorio?aba=multas', regulatorio_espectro: '/regulatorio?aba=espectro', regulatorio_satelites: '/regulatorio?aba=satelites', qualidade: '/qualidade', qualidade_reclamacoes: '/qualidade?aba=reclamacoes', snapshots: '/snapshots',
  }
  const iN = process.argv.indexOf('--amostra')
  const N = iN > 0 ? parseInt(process.argv[iN + 1], 10) : 0
  if (N > 0) {
    const get = async (p) => (await ctx.request.get(BASE + p)).json()
    const pick = (arr, n) => { const out = []; for (let i = 0; i < arr.length && out.length < n; i += Math.max(1, Math.floor(arr.length / n))) out.push(arr[i]); return out }
    const asns = (await get('/api/v1/asns?limit=1000')).items
    pick(asns.filter((a) => a.is_br), N).forEach((a) => { pages[`asn-br-${a.asn}`] = `/asn/${a.asn}` })
    pick(asns.filter((a) => !a.is_br), N).forEach((a) => { pages[`asn-fora-${a.asn}`] = `/asn/${a.asn}` })
    pick((await get('/api/v1/scms?limit=200')).items, N).forEach((o) => { pages[`operadora-scm-${o.cnpj}`] = `/operadora/${o.cnpj}` })
    const smps = await get('/api/v1/smps?limit=200').catch(() => ({ items: [] }))
    pick(smps.items || [], N).forEach((o) => { pages[`operadora-smp-${o.cnpj}`] = `/operadora/${o.cnpj}` })
    const muns = (await get('/api/v1/acessos/municipios')).items || []
    pick(muns, N).forEach((m) => { const c = String(m.codigo_ibge || m.ibge); pages[`municipio-${c}`] = `/municipio/${c}` })
    pick((await get('/api/v1/ixps')).ixps, N).forEach((x) => { pages[`ptt-${x.code}`] = `/ixp/${x.code}` })
  }
  let total = 0
  let seq = 0
  for (const [name, path] of Object.entries(pages)) {
    // um visitante novo por página: sem cookie a identidade é a impressão digital (UA e cabeçalhos), então cada página leva um UA
    // próprio; com a mesma identidade o orçamento de uso anônimo (que persiste entre execuções) esgota e o 403 vira "erro"
    seq += 1
    const ua = `Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/131.0.6778.33 Safari/537.36 console-${Date.now()}-${seq}`
    const ctxPag = await browser.newContext({ viewport: { width: 1400, height: 900 }, userAgent: ua, extraHTTPHeaders: { 'X-Forwarded-For': '203.0.113.129' } })
    const page = await ctxPag.newPage()
    const erros = new Map()
    const falhas = new Map()
    const add = (m, k) => m.set(k, (m.get(k) || 0) + 1)
    const tiles = (t) => process.env.IGNORAR_TILES === '1' && (t.includes('/tiles/') || t.includes('Bad response code: 404') || t.includes('ExplorerMap runtime error'))
    page.on('console', (msg) => { if (msg.type() === 'error' && !tiles(msg.text() + (msg.location().url || ''))) add(erros, msg.text().slice(0, 220) + (msg.location().url ? `  @ ${msg.location().url.slice(0, 120)}` : '')) })
    page.on('pageerror', (e) => add(erros, 'pageerror: ' + String(e.message).slice(0, 220)))
    page.on('response', (res) => { if (res.status() >= 400 && !tiles(res.url())) add(falhas, `${res.status()} ${res.url().replace(BASE, '').slice(0, 140)}`) })
    page.on('requestfailed', (req) => { const e = req.failure() && req.failure().errorText; if (e !== 'net::ERR_ABORTED') add(falhas, `FALHOU ${req.url().replace(BASE, '').slice(0, 140)} (${e})`) })
    await page.goto(BASE + path, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {})
    await wait(1500)
    const n = [...erros.values()].reduce((a, b) => a + b, 0)
    total += n
    console.log(`${n ? 'ERRO' : 'ok  '} ${name} ${path}: ${n} erro(s) de console`)
    for (const [k, v] of erros) console.log(`      console ×${v}: ${k}`)
    for (const [k, v] of falhas) console.log(`      rede    ×${v}: ${k}`)
    await page.close()
    await ctxPag.close()
  }
  await browser.close()
  console.log(total ? `TOTAL: ${total} erro(s) de console` : 'ZERO erros de console')
  process.exit(total ? 1 : 0)
})()
