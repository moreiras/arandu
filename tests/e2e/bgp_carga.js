// Carga da página /bgp: quando o conteúdo aparece, quanto a thread principal fica presa e o que é baixado antes de rolar.
// Uso (contra um ambiente real): docker run --rm -v $PWD/tests/e2e/bgp_carga.js:/e2e/bgp_carga.js -w /e2e -e BASE_URL=http://<ambiente> \
//   -e XFF=<IP da ALLOWED_IPS> mcr.microsoft.com/playwright:v1.49.0-jammy bash -c "npm i playwright@1.49.0 >/dev/null 2>&1 && node bgp_carga.js"
// `maior_tarefa_ms` = maior atraso do batimento de 50 ms (thread principal presa). Mede sem rolar a página e depois rolando até a seção de estabilidade. Falha se o conteúdo demorar > 5 s ou se a thread ficar presa > 1 s antes de rolar.
const { chromium } = require('playwright')
const BASE = process.env.BASE_URL || 'http://localhost:18080'
const XFF = process.env.XFF || '203.0.113.129'
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

;(async () => {
  const browser = await chromium.launch()
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, extraHTTPHeaders: { 'X-Forwarded-For': XFF } })
  const page = await ctx.newPage()
  let bytes = 0
  const grandes = []
  const pend = []
  page.on('response', (res) => pend.push(res.request().sizes().then((s) => {
    const b = (s.responseBodySize || 0) + (s.responseHeadersSize || 0)
    bytes += b
    if (b > 500000) grandes.push(`${(b / 1e6).toFixed(1)} MB ${res.url().replace(BASE, '')}`)
  }).catch(() => {})))
  await page.addInitScript(() => {
    // batimento: a thread principal presa aparece como um intervalo muito maior que os 50 ms pedidos
    window.__tarefas = []
    let ult = performance.now()
    setInterval(() => { const n = performance.now(); window.__tarefas.push(n - ult - 50); ult = n }, 50)
  })
  const t0 = Date.now()
  await page.goto(BASE + '/bgp', { waitUntil: 'commit' })
  await page.getByRole('heading', { name: /Tabela BGP Global/ }).waitFor({ timeout: 60000 })
  const tConteudo = Date.now() - t0
  await wait(8000)
  await Promise.all(pend)
  const antes = { bytes, maiorTarefa: Math.max(0, ...(await page.evaluate(() => window.__tarefas))) }
  const grandesAntes = [...grandes]
  // rola até a estabilidade
  await page.getByRole('heading', { name: /Estabilidade de anúncios BGP/ }).scrollIntoViewIfNeeded()
  await page.waitForFunction(() => document.body.innerText.includes('Distribuição de updates/prefixo/dia'), null, { timeout: 120000 }).catch(() => {})
  await wait(8000)
  await Promise.all(pend)
  const depois = { bytes, maiorTarefa: Math.max(0, ...(await page.evaluate(() => window.__tarefas))) }
  console.log(JSON.stringify({ conteudo_ms: tConteudo, antes_de_rolar: { MB: +(antes.bytes / 1e6).toFixed(2), maior_tarefa_ms: Math.round(antes.maiorTarefa), grandes: grandesAntes },
    depois_de_rolar: { MB: +(depois.bytes / 1e6).toFixed(2), maior_tarefa_ms: Math.round(depois.maiorTarefa), grandes } }, null, 1))
  await browser.close()
  if (process.argv.includes('--verificar') && (tConteudo > 5000 || antes.maiorTarefa > 1000)) { console.error('FALHOU: conteúdo lento ou thread presa antes de rolar'); process.exit(1) }
})()
