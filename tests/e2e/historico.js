// Histórico na interface: a Linha do tempo aparece, com proveniência, nas páginas de ASN, PTT, operadora e UF; a página O que mudou lista
// as diferenças observadas (sem eventos de provedor); Comparar aceita duas datas; o menu "Ecossistema" leva a O que mudou.
//   BASE_URL=http://host.docker.internal:18080 node historico.js
const { chromium } = require('playwright')

const BASE = process.env.BASE_URL || 'http://localhost:18080'
const XFF = process.env.XFF
const wait = (ms) => new Promise((r) => setTimeout(r, ms))
let falhas = 0
const ok = (cond, msg) => { console.log(`${cond ? 'ok  ' : 'FAIL'} - ${msg}`); if (!cond) falhas += 1 }

;(async () => {
  const browser = await chromium.launch()
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, ...(XFF ? { extraHTTPHeaders: { 'X-Forwarded-For': XFF } } : {}) })
  const get = async (p) => (await ctx.request.get(BASE + p)).json()
  const asns = (await get('/api/v1/asns?limit=50')).items
  const asn = (asns.find((a) => a.is_br) || asns[0]).asn
  const ixps = (await get('/api/v1/ixps')).ixps
  const scms = (await get('/api/v1/scms?limit=1')).items
  const paginas = { asn: `/asn/${asn}`, ptt: `/ixp/${ixps[0].code}`, uf: `/uf/${ixps[0].uf}`, ...(scms.length ? { operadora: `/operadora/${scms[0].cnpj}` } : {}) }
  for (const [nome, path] of Object.entries(paginas)) {
    const page = await ctx.newPage()
    await page.goto(BASE + path, { waitUntil: 'networkidle' })
    await wait(800)
    const bloco = page.locator('section[id="bloco-linha-do-tempo"]')
    // operadora sem ASN brasileiro não tem série (o histórico de operadora soma os ASNs do CNPJ): sem histórico no perfil, o bloco não aparece
    const semHistorico = nome === 'operadora' && !(await get(`/api/v1/operadoras/${scms[0].cnpj}?include=historico`)).historico
    ok((await bloco.count()) === (semHistorico ? 0 : 1), `${nome}: bloco Linha do tempo ${semHistorico ? 'ausente (CNPJ sem ASN)' : 'presente'}`)
    if ((await bloco.count()) === 1) {
      ok((await bloco.locator('[data-testid="proveniencia"]').count()) > 0, `${nome}: com proveniência`)
      const texto = (await bloco.innerText()).replace(/\s+/g, ' ')
      ok(/snapshots? com histórico|Ainda não há histórico/.test(texto), `${nome}: mostra a série ou explica que não há histórico`)
      ok(!/provedor/i.test(texto), `${nome}: sem eventos de provedor`)
    }
    await page.close()
  }

  const p = await ctx.newPage()
  await p.goto(BASE + '/mudancas', { waitUntil: 'networkidle' })
  await wait(800)
  ok(/O que mudou/.test(await p.locator('h1').innerText()), 'mudancas: título')
  const corpo = (await p.locator('main').innerText()).replace(/\s+/g, ' ')
  ok(/Passou a|Deixou de|origem mudou|Nova outorga|Nenhuma mudança/.test(corpo), 'mudancas: lista eventos ou diz que não há')
  ok(!/provedor/i.test(corpo.replace(/Assinar por feed/, '')), 'mudancas: sem eventos de provedor')
  ok((await p.locator('a[href="/api/v1/feed/mudancas.atom"]').count()) === 1, 'mudancas: link do feed Atom')
  const feed = await ctx.request.get(BASE + '/api/v1/feed/mudancas.atom')
  ok(feed.status() === 200 && (feed.headers()['content-type'] || '').includes('atom+xml'), 'feed Atom responde')

  await p.goto(BASE + '/comparar?modo=datas', { waitUntil: 'networkidle' })
  await wait(800)
  const c = (await p.locator('main').innerText()).replace(/\s+/g, ' ')
  ok(/Comparar datas/.test(c) && /Indicador|histórico guardado|Escolha duas datas/.test(c), 'comparar por datas: tabela ou aviso')

  await p.goto(BASE + '/', { waitUntil: 'networkidle' })
  await p.getByRole('button', { name: 'Ecossistema' }).click()
  ok((await p.getByRole('menu').getByText('O que mudou').count()) > 0, 'menu Ecossistema tem O que mudou')
  ok((await p.getByRole('button', { name: 'Mercado' }).count()) === 0, 'menu não se chama mais Mercado')
  await browser.close()
  console.log(falhas ? `${falhas} FALHA(S)` : 'TUDO OK')
  process.exit(falhas ? 1 : 0)
})()
