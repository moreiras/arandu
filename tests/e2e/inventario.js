// Inventário de conteúdo das páginas de entidade: o que cada página MOSTRA hoje — títulos, rótulos de métricas,
// colunas de tabela e botões. Serve de lista de conferência da migração para blocos: nada que estava lá pode sumir.
//   BASE_URL=http://host.docker.internal:18080 node inventario.js [--update]
// Sem --update compara com tests/contracts/page_inventory.json: todo item da baseline tem de continuar na página (itens novos são ok).
const { chromium } = require('playwright')
const fs = require('fs')

const BASE = process.env.BASE_URL || 'http://localhost:18080'
const FILE = process.env.INVENTORY_FILE || '/contracts/page_inventory.json'
const UPDATE = process.argv.includes('--update')
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

async function ids(ctx) {
  const get = async (p) => (await ctx.request.get(BASE + p)).json()
  const asns = (await get('/api/v1/asns?limit=50')).items
  const br = asns.filter((a) => a.is_br)
  const ixps = (await get('/api/v1/ixps')).ixps
  const mun = (await get('/api/v1/acessos/municipios?limit=1')).items
  const scms = (await get('/api/v1/scms?limit=1')).items
  return {
    asnBR: (br[0] || asns[0]).asn,
    asnOutro: (asns.find((a) => !a.is_br) || asns[asns.length - 1]).asn,
    code: ixps[0].code,
    cnpj: scms.length ? scms[0].cnpj : '00000000000191',
    ibge: mun.length ? String(mun[0].ibge) : '3550308',
    uf: ixps[0].uf,
  }
}

async function coletar(page) {
  return page.evaluate(() => {
    const txt = (el) => (el.textContent || '').replace(/\s+/g, ' ').trim()
    const uniq = (a) => [...new Set(a.filter(Boolean))]
    const main = document.querySelector('main') || document.body
    const blocos = [...main.querySelectorAll('section[id^="bloco-"]')]
    return {
      _blocos: blocos.length,
      _blocosSemProveniencia: blocos.filter((b) => !b.querySelector('[data-testid="proveniencia"]')).map((b) => b.id),
      titulos: uniq([...main.querySelectorAll('h1,h2,h3')].map(txt)),
      rotulos: uniq([...main.querySelectorAll('.text-xs.text-gray-500, dt')].map(txt).filter((t) => t.length < 60)),
      colunas: uniq([...main.querySelectorAll('th')].map(txt)),
      botoes: uniq([...main.querySelectorAll('button')].map((b) => txt(b) || b.getAttribute('aria-label') || '').filter((t) => t.length < 60)),
    }
  })
}

;(async () => {
  const browser = await chromium.launch()
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, extraHTTPHeaders: { 'X-Forwarded-For': '203.0.113.129' } })
  const id = await ids(ctx)
  const pages = { asn_br: `/asn/${id.asnBR}`, asn_outro: `/asn/${id.asnOutro}`, ptt: `/ixp/${id.code}`, operadora: `/operadora/${id.cnpj}`, municipio: `/municipio/${id.ibge}` }
  const result = {}
  for (const [name, path] of Object.entries(pages)) {
    const page = await ctx.newPage()
    await page.goto(BASE + path, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {})
    await wait(2500)
    // Páginas com abas (AS em 6 abas, operadora em 7, PTT com abas): o conteúdo de cada aba só existe no DOM quando ela está aberta.
    // O inventário é a união das abas; sem isso cada bloco que mudou de aba aparecia como "sumido".
    const r = await coletar(page)
    const abas = await page.locator('main [role="tab"]').count()
    for (let i = 0; i < abas; i++) {
      await page.locator('main [role="tab"]').nth(i).click({ timeout: 10000 }).catch(() => {})
      await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {})
      await wait(800)
      const a = await coletar(page)
      for (const k of Object.keys(r)) {
        if (Array.isArray(r[k]) && k !== '_blocosSemProveniencia') r[k] = [...new Set([...r[k], ...a[k]])]
        else if (k === '_blocosSemProveniencia') r[k] = [...new Set([...r[k], ...a[k]])]
        else if (typeof r[k] === 'number') r[k] = Math.max(r[k], a[k])
      }
    }
    r._abas = abas
    result[name] = r
    await page.close()
  }
  await browser.close()
  if (UPDATE) {
    const limpo = Object.fromEntries(Object.entries(result).map(([n, r]) => [n, Object.fromEntries(Object.entries(r).filter(([k]) => !k.startsWith('_')))]))
    fs.writeFileSync(FILE, JSON.stringify({ _doc: 'Inventário de conteúdo das páginas (inventario.js --update): lista de conferência da migração para blocos.', paginas: limpo }, null, 1) + '\n')
    for (const [n, r] of Object.entries(result)) console.log(n, Object.entries(r).map(([k, v]) => `${k}=${v.length}`).join(' '))
    process.exit(0)
  }
  const base = JSON.parse(fs.readFileSync(FILE, 'utf8')).paginas
  let fails = 0
  for (const [name, atual] of Object.entries(result)) {
    const faltam = []
    // contagens dentro de um título ("Pontos de Atenção … 3 aviso1 info") dependem dos dados, não do conteúdo da página
    const norm = (t) => t.replace(/(\d+ (crítico|aviso|info))+$/i, '').trim()
    const tem = (tipo) => new Set((atual[tipo] || []).map(norm))
    for (const [tipo, itens] of Object.entries(base[name] || {}).filter(([k]) => !k.startsWith('_'))) { const h = tem(tipo); for (const t of itens) if (!h.has(norm(t))) faltam.push(`${tipo}: "${t}"`) }
    if (atual._blocosSemProveniencia.length) faltam.push(`blocos sem proveniência: ${atual._blocosSemProveniencia.join(', ')}`)
    if (atual._blocos) console.log(`     ${name}: ${atual._blocos} blocos, todos com proveniência`)
    console.log(`${faltam.length ? 'FAIL' : 'ok  '} - ${name}` + (faltam.length ? ` → faltam ${faltam.length}: ${faltam.slice(0, 8).join(' | ')}` : ''))
    if (faltam.length) fails += 1
  }
  process.exit(fails ? 1 : 0)
})()
