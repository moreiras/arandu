// Fumaça das 8 páginas principais + orçamento de requisições e bytes (T6) + largura a 390 px.
//   BASE_URL=http://host.docker.internal:18080 node smoke.js [--update]
// Visita Dashboard, ASN, PTT, operadora, município, mapa, BGP e estatísticas como IP da allowlist (sem
// limite de orçamento de navegação), conta chamadas e bytes por página e compara com
// tests/contracts/page_budget.json (montado em /contracts). `--update` regrava a baseline.
const { chromium } = require('playwright')
const fs = require('fs')

const BASE = process.env.BASE_URL || 'http://localhost:18080'
const BUDGET_FILE = process.env.BUDGET_FILE || '/contracts/page_budget.json'
const UPDATE = process.argv.includes('--update')
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

async function ids(ctx) {
  const get = async (p) => (await ctx.request.get(BASE + p)).json()
  const asns = (await get('/api/v1/asns?limit=5')).items
  const asn = (asns.find((a) => a.is_br) || asns[0]).asn
  const ixps = (await get('/api/v1/ixps')).ixps
  const scms = (await get('/api/v1/scms?limit=1')).items
  const mun = (await get('/api/v1/acessos/municipios')).items || []
  return {
    asn, asn2: (asns.find((a) => a.is_br && a.asn !== asn) || asns[1] || asns[0]).asn, code: ixps[0].code,
    cnpj: scms.length ? scms[0].cnpj : '00000000000191',
    uf: ixps[0].uf,
    prefixo: (await get('/api/v1/prefixes?limit=1')).items[0].prefix,
    // grupo com mais de uma empresa; sem ele, a página do grupo fica fora da fumaça
    grupo: ((await get('/api/v1/grupos')).grupos || []).find((g) => g.tamanho >= 2)?.grupo_id || null,
    ibge: mun.length ? String(mun[0].codigo_ibge || mun[0].ibge) : '3550308',
    // CDN/CAP com mais ASNs (o pior caso) e seu slug, igual a `cdnSlug` do frontend
    cdn: await (async () => {
      const cdns = ((await get('/api/v1/cdns/presence')).cdns || []).slice().sort((a, b) => (b.asns || []).length - (a.asns || []).length)
      return cdns.length ? cdns[0].name.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') : null
    })(),
  }
}

;(async () => {
  const browser = await chromium.launch()
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, extraHTTPHeaders: { 'X-Forwarded-For': '203.0.113.129' } })
  const id = await ids(ctx)
  const pages = {
    home: '/', explorar: '/explorar', fontes: '/fontes', estados: '/estados', dados: '/dados', dashboard: '/panorama/tecnico', asn: `/asn/${id.asn}`, ptt: `/ixp/${id.code}`, operadora: `/operadora/${id.cnpj}`,
    municipio: `/municipio/${id.ibge}`, uf: `/uf/${id.uf}`, prefixo: `/prefixo/${id.prefixo}`, mapa: '/mapa', bgp: '/bgp', estatisticas: '/panorama/mercado', panorama_tecnico_ipv6: '/panorama/tecnico?aba=ipv6', mudancas: '/mudancas', uso_da_internet: '/uso-da-internet', qualidade: '/qualidade', regulatorio: '/regulatorio', seguranca_roteamento: '/seguranca-de-roteamento', mercado_ipv4: '/mercado-ipv4', rankings: '/rankings', municipios: '/municipios', communities: '/communities', ases: '/ases',
    comparar_asn: `/comparar?tipo=asn&ids=${id.asn},${id.asn2}`, relatorio_asn: `/relatorio/asn/${id.asn}`, panorama_mercado_concentracao: '/panorama/mercado?aba=concentracao', operadoras_ranking: '/operadoras?visao=ranking', panorama_mercado_maiores: '/panorama/mercado?aba=maiores',
    ...(id.grupo ? { grupo: `/grupo/${encodeURIComponent(id.grupo)}` } : {}),
    ...(id.cdn ? { cdncap: `/cdncap/${id.cdn}` } : {}),
  }
  const result = {}
  for (const [name, path] of Object.entries(pages)) {
    const page = await ctx.newPage()
    const m = { chamadas: 0, api: 0, bytes: 0, erros_5xx: 0, erros_console: 0, erros_pagina: 0 }
    const pending = []
    page.on('response', (res) => {
      m.chamadas += 1
      if (res.url().includes('/api/') || res.url().includes('/health')) m.api += 1
      if (res.status() >= 500) m.erros_5xx += 1
      pending.push(res.request().sizes().then((s) => { m.bytes += (s.responseBodySize || 0) + (s.responseHeadersSize || 0) }).catch(() => {}))
    })
    page.on('console', (msg) => { if (msg.type() === 'error') m.erros_console += 1 })
    page.on('pageerror', () => { m.erros_pagina += 1 })
    await page.goto(BASE + path, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {})
    await wait(1500)
    await Promise.all(pending)
    m.mostra_erro_na_tela = await page.getByText(/Erro ao carregar|Something went wrong|HTTP 5\d\d/i).first().isVisible().catch(() => false)
    result[name] = m
    await page.close()
  }
  // Celular: a página não pode rolar na horizontal a 390 px (largura do documento = largura da tela).
  // Com `isMobile` o viewport do layout cresce junto com o conteúdo; por isso compara-se scrollWidth com 390 e não com innerWidth.
  const LARGURA_CELULAR = 390
  const rolagem = {}
  const mctx = await browser.newContext({ viewport: { width: LARGURA_CELULAR, height: 844 }, isMobile: true, hasTouch: true, extraHTTPHeaders: { 'X-Forwarded-For': '203.0.113.129' } })
  for (const [name, path] of Object.entries(pages)) {
    const page = await mctx.newPage()
    await page.goto(BASE + path, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {})
    await page.waitForSelector('main section, main h1, main table', { timeout: 10000 }).catch(() => {})   // conteúdo da página, não só a casca
    await wait(3000)
    rolagem[name] = await page.evaluate(() => document.documentElement.scrollWidth).catch(() => 0)
    await page.close()
  }
  await mctx.close()
  await browser.close()

  if (UPDATE) {
    fs.writeFileSync(BUDGET_FILE, JSON.stringify({ _doc: 'Baseline de requisições e bytes por página (smoke.js --update). Orçamento = baseline + tolerância.', paginas: result }, null, 1) + '\n')
    console.log('baseline gravada em', BUDGET_FILE)
    console.table(result)
    process.exit(0)
  }
  const base = JSON.parse(fs.readFileSync(BUDGET_FILE, 'utf8')).paginas
  let fails = 0
  for (const [name, m] of Object.entries(result)) {
    const b = base[name]
    const problems = []
    if (!b) problems.push('sem baseline')
    else {
      if (m.chamadas > b.chamadas + Math.max(5, Math.ceil(b.chamadas * 0.25))) problems.push(`chamadas ${m.chamadas} > baseline ${b.chamadas}`)
      if (m.api > b.api + Math.max(3, Math.ceil(b.api * 0.25))) problems.push(`chamadas à API ${m.api} > baseline ${b.api}`)
      if (m.bytes > b.bytes * 1.3 + 50000) problems.push(`bytes ${m.bytes} > baseline ${b.bytes}`)
      if (m.erros_pagina > b.erros_pagina) problems.push(`erros de página ${m.erros_pagina} > ${b.erros_pagina}`)
    }
    if (m.erros_5xx) problems.push(`${m.erros_5xx} resposta(s) 5xx`)
    if (m.mostra_erro_na_tela) problems.push('mostra erro cru na tela')
    console.log(`${problems.length ? 'FAIL' : 'ok  '} - ${name}: ${m.chamadas} chamadas (${m.api} API), ${(m.bytes / 1024).toFixed(0)} KiB` + (problems.length ? ' → ' + problems.join('; ') : ''))
    if (problems.length) fails += 1
  }
  for (const [name, w] of Object.entries(rolagem)) {
    const estoura = w > LARGURA_CELULAR
    console.log(`${estoura ? 'FAIL' : 'ok  '} - ${name} (celular ${LARGURA_CELULAR} px): largura do documento ${w} px` + (estoura ? ' → rolagem horizontal' : ''))
    if (estoura) fails += 1
  }
  console.log(fails ? `HÁ ${fails} PÁGINA(S) FORA DO ORÇAMENTO` : 'TODAS AS PÁGINAS DENTRO DO ORÇAMENTO')
  process.exit(fails ? 1 : 0)
})()
