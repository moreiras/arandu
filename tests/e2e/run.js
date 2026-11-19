// E2E da política de acesso (api/auth/access_policy.py) — Playwright.
// Requer a pilha local (ver tests/e2e/run.sh): nginx do frontend + API real em modo
// enforce com ANON_SESSION_LIMIT_MINUTES=1 e heartbeat de 2 s.
const { chromium } = require('playwright')
const BASE = process.env.BASE_URL || 'http://host.docker.internal:18080'
let fails = 0
const ok = (m) => console.log('  ok   -', m)
const nok = (m, e) => { fails++; console.log('  FAIL -', m, e ? `(${e})` : '') }
async function step(name, fn) {
  try { await fn(); ok(name) } catch (e) { nok(name, String(e.message || e).split('\n')[0]) }
}
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

async function visible(page, text, timeout = 15000) {
  await page.getByText(text, { exact: false }).first().waitFor({ state: 'visible', timeout })
}
// Painel de acesso (AccessPanel): o contêiner role=status com o título "Entre para continuar". Procurar só o texto
// casava também com o aviso do chip para leitores de tela (BudgetChip, sr-only), presente desde o
// início quando o orçamento é de 1 min, e com o modal de login (que tem o mesmo título, mas é um dialog).
const painel = (p) => p.locator('[role="status"]').filter({ has: p.getByRole('heading', { name: 'Entre para continuar' }) }).first()
async function notRedirectedToLogin(page) {
  if (page.url().includes('/login')) throw new Error('redirecionou para /login: ' + page.url())
}
async function jiggle(page, n = 1) {
  for (let i = 0; i < n; i++) { await page.mouse.move(100 + i * 7, 120 + i * 5); await wait(250) }
}

;(async () => {
  const browser = await chromium.launch()

  // ── Anônimo ────────────────────────────────────────────────────────────────
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } })
  const page = await ctx.newPage()
  const apiStatus = {}
  page.on('response', (r) => { const u = new URL(r.url()); if (u.pathname.startsWith('/api/')) apiStatus[u.pathname + u.search] = r.status() })

  await step('entrada: Dashboard abre sem login', async () => {
    await page.goto(BASE + '/'); await visible(page, 'Home'); await notRedirectedToLogin(page)
  })
  await step('entrada: /ases abre e mostra a prévia', async () => {
    await page.goto(BASE + '/ases'); await visible(page, 'ASes Brasileiros'); await visible(page, 'Prévia', 30000)
  })
  await step('lista: "Próxima" abre o modal de login e mantém a página', async () => {
    await page.getByRole('button', { name: /Próxima/ }).click()
    await page.getByRole('dialog').waitFor({ state: 'visible', timeout: 5000 })
    await visible(page, 'lista completa')
    if (!page.url().endsWith('/ases')) throw new Error('mudou de página: ' + page.url())
    await page.getByRole('button', { name: 'Agora não' }).click()
    await page.getByRole('dialog').waitFor({ state: 'hidden', timeout: 3000 })
  })
  await step('API: /asns?page=2 sem login = 401 login_required', async () => {
    const r = await ctx.request.get(BASE + '/api/v1/asns?page=2&limit=10')
    if (r.status() !== 401) throw new Error('status ' + r.status())
    const b = await r.json(); if (!b.login_required) throw new Error('sem login_required')
  })
  await step('entrada: /scms redireciona para /operadoras e abre sem login', async () => {
    await page.goto(BASE + '/scms'); await page.waitForLoadState('networkidle'); await notRedirectedToLogin(page)
    if (!page.url().includes('/operadoras?servico=scm')) throw new Error('não redirecionou: ' + page.url())
  })

  // Página avançada: orçamento de 1 min só corre aqui
  let chipSeen = false
  await step('avançada: /mapa abre com o chip de orçamento', async () => {
    await page.goto(BASE + '/mapa'); await notRedirectedToLogin(page)
    await visible(page, 'restam', 20000); chipSeen = true
  })
  await step('avançada: ao esgotar, painel de login só na página', async () => {
    const deadline = Date.now() + 120000
    while (Date.now() < deadline) {
      await jiggle(page, 4)
      if (await painel(page).isVisible().catch(() => false)) return
    }
    throw new Error('orçamento não esgotou em 120 s')
  })
  await step('esgotado: entrada segue aberta (/, /ixps, /ases)', async () => {
    for (const [path, h] of [['/', 'Home'], ['/ixps', 'IXPs'], ['/ases', 'ASes Brasileiros']]) {
      await page.goto(BASE + path); await visible(page, h, 20000); await notRedirectedToLogin(page)
      if (await painel(page).isVisible().catch(() => false)) throw new Error('painel em ' + path)
    }
  })
  await step('esgotado: detalhe de ASN mostra o painel', async () => {
    await page.goto(BASE + '/asn/3356'); await painel(page).waitFor({ state: 'visible', timeout: 15000 })
  })
  await step('esgotado: API avançada = 403, entrada = 200', async () => {
    const a = await ctx.request.get(BASE + '/api/v1/map/asns'); if (a.status() !== 403) throw new Error('map/asns ' + a.status())
    const b = await ctx.request.get(BASE + '/api/v1/ixps'); if (b.status() !== 200) throw new Error('ixps ' + b.status())
  })
  await step('histórico: /snapshots mostra o painel de login', async () => {
    await page.goto(BASE + '/snapshots'); await visible(page, 'snapshots anteriores', 10000)
  })
  await ctx.close()

  // ── IP na allowlist (via X-Forwarded-For, aceito do proxy privado) ────────
  const ctx2 = await browser.newContext({ viewport: { width: 1400, height: 900 }, extraHTTPHeaders: { 'X-Forwarded-For': '203.0.113.129' } })
  const p2 = await ctx2.newPage()
  await step('allowlist: /mapa abre sem chip nem painel', async () => {
    await p2.goto(BASE + '/mapa'); await wait(4000); await notRedirectedToLogin(p2)
    if (await p2.getByText('restam').first().isVisible().catch(() => false)) throw new Error('chip visível')
    if (await painel(p2).isVisible().catch(() => false)) throw new Error('painel visível')
  })
  await step('allowlist: paginar não pede login', async () => {
    await p2.goto(BASE + '/ases'); await visible(p2, 'ASes Brasileiros')
    await p2.getByRole('button', { name: /Próxima/ }).click({ timeout: 30000 })
    await wait(800)
    if (await p2.getByRole('dialog').isVisible().catch(() => false)) throw new Error('modal apareceu')
  })
  await step('allowlist: API /asns?page=2 = 200', async () => {
    const r = await ctx2.request.get(BASE + '/api/v1/asns?page=2&limit=10'); if (r.status() !== 200) throw new Error('status ' + r.status())
  })
  await ctx2.close()

  await browser.close()
  console.log(fails ? `HÁ ${fails} FALHA(S)` : 'TODOS OK')
  process.exit(fails ? 1 : 0)
})()
