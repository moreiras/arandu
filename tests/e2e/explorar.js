// Explorador de consultas: cobertura de 100% das coleções do /schema e latência (p95) da consulta padrão de cada uma.
//   BASE_URL=http://host.docker.internal:18080 node explorar.js
// Para cada coleção: (1) a consulta padrão (25 linhas, sem filtro) responde 200 pela API e (2) a página /explorar abre a mesma consulta pela URL
// e mostra a tabela de resultado. Mede N chamadas e confere o p95 contra o teto (P95_MAX_MS, padrão 3000 ms).
const { chromium } = require('playwright')

const BASE = process.env.BASE_URL || 'http://localhost:18080'
const N = Number(process.env.REPETICOES || 12)
const P95_MAX_MS = Number(process.env.P95_MAX_MS || 3000)
const wait = (ms) => new Promise((r) => setTimeout(r, ms))
const p95 = (xs) => [...xs].sort((a, b) => a - b)[Math.min(xs.length - 1, Math.ceil(xs.length * 0.95) - 1)]

function urlDaConsulta(colecao) {
  const estado = { modo: 'lista', juncao: 'and', condicoes: [], colunas: [], ordem: null, limite: 25, pagina: 1, perto: null, agrupar: [], agregados: [{ fn: 'count', campo: '' }] }
  const q = Buffer.from(JSON.stringify(estado)).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
  return `/explorar?c=${encodeURIComponent(colecao)}&q=${q}`
}

;(async () => {
  const browser = await chromium.launch()
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, extraHTTPHeaders: { 'X-Forwarded-For': '203.0.113.129' } })
  const schema = await (await ctx.request.get(BASE + '/api/v1/schema')).json()
  const colecoes = Object.keys(schema.collections)
  let fails = 0
  console.log(`${colecoes.length} coleções no schema`)
  for (const col of colecoes) {
    const tempos = []
    let status = 0
    for (let i = 0; i < N; i++) {
      const t = Date.now()
      const r = await ctx.request.post(`${BASE}/api/v1/query/${col}`, { data: { limit: 25 }, headers: { 'X-Forwarded-For': `203.0.113.${128 + (i * 13 + col.length * 7) % 127}` } })
      tempos.push(Date.now() - t); status = r.status()
    }
    const page = await ctx.newPage()
    await page.goto(BASE + urlDaConsulta(col), { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {})
    await wait(800)
    const tabela = await page.getByRole('table', { name: 'Resultado' }).count()
    const vazio = await page.getByText('Nenhuma linha atende à consulta').count()
    const erro = await page.getByRole('alert').count()
    await page.close()
    const lento = p95(tempos) > P95_MAX_MS
    const ok = status === 200 && (tabela > 0 || vazio > 0) && !erro && !lento
    console.log(`${ok ? 'ok  ' : 'FAIL'} - ${col.padEnd(24)} API ${status}  p95 ${p95(tempos)} ms  tela: ${tabela ? 'tabela' : vazio ? 'vazio' : 'sem resultado'}${erro ? ' + ERRO' : ''}${lento ? ' (lento)' : ''}`)
    if (!ok) fails += 1
  }
  await browser.close()
  console.log(fails ? `${fails} coleção(ões) com problema` : `TODAS AS ${colecoes.length} COLEÇÕES OK`)
  process.exit(fails ? 1 : 0)
})()
