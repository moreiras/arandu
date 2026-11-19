// Critérios de desempenho medidos no navegador: bytes, chamadas, tempo e cache das páginas.
//   BASE_URL=http://<ambiente> XFF=<IP da ALLOWED_IPS> [VISITAS=5] node criterios_fase4.js
// Cada "visitante" é um contexto novo (sem cache do navegador) que visita as páginas de entrada e as de entidade. O 1º aquece o cache do nginx; a
// taxa de acerto e o p95 valem para os visitantes 2..N (regime). Mede a API como chega pelo nginx (cabeçalho X-Cache-Status).
const { chromium } = require('playwright')

const BASE = process.env.BASE_URL || 'http://localhost:18080'
const XFF = process.env.XFF || '203.0.113.129'
const VISITAS = parseInt(process.env.VISITAS || '5', 10)
const wait = (ms) => new Promise((r) => setTimeout(r, ms))
const pct = (xs, p) => { const s = [...xs].sort((a, b) => a - b); return s.length ? s[Math.min(s.length - 1, Math.ceil(p * s.length) - 1)] : null }
const molde = (u) => new URL(u).pathname.replace(/\/api\/v1/, '').replace(/\/\d{4}-\d{2}-\d{2}/g, '/{data}').replace(/\/\d{5,}/g, '/{n}').replace(/\/[0-9a-f]{16,}/g, '/{h}')

;(async () => {
  const browser = await chromium.launch()
  const base = await browser.newContext({ extraHTTPHeaders: { 'X-Forwarded-For': XFF } })
  const get = async (p) => (await base.request.get(BASE + p)).json()
  const asns = (await get('/api/v1/asns?limit=5')).items
  const asn = (asns.find((a) => a.is_br) || asns[0]).asn
  const ixps = (await get('/api/v1/ixps')).ixps
  const scms = (await get('/api/v1/scms?limit=1')).items
  const mun = (await get('/api/v1/acessos/municipios')).items || []
  const cdns = ((await get('/api/v1/cdns/presence')).cdns || []).slice().sort((a, b) => (b.asns || []).length - (a.asns || []).length)
  const slug = (n) => n.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
  const pages = {
    home: '/', ases: '/ases', dados: '/dados', estados: '/estados', fontes: '/fontes', grupos: '/grupos', ixps: '/ixps', operadoras: '/operadoras',
    sobre: '/sobre', visao_geral: '/visao-geral',
    asn: `/asn/${asn}`, ptt: `/ixp/${ixps[0].code}`, operadora: `/operadora/${scms[0].cnpj}`, municipio: `/municipio/${mun[0].codigo_ibge || mun[0].ibge}`,
    uf: `/uf/${ixps[0].uf}`, cdncap: cdns.length ? `/cdncap/${slug(cdns[0].name)}` : null,
  }
  const entrada = new Set(['home', 'ases', 'dados', 'estados', 'fontes', 'grupos', 'ixps', 'operadoras', 'sobre', 'visao_geral'])
  const por = {}
  for (const nome of Object.keys(pages)) por[nome] = { visitas: [] }
  for (let v = 0; v < VISITAS; v++) {
    const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, extraHTTPHeaders: { 'X-Forwarded-For': XFF } })
    for (const [nome, path] of Object.entries(pages)) {
      if (!path) continue
      const page = await ctx.newPage()
      const m = { metodos: {}, chamadas: 0, api: 0, bytes: 0, acertos: 0, erros: 0, tempos: [], rotas: {} }
      const pend = []
      page.on('response', (res) => {
        m.chamadas += 1
        const u = res.url()
        if (res.status() >= 500) m.erros += 1
        pend.push(res.request().sizes().then((s) => { m.bytes += (s.responseBodySize || 0) + (s.responseHeadersSize || 0) }).catch(() => {}))
        if (u.includes('/api/')) {
          m.api += 1
          const st = res.headers()['x-cache-status'] || '-'
          if (st === 'HIT' || st === 'STALE' || st === 'UPDATING') m.acertos += 1
          pend.push(res.finished().then(() => {
            const t = res.request().timing()
            if (t && t.responseEnd >= 0 && t.requestStart >= 0) {
              const ms = t.responseEnd - t.requestStart
              m.tempos.push(ms)
              const r = (por[nome].rota ||= {})[k] ||= { n: 0, hit: 0, ms: [], bytes: 0, metodo: res.request().method() }
              if (v > 0) { r.n += 1; r.hit += st === 'HIT' || st === 'STALE' || st === 'UPDATING' ? 1 : 0; r.ms.push(ms); res.body().then((b) => { r.bytes = Math.max(r.bytes, b.length) }).catch(() => {}) }
            }
          }).catch(() => {}))
          var k = molde(u); m.rotas[k] = (m.rotas[k] || 0) + 1
        }
      })
      await page.goto(BASE + path, { waitUntil: 'networkidle', timeout: 90000 }).catch(() => {})
      await wait(1000)
      await Promise.all(pend)
      por[nome].visitas.push(m)
      await page.close()
    }
    await ctx.close()
  }
  await browser.close()
  const out = {}
  let hitT = 0, apiT = 0, hitR = 0, apiR = 0
  const tEntrada = []
  for (const [nome, d] of Object.entries(por)) {
    const reg = d.visitas.slice(1)
    if (!reg.length) continue
    const soma = (f) => reg.reduce((a, x) => a + f(x), 0)
    const tempos = reg.flatMap((x) => x.tempos)
    out[nome] = {
      chamadas: Math.round(soma((x) => x.chamadas) / reg.length), api: Math.round(soma((x) => x.api) / reg.length),
      kib: Math.round(soma((x) => x.bytes) / reg.length / 1024), hit_pct: Math.round(100 * soma((x) => x.acertos) / Math.max(1, soma((x) => x.api))),
      p95_ms: Math.round(pct(tempos, 0.95)), erros_5xx: soma((x) => x.erros), rotas: Object.keys(reg[0].rotas).sort(),
    }
    hitR += soma((x) => x.acertos); apiR += soma((x) => x.api)
    if (entrada.has(nome)) tEntrada.push(...tempos)
    hitT += d.visitas.reduce((a, x) => a + x.acertos, 0); apiT += d.visitas.reduce((a, x) => a + x.api, 0)
  }
  for (const [nome, d] of Object.entries(por)) if (out[nome]) out[nome].rota = Object.fromEntries(Object.entries(d.rota || {}).map(([k, r]) => [k, { metodo: r.metodo, n: r.n, hit_pct: Math.round(100 * r.hit / Math.max(1, r.n)), p95_ms: Math.round(pct(r.ms, 0.95)), kib: Math.round(r.bytes / 1024) }]))
  console.log(JSON.stringify({ visitas: VISITAS, regime_hit_pct: +(100 * hitR / apiR).toFixed(1), todas_hit_pct: +(100 * hitT / apiT).toFixed(1),
    entrada_p95_ms: Math.round(pct(tEntrada, 0.95)), entrada_p50_ms: Math.round(pct(tEntrada, 0.5)), paginas: out }, null, 1))
})()
