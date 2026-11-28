// E2E da política de acesso (api/auth/access_policy.py) — Playwright.
// Requer a pilha local (ver tests/e2e/run.sh): nginx do frontend + API real em modo
// enforce com ANON_SESSION_LIMIT_MINUTES=1 e heartbeat de 2 s.
const { chromium } = require('playwright')
const BASE = process.env.BASE_URL || 'http://host.docker.internal:18080'
// E2E_XFF: IP de origem fictício (fora da allowlist) do contexto anônimo; cada valor tem orçamento próprio, o que permite repetir a rodada sem zerar o estado.
const E2E_XFF = process.env.E2E_XFF || ''
let fails = 0
const ok = (m) => console.log('  ok   -', m)
const nok = (m, e) => { fails++; console.log('  FAIL -', m, e ? `(${e})` : '') }
async function step(name, fn) {
  try { await fn(); ok(name) } catch (e) { nok(name, String(e.message || e).split('\n')[0]) }
}
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

async function visible(page, text, timeout = 30000) {
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
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, extraHTTPHeaders: E2E_XFF ? { 'X-Forwarded-For': E2E_XFF } : {} })
  const page = await ctx.newPage()
  const apiStatus = {}
  page.on('response', (r) => { const u = new URL(r.url()); if (u.pathname.startsWith('/api/')) apiStatus[u.pathname + u.search] = r.status() })

  await step('entrada: Dashboard abre sem login', async () => {
    await page.goto(BASE + '/'); await visible(page, 'Home'); await notRedirectedToLogin(page)
  })
  await step('entrada: /ases abre e mostra a prévia', async () => {
    await page.goto(BASE + '/ases'); await visible(page, 'ASes Brasileiros'); await visible(page, 'Prévia')
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
    await page.goto(BASE + '/scms'); await notRedirectedToLogin(page)
    // não usar waitForLoadState('networkidle'): a página tem mapa (camadas, tiles, fontes) e o heartbeat, e o critério depende da carga do servidor
    await page.waitForURL(/\/operadoras\?servico=scm/, { timeout: 30000 })
    await visible(page, 'Outorgas SCM')
  })

  await step('lista: prévia de 100 linhas em /ases e /operadoras, com a mensagem e o modal de login', async () => {
    for (const path of ['/ases', '/operadoras?servico=scm']) {
      await page.goto(BASE + path); await notRedirectedToLogin(page)
      const previa = page.getByTestId('previa-lista')
      await previa.waitFor({ state: 'visible', timeout: 30000 })
      const m = (await previa.innerText()).replace(/\s+/g, ' ').match(/^Prévia: (\d+) de ([\d.]+)\. Entre para ver as demais\.$/)
      if (!m) throw new Error(path + ': texto da prévia inesperado: ' + (await previa.innerText()))
      const mostradas = Number(m[1]); const total = Number(m[2].replace(/\./g, ''))
      if (mostradas > 100 || mostradas < 1) throw new Error(path + ': prévia de ' + mostradas + ' linhas')
      if (total <= mostradas) throw new Error(path + ': total ' + total + ' não excede a prévia ' + mostradas)
      if (path === '/ases') {
        const linhas = await page.locator('table tbody tr').filter({ hasText: /^AS\d+/ }).count()
        if (linhas > 100 || linhas !== mostradas) throw new Error(`/ases: ${linhas} linhas na tabela, prévia diz ${mostradas}`)
      }
      await previa.getByRole('button', { name: 'Entre para ver as demais.' }).click()
      await page.getByRole('dialog').waitFor({ state: 'visible', timeout: 5000 })
      await page.getByRole('button', { name: 'Agora não' }).click()
      await page.getByRole('dialog').waitFor({ state: 'hidden', timeout: 3000 })
    }
  })
  await step('histórico: data antiga sem login mostra o aviso de snapshot histórico e "Ir para o snapshot atual" leva à página sem data', async () => {
    await page.goto(BASE + '/ases?date=2001-01-01'); await notRedirectedToLogin(page)
    const aviso = page.getByTestId('snapshot-historico')
    await aviso.waitFor({ state: 'visible', timeout: 30000 })
    const t = await aviso.innerText()
    for (const trecho of ['Snapshot histórico', 'dois snapshots mais recentes', 'login gratuito', 'Isto não é um erro']) if (!t.includes(trecho)) throw new Error('aviso sem "' + trecho + '": ' + t.slice(0, 200))
    const entrar = await aviso.getByRole('link', { name: 'Entrar para ver este snapshot' }).getAttribute('href')
    if (!entrar || !entrar.startsWith('/login?next=') || !decodeURIComponent(entrar).includes('/ases?date=2001-01-01')) throw new Error('link de login sem o endereço: ' + entrar)
    if (await page.getByText('não encontrado', { exact: false }).first().isVisible().catch(() => false)) throw new Error('mostra "não encontrado"')
    await aviso.getByRole('button', { name: 'Ir para o snapshot atual' }).click()
    await visible(page, 'ASes Brasileiros')
    if (page.url().includes('date=')) throw new Error('a data voltou à URL: ' + page.url())
    if (await page.getByTestId('snapshot-historico').isVisible().catch(() => false)) throw new Error('o aviso continua na tela')
    await visible(page, 'Prévia')
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
    await page.goto(BASE + '/asn/3356'); await painel(page).waitFor({ state: 'visible', timeout: 30000 })
  })
  await step('esgotado: a página avançada explica o limite e oferece "Entrar"; não diz "não encontrado" nem mostra zeros', async () => {
    await page.goto(BASE + '/asn/3356'); await painel(page).waitFor({ state: 'visible', timeout: 30000 })
    const t = (await painel(page).innerText()).replace(/\s+/g, ' ')
    if (!t.includes('O tempo de uso das páginas avançadas sem login acabou. Entre gratuitamente para continuar.')) throw new Error('mensagem do painel: ' + t)
    const href = await painel(page).getByRole('link', { name: 'Entrar' }).getAttribute('href')
    if (!href || !href.startsWith('/login?next=') || !decodeURIComponent(href).includes('/asn/3356')) throw new Error('link Entrar sem next: ' + href)
    const corpo = (await page.locator('body').innerText()).replace(/\s+/g, ' ')
    if (/n[ãa]o encontrad/i.test(corpo)) throw new Error('a página diz "não encontrado"')
    if (await page.locator('main h1').first().isVisible().catch(() => false)) throw new Error('perfil renderizado em vez do painel')
    // Bloco de dado que recebe o 429 (EstadoDados, data-estado=orcamento): quando houver, deve oferecer a entrada e a espera.
    for (const bloco of await page.locator('[data-estado="orcamento"]').all()) {
      const b = (await bloco.innerText()).replace(/\s+/g, ' ')
      if (!b.includes('Entrar') || !/volte em/.test(b)) throw new Error('bloco de orçamento sem "Entrar" ou "volte em": ' + b)
    }
  })
  await step('esgotado: API avançada = 429 com Retry-After, entrada = 200', async () => {
    const a = await ctx.request.get(BASE + '/api/v1/map/asns'); if (a.status() !== 429 || !a.headers()['retry-after']) throw new Error('map/asns ' + a.status())
    const b = await ctx.request.get(BASE + '/api/v1/ixps'); if (b.status() !== 200) throw new Error('ixps ' + b.status())
  })
  await step('esgotado: o corpo do 429 explica o limite, a renovação e o login', async () => {
    const a = await ctx.request.get(BASE + '/api/v1/map/asns')
    if (a.status() !== 429) throw new Error('map/asns ' + a.status())
    const espera = Number(a.headers()['retry-after'])
    if (!Number.isInteger(espera) || espera < 1 || espera > 86400) throw new Error('Retry-After fora de 1 a 86400 s: ' + a.headers()['retry-after'])
    if (!/no-store/.test(a.headers()['cache-control'] || '')) throw new Error('429 cacheável: ' + a.headers()['cache-control'])
    const c = await a.json()
    if (c.anon_limit_reached !== true) throw new Error('sem anon_limit_reached')
    if (c.retry_after !== espera) throw new Error(`retry_after ${c.retry_after} difere do cabeçalho ${espera}`)
    if (!/meia-noite UTC/.test(c.detail || '') || !/conta/.test(c.detail || '')) throw new Error('detail não explica a renovação e o login: ' + c.detail)
    if (!Array.isArray(c.alternativas) || !c.alternativas.some((x) => /login|conta gratuita/i.test(x))) throw new Error('sem alternativa de login: ' + JSON.stringify(c.alternativas))
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
