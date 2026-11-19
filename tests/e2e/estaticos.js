// Arquivos de descoberta (gerados pela API): o nginx tem de servi-los, não o index.html do SPA.
//   BASE_URL=http://host.docker.internal:18080 node estaticos.js
const BASE = process.env.BASE_URL || 'http://localhost:18080'
const ESPERADO = [
  ['/sitemap.xml', /xml/, /^<\?xml[\s\S]*<sitemapindex/],
  ['/sitemap-paginas.xml', /xml/, /^<\?xml[\s\S]*<urlset/],
  ['/robots.txt', /text\/plain/, /^User-agent: \*[\s\S]*Sitemap:/],
  ['/llms.txt', /text\/plain/, /^# \S/],
  ['/catalogo.json', /json/, /^\{"versao_esquema":1,"fontes":\[/],
]
;(async () => {
  let fails = 0
  for (const [path, tipo, corpo] of ESPERADO) {
    const r = await fetch(BASE + path)
    const txt = await r.text()
    const ok = r.status === 200 && tipo.test(r.headers.get('content-type') || '') && corpo.test(txt)
    console.log(`${ok ? 'ok  ' : 'FAIL'} - ${path}: ${r.status} ${r.headers.get('content-type')} ${txt.length} bytes`)
    if (!ok) fails += 1
  }
  process.exit(fails ? 1 : 0)
})()
