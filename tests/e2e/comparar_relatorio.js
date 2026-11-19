// Comparar genérico e relatório de uma página.
//   BASE_URL=http://host.docker.internal:18080 node comparar_relatorio.js
// Confere: comparar ASes/operadoras/municípios pela URL, aliases, citação, e que o relatório de AS, operadora, município e grupo cabe em 1 página A4 (PDF do Chromium).
const { chromium } = require('playwright')
const BASE = process.env.BASE_URL || 'http://localhost:18080'
const paginasPdf = (buf) => (buf.toString('latin1').match(/\/Type\s*\/Page[^s]/g) || []).length
let falhas = 0
const ok = (c, msg) => { console.log(`${c ? 'ok  ' : 'FAIL'} - ${msg}`); if (!c) falhas++ }

;(async () => {
  const browser = await chromium.launch()
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, extraHTTPHeaders: { 'X-Forwarded-For': '203.0.113.129' } })
  const get = async (p) => (await ctx.request.get(BASE + p)).json()
  const asns = ((await get('/api/v1/asns?limit=5')).items || []).slice(0, 2).map((a) => a.asn)
  const ops = ((await get('/api/v1/scms?limit=2')).items || []).map((s) => s.cnpj)
  const muns = ((await get('/api/v1/acessos/municipios')).items || []).slice(0, 2).map((m) => String(m.ibge || m.codigo_ibge))
  const grupo = ((await get('/api/v1/grupos')).grupos || []).find((g) => g.tamanho >= 2)?.grupo_id
  const page = await ctx.newPage()
  const cenarios = [['asn', asns], ['operadora', ops], ['municipio', muns]]
  for (const [tipo, ids] of cenarios) {
    if (ids.length < 2) { console.log(`skip - comparar ${tipo}: amostra com menos de 2`); continue }
    await page.goto(`${BASE}/comparar?tipo=${tipo}&ids=${ids.join(',')}`, { waitUntil: 'networkidle' })
    await page.waitForSelector('[data-testid="quadro-comparacao"]', { timeout: 15000 }).catch(() => {})
    ok((await page.locator('[data-testid="quadro-comparacao"] thead th').count()) === ids.length + 1, `comparar ${tipo}: ${ids.length} colunas`)
    ok((await page.locator('[data-testid="quadro-comparacao"] tbody tr').count()) > 0, `comparar ${tipo}: tem linhas com selo`)
    await page.goto(`${BASE}/comparar?${tipo}=${ids.join(',')}`, { waitUntil: 'networkidle' })     // alias
    await page.waitForSelector('[data-testid="quadro-comparacao"]', { timeout: 15000 }).catch(() => {})
    ok((await page.locator('[data-testid="quadro-comparacao"]').count()) === 1, `alias ?${tipo}= abre a mesma comparação`)
  }
  await page.goto(`${BASE}/comparar`, { waitUntil: 'networkidle' })
  ok((await page.getByText('Comparar PTTs').count()) > 0, '/comparar sem parâmetros segue sendo o comparador de PTTs')
  // citar este dado
  await page.goto(`${BASE}/asn/${asns[0]}`, { waitUntil: 'networkidle' })
  await page.locator('[data-testid="proveniencia-compacta"] summary').first().click()
  const txt = await page.locator('[data-testid="citar-dado"] textarea').first().inputValue().catch(() => '')
  ok(/Disponível em: .*date=/.test(txt) && /Snapshot de/.test(txt) && /Acesso em/.test(txt), 'citação tem link permanente com ?date=, snapshot e data de acesso')
  // relatório em A4
  const rels = [['asn', asns[0]], ['operadora', ops[0]], ['municipio', muns[0]], ['grupo', grupo]].filter(([, id]) => id)
  for (const [tipo, id] of rels) {
    await page.goto(`${BASE}/relatorio/${tipo}/${encodeURIComponent(id)}`, { waitUntil: 'networkidle' })
    await page.waitForSelector('[data-testid="relatorio"]', { timeout: 15000 }).catch(() => {})
    await page.emulateMedia({ media: 'print' })
    const pdf = await page.pdf({ format: 'A4', printBackground: true, margin: { top: '12mm', bottom: '12mm', left: '12mm', right: '12mm' } })
    const n = paginasPdf(pdf)
    ok(n === 1, `relatório de ${tipo} cabe em 1 página A4 (${n})`)
    ok((await page.locator('header.sticky').isVisible().catch(() => false)) === false, `relatório de ${tipo}: menu do site some na impressão`)
    await page.emulateMedia({ media: 'screen' })
  }
  await browser.close()
  process.exit(falhas ? 1 : 0)
})()
