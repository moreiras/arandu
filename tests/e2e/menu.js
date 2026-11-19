// Menu por tema: percorre todos os grupos e links de frontend/src/components/layout/menu.ts e testa o teclado.
//   BASE_URL=http://host.docker.internal:18080 node menu.js
// Falha se: algum link não leva à própria rota, a página mostra erro cru, há resposta 5xx ou erro de página, ou o teclado não funciona.
const { chromium } = require('playwright')
const fs = require('fs')

const BASE = process.env.BASE_URL || 'http://localhost:18080'
const MENU_TS = process.env.MENU_TS || '/menu.ts'
// Itens do menu que redirecionam de propósito: o destino final é o que o teste confere.
const REDIRECIONA = { '/rankings': '/operadoras?visao=ranking' }
const destino = (to) => REDIRECIONA[to] || to
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

function lerMenu() {
  const bruto = fs.readFileSync(MENU_TS, 'utf8')
  const src = bruto.split('export const ITENS_AVULSOS')[0]            // os itens avulsos (Comparar) têm leitura própria, abaixo
  const grupos = []
  for (const m of src.matchAll(/id: '[^']+', rotulo: '([^']+)'|rotulo: '([^']+)', to: '([^']+)'/g)) {
    if (m[1]) grupos.push({ rotulo: m[1], itens: [] })
    else grupos[grupos.length - 1].itens.push({ rotulo: m[2], to: m[3] })
  }
  return grupos
}

function lerAvulsos() {
  const trecho = fs.readFileSync(MENU_TS, 'utf8').split('export const ITENS_AVULSOS')[1] || ''
  return [...trecho.split('\n]\n')[0].matchAll(/rotulo: '([^']+)', to: '([^']+)'/g)].map((m) => ({ rotulo: m[1], to: m[2] }))
}

;(async () => {
  const grupos = lerMenu()
  if (grupos.length < 6) { console.log('FAIL - menu.ts não foi lido (' + grupos.length + ' grupos)'); process.exit(1) }
  const browser = await chromium.launch()
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, extraHTTPHeaders: { 'X-Forwarded-For': '203.0.113.129' } })
  const page = await ctx.newPage()
  let erros5xx = 0, errosPagina = 0
  page.on('response', (r) => { if (r.status() >= 500) erros5xx += 1 })
  page.on('pageerror', () => { errosPagina += 1 })
  let fails = 0
  const falha = (msg) => { console.log('FAIL - ' + msg); fails += 1 }

  await page.goto(BASE + '/', { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {})
  let total = 0
  for (const g of grupos) {
    for (const item of g.itens) {
      await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' })
      await page.getByRole('button', { name: g.rotulo, exact: true }).click()
      await page.getByRole('menuitem', { name: item.rotulo, exact: true }).click()
      await page.waitForURL((u) => u.pathname + u.search === destino(item.to), { timeout: 15000 }).catch(() => falha(`${g.rotulo} › ${item.rotulo} não foi para ${item.to} (está em ${new URL(page.url()).pathname + new URL(page.url()).search})`))
      await wait(800)
      const erro = await page.getByText(/Erro ao carregar|Something went wrong|HTTP 5\d\d/i).first().isVisible().catch(() => false)
      if (erro) falha(`${g.rotulo} › ${item.rotulo}: erro cru na tela`)
      total += 1
    }
  }
  const avulsos = lerAvulsos()
  if (!avulsos.length) falha('menu.ts: nenhum item avulso lido (Comparar)')
  for (const item of avulsos) {
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' })
    await page.getByRole('link', { name: item.rotulo, exact: true }).first().click()
    await page.waitForURL((u) => u.pathname + u.search === destino(item.to), { timeout: 15000 }).catch(() => falha(`avulso ${item.rotulo} não foi para ${item.to}`))
    total += 1
  }
  console.log(`ok   - ${total} links percorridos em ${grupos.length} grupos + ${avulsos.length} avulso(s)`)

  // teclado: ↓ abre e foca o 1º item; ↓/↑ percorrem; Esc fecha e devolve o foco ao botão
  await page.goto(BASE + '/', { waitUntil: 'networkidle' })
  const g0 = grupos[0]
  const botao = page.getByRole('button', { name: g0.rotulo, exact: true })
  await botao.focus()
  await page.keyboard.press('ArrowDown')
  await wait(200)
  const primeiro = await page.evaluate(() => document.activeElement?.getAttribute('aria-label'))
  if (primeiro !== g0.itens[0].rotulo) falha(`teclado: ↓ deveria focar "${g0.itens[0].rotulo}" e focou "${primeiro}"`)
  await page.keyboard.press('ArrowDown')
  await wait(200)
  const segundo = await page.evaluate(() => document.activeElement?.getAttribute('aria-label'))
  if (segundo !== g0.itens[1].rotulo) falha(`teclado: 2º ↓ deveria focar "${g0.itens[1].rotulo}" e focou "${segundo}"`)
  await page.keyboard.press('Escape')
  await wait(200)
  if (await page.getByRole('menu').count()) falha('teclado: Esc não fechou o menu')
  if (!(await botao.evaluate((el) => el === document.activeElement))) falha('teclado: Esc não devolveu o foco ao botão')
  else console.log('ok   - teclado (↓ abre e foca, ↑/↓ percorrem, Esc fecha e devolve o foco)')

  // celular: cabeçalho de uma linha, ☰ abre a gaveta, nenhum item fora da tela e cada link leva à própria rota
  const cel = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, extraHTTPHeaders: { 'X-Forwarded-For': '203.0.113.129' } })
  const m = await cel.newPage()
  m.on('response', (r) => { if (r.status() >= 500) erros5xx += 1 })
  m.on('pageerror', () => { errosPagina += 1 })
  await m.goto(BASE + '/', { waitUntil: 'networkidle' })
  const altura = await m.evaluate(() => document.querySelector('header').getBoundingClientRect().height)
  if (altura > 56) falha(`celular: cabeçalho com ${Math.round(altura)} px (deveria ser de uma linha)`)
  let foraDaTela = 0, totalCel = 0
  for (const g of grupos) {
    for (const item of g.itens) {
      await m.goto(BASE + '/', { waitUntil: 'domcontentloaded' })
      await m.getByRole('button', { name: 'Abrir menu' }).click()
      await m.getByRole('button', { name: new RegExp('^' + g.rotulo) }).click()
      const link = m.getByRole('link', { name: item.rotulo, exact: true })
      const caixa = await link.boundingBox()
      if (!caixa || caixa.x < 0 || caixa.x + caixa.width > 390.5) foraDaTela += 1
      totalCel += 1
      if (item.to.endsWith('.xml')) continue
      await link.click()
      await m.waitForURL((u) => u.pathname + u.search === destino(item.to), { timeout: 15000 }).catch(() => falha(`celular: ${g.rotulo} › ${item.rotulo} não foi para ${item.to}`))
    }
  }
  for (const item of avulsos) {
    await m.goto(BASE + '/', { waitUntil: 'domcontentloaded' })
    await m.getByRole('button', { name: 'Abrir menu' }).click()
    const link = m.getByRole('link', { name: item.rotulo, exact: true })
    const caixa = await link.boundingBox()
    if (!caixa || caixa.x < 0 || caixa.x + caixa.width > 390.5) foraDaTela += 1
    totalCel += 1
    await link.click()
    await m.waitForURL((u) => u.pathname + u.search === destino(item.to), { timeout: 15000 }).catch(() => falha(`celular: avulso ${item.rotulo} não foi para ${item.to}`))
  }
  if (foraDaTela) falha(`celular: ${foraDaTela} item(ns) de menu fora da tela`)
  else console.log(`ok   - celular: ${totalCel} itens na gaveta, 0 fora da tela, cabeçalho de ${Math.round(altura)} px`)
  const rolou = await m.evaluate(() => document.documentElement.scrollWidth > 390)
  if (rolou) falha('celular: a página rola na horizontal')

  if (erros5xx) falha(`${erros5xx} resposta(s) 5xx`)
  if (errosPagina) falha(`${errosPagina} erro(s) de página`)
  await browser.close()
  process.exit(fails ? 1 : 0)
})()
