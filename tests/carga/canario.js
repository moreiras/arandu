// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
//
// Canário do teste de carga: um navegador real visitando páginas enquanto o Locust gera a carga. Mede o que a pessoa sente
// (da navegação até o conteúdo na tela) e conta erros de console. Cada ciclo é um visitante novo (contexto e IP novos).
//   BASE_URL=http://HOST DURACAO_S=1800 INTERVALO_S=20 SAIDA=saida/RUN/canario.jsonl node canario.js
const { chromium } = require('playwright')
const fs = require('fs')

const BASE = process.env.BASE_URL || 'http://localhost:18080'
const DURACAO = parseInt(process.env.DURACAO_S || '600', 10) * 1000
const INTERVALO = parseInt(process.env.INTERVALO_S || '20', 10) * 1000
const SAIDA = process.env.SAIDA || 'saida/canario.jsonl'
const ID = process.env.CANARIO_ID || '1'
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

;(async () => {
  const browser = await chromium.launch()
  const sonda = await browser.newContext({ extraHTTPHeaders: { 'X-Forwarded-For': process.env.XFF_SETUP || '127.0.0.1' } })
  const get = async (p) => (await sonda.request.get(BASE + p)).json()
  const asns = (await get('/api/v1/asns?limit=50&br_only=true&sort_by=apnic_users&sort_desc=true')).items.map((a) => a.asn)
  const ixps = (await get('/api/v1/ixps')).ixps.map((i) => i.code)
  const mun = (await get('/api/v1/acessos/municipios')).items.slice(0, 100).map((m) => m.ibge)
  await sonda.close()
  const sorteio = (xs) => xs[Math.floor(Math.random() * xs.length)]
  const fim = Date.now() + DURACAO
  let n = 0
  fs.mkdirSync(require('path').dirname(SAIDA), { recursive: true })
  while (Date.now() < fim) {
    n += 1
    // Cada ciclo é outro visitante: IP sorteado fora da faixa dos usuários do Locust (198.19.240.0/20) e tela sorteada (o navegador
    // headless dá sempre o mesmo fingerprint; com a mesma tela e o mesmo IP de rodadas anteriores ele herdaria a sessão anônima delas)
    const ip = `198.19.${240 + Math.floor(Math.random() * 15)}.${1 + Math.floor(Math.random() * 250)}`
    const tela = { width: 1280 + Math.floor(Math.random() * 400), height: 800 + Math.floor(Math.random() * 200) }
    const ctx = await browser.newContext({ viewport: tela, extraHTTPHeaders: { 'X-Forwarded-For': ip } })
    const page = await ctx.newPage()
    let erros = 0
    page.on('console', (m) => { if (m.type() === 'error') erros += 1 })
    page.on('pageerror', () => { erros += 1 })
    const roteiro = [['home', '/'], ['asn', `/asn/${sorteio(asns)}`], ['ptt', `/ixp/${sorteio(ixps)}`], ['municipio', `/municipio/${sorteio(mun)}`]]
    for (const [nome, caminho] of roteiro) {
      const t0 = Date.now()
      let ok = true
      let etapa = 'navegar'
      let pendentes = 0
      const contar = () => { pendentes += 1 }
      const descontar = () => { pendentes -= 1 }
      page.on('request', contar); page.on('requestfinished', descontar); page.on('requestfailed', descontar)
      try {
        if (nome === 'home') await page.goto(BASE + caminho, { waitUntil: 'commit', timeout: 60000 })
        else await page.evaluate((c) => { window.history.pushState({}, '', c); window.dispatchEvent(new PopStateEvent('popstate')) }, caminho)
        etapa = 'titulo'
        await page.locator('main h1').first().waitFor({ timeout: 60000 })
        etapa = 'rede_ociosa'
        await page.waitForLoadState('networkidle', { timeout: 60000 })
        etapa = 'ok'
      } catch (e) { ok = false }
      page.off('request', contar); page.off('requestfinished', descontar); page.off('requestfailed', descontar)
      const linha = { ts: Date.now() / 1000, canario: ID, pagina: nome, ms: Date.now() - t0, ok, etapa, pendentes, url: page.url().replace(BASE, ''), erros_console: erros }
      fs.appendFileSync(SAIDA, JSON.stringify(linha) + '\n')
      erros = 0
      await wait(2000)
    }
    await ctx.close()
    await wait(INTERVALO)
  }
  await browser.close()
})()
