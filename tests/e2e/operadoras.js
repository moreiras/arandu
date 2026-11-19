// Páginas de outorga por serviço: contagens, estatísticas e colunas de /scms, /smps, /stfcs e /seacs.
//   BASE_URL=http://host.docker.internal:18080 node operadoras.js [--update]
// A baseline (tests/contracts/operadoras_paridade.json) tem as QUATRO páginas por serviço (/scms, /smps, /stfcs, /seacs);
// essas URLs redirecionam para /operadoras e o resultado tem de ser igual (contagens, estatísticas, colunas e primeira linha).
const { chromium } = require('playwright')
const fs = require('fs')

const BASE = process.env.BASE_URL || 'http://localhost:18080'
const FILE = process.env.PARIDADE_FILE || '/contracts/operadoras_paridade.json'
const UPDATE = process.argv.includes('--update')
const wait = (ms) => new Promise((r) => setTimeout(r, ms))
const ROTAS = { scm: '/scms', smp: '/smps', stfc: '/stfcs', seac: '/seacs' }

async function coletar(page) {
  return page.evaluate(() => {
    const txt = (el) => (el.textContent || '').replace(/\s+/g, ' ').trim()
    const main = document.querySelector('main') || document.body
    const cards = [...main.querySelectorAll('.text-xs.text-gray-500')].filter((e) => e.nextElementSibling && /text-xl/.test(e.nextElementSibling.className))
    const stats = Object.fromEntries(cards.map((e) => [txt(e), txt(e.nextElementSibling)]))
    const resultados = [...main.querySelectorAll('span')].map(txt).find((t) => /^[\d.]+ resultados?$/.test(t)) || null
    const pagina = [...main.querySelectorAll('span')].map(txt).find((t) => /^Página \d+ de \d+/.test(t)) || null
    const colunas = [...main.querySelectorAll('thead th')].map(txt)
    const linha1 = [...(main.querySelector('tbody tr')?.querySelectorAll('td') || [])].map(txt)
    const filtros = [...main.querySelectorAll('label')].map(txt)
    return { stats, resultados, pagina, colunas, linha1, filtros, titulo: txt(main.querySelector('h1') || main) }
  })
}

;(async () => {
  const browser = await chromium.launch()
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, extraHTTPHeaders: { 'X-Forwarded-For': '203.0.113.129' } })
  const result = {}
  for (const [serv, rota] of Object.entries(ROTAS)) {
    const page = await ctx.newPage()
    await page.goto(BASE + rota, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {})
    await wait(2500)
    result[serv] = await coletar(page)
    await page.close()
  }
  await browser.close()
  if (UPDATE) {
    fs.writeFileSync(FILE, JSON.stringify({ _doc: 'Paridade das páginas de outorga por serviço (operadoras.js --update), gravada nas páginas antigas antes da unificação.', servicos: result }, null, 1) + '\n')
    console.log(JSON.stringify(result, null, 1).slice(0, 1800))
    process.exit(0)
  }
  const base = JSON.parse(fs.readFileSync(FILE, 'utf8')).servicos
  let fails = 0
  for (const [serv, atual] of Object.entries(result)) {
    const b = base[serv]
    const dif = []
    for (const k of ['stats', 'resultados', 'pagina', 'colunas', 'linha1']) {
      if (JSON.stringify(atual[k]) !== JSON.stringify(b[k])) dif.push(`${k}: esperado ${JSON.stringify(b[k])} e veio ${JSON.stringify(atual[k])}`)
    }
    for (const f of b.filtros) if (!atual.filtros.includes(f)) dif.push(`filtro "${f}" sumiu`)
    console.log(`${dif.length ? 'FAIL' : 'ok  '} - ${serv}` + (dif.length ? ' → ' + dif.join(' | ').slice(0, 600) : ` (${atual.resultados ?? atual.pagina})`))
    if (dif.length) fails += 1
  }
  process.exit(fails ? 1 : 0)
})()
