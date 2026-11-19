// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
//
// Acessibilidade (ABNT NBR 17225:2025, conformidade regular = WCAG 2.2 A/AA). Contra um ambiente real, como o console.js:
//   docker run --rm -v $PWD/tests/e2e:/repo/tests/e2e -v $PWD/frontend/src/components/layout:/repo/frontend/src/components/layout:ro -w /repo/tests/e2e \
//     -e BASE_URL=http://<ambiente> mcr.microsoft.com/playwright:v1.49.0-jammy bash -c "npm i playwright@1.49.0 @axe-core/playwright@4.10.1 && node acessibilidade.js"
// (o menu.ts entra montado: as rotas testadas são as do menu)
// Confere, nas páginas do menu e numa página de cada entidade:
//  - 1280 px: violações sérias ou críticas do axe (regras WCAG 2.0/2.1/2.2 A e AA), fora as exceções abaixo;
//  - 360 px com toque: a página não rola na horizontal;
//  - "Leitura confortável" ligada (5.12.1–5.12.4): a página continua sem rolagem horizontal e o conteúdo principal não some.
// O axe só vê o que está na tela ao carregar (a primeira aba): não substitui teste com teclado e leitor de tela.
const fs = require('fs')
const { chromium } = require('playwright')
const { AxeBuilder } = require('@axe-core/playwright')

const BASE = process.env.BASE_URL || 'http://localhost:18080'
const MENU = fs.readFileSync(__dirname + '/../../frontend/src/components/layout/menu.ts', 'utf8')
const ROTAS = ['/', ...[...MENU.matchAll(/to: '([^']+)'/g)].map((m) => m[1]).filter((r) => !r.includes('sitemap')),
  '/asn/28573', '/ixp/sp', '/operadora/02558157000162', '/municipio/3550308', '/uf/SP', '/login', '/privacidade', '/acessibilidade']

// Exceções: mapas e curvas de Hilbert ficam fora; o seletor de camadas do Mapa é parte do mapa.
const EXCECOES = [
  { rota: '/mapa', regra: 'target-size' },
]
const exceto = (rota, regra) => EXCECOES.some((e) => e.rota === rota && e.regra === regra)

;(async () => {
  const b = await chromium.launch()
  let falhas = 0
  const largo = await b.newContext({ viewport: { width: 1280, height: 900 } })
  const p = await largo.newPage()
  for (const r of ROTAS) {
    try {
      await p.goto(BASE + r, { waitUntil: 'networkidle', timeout: 60000 })
      await p.waitForTimeout(1200)
      const ax = await new AxeBuilder({ page: p }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze()
      const graves = ax.violations.filter((v) => ['serious', 'critical'].includes(v.impact) && !exceto(r, v.id))
      if (graves.length) {
        falhas++
        console.log(`ERRO ${r}: ${graves.map((v) => `${v.id} (${v.nodes.length}: ${v.nodes.slice(0, 2).map((n) => n.target.join(' ')).join(' | ')})`).join('; ')}`)
      } else console.log(`ok   ${r}: axe sem violação séria`)
    } catch (e) { falhas++; console.log(`ERRO ${r}: ${String(e).slice(0, 160)}`) }
  }
  await largo.close()

  const celular = await b.newContext({ viewport: { width: 360, height: 740 }, hasTouch: true, isMobile: true })
  const c = await celular.newPage()
  for (const confortavel of [false, true]) {
    await c.goto(BASE + '/', { waitUntil: 'domcontentloaded' })
    await c.evaluate((v) => { try { localStorage.setItem('arandurape.leitura.confortavel', v ? '1' : '0') } catch { /* sem armazenamento */ } }, confortavel)
    for (const r of ROTAS) {
      try {
        await c.goto(BASE + r, { waitUntil: 'networkidle', timeout: 60000 })
        await c.waitForTimeout(800)
        const sobra = await c.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
        const temMain = await c.evaluate(() => (document.querySelector('main')?.textContent ?? '').trim().length > 0)
        if (sobra > 1 || !temMain) {
          falhas++
          console.log(`ERRO ${r} (360 px${confortavel ? ', leitura confortável' : ''}): rolagem horizontal de ${sobra} px${temMain ? '' : '; conteúdo vazio'}`)
        }
      } catch (e) { falhas++; console.log(`ERRO ${r} (360 px): ${String(e).slice(0, 160)}`) }
    }
  }
  await celular.close()
  await b.close()
  console.log(falhas ? `TOTAL: ${falhas} falha(s)` : 'ZERO falhas de acessibilidade verificáveis automaticamente')
  process.exit(falhas ? 1 : 0)
})()
