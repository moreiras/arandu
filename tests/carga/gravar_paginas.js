// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
//
// Grava o que cada tipo de página pede ao servidor (HTML, estáticos, tiles, API), para o Locust repetir sem navegador.
// A entidade visitada (ASN, PTT, CNPJ, município, UF, prefixo) vira marcador ({asn}, {code}…) em caminho, query e corpo.
//   docker run --rm -v $PWD/tests/carga:/carga -w /carga -e BASE_URL=http://HOST -e XFF=IP_DA_ALLOWLIST \
//     mcr.microsoft.com/playwright:v1.49.0-jammy bash -c "npm i playwright@1.49.0 >/dev/null 2>&1 && node gravar_paginas.js"
// Saída: saida/paginas.json ({pagina: {caminho, requisicoes: [{metodo, url, tipo, range, corpo, bytes}]}}).
const { chromium } = require('playwright')
const fs = require('fs')

const BASE = process.env.BASE_URL || 'http://localhost:18080'
const XFF = process.env.XFF || '127.0.0.1'                 // IP da allowlist do alvo (sem orçamento anônimo na gravação)
const SAIDA = process.env.SAIDA || 'saida/paginas.json'
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

async function entidades(ctx) {
  const get = async (p) => (await ctx.request.get(BASE + p)).json()
  const data = (await get('/health')).latest_snapshot
  const asns = (await get('/api/v1/asns?limit=20&br_only=true&sort_by=apnic_users&sort_desc=true')).items
  const ixps = (await get('/api/v1/ixps')).ixps
  const ops = (await get('/api/v1/acessos/operadoras?limit=20')).items
  const mun = (await get('/api/v1/acessos/municipios')).items
  const pref = (await get('/api/v1/prefixes?limit=20')).items
  // valores que não se repetem entre si (senão o marcador fica ambíguo); evita a 1ª de cada lista (SP, por exemplo, aparece em toda parte)
  const a = asns.slice(1).find((x) => x.cnpj)
  const op = ops.slice(1).find((x) => x.cnpj !== a.cnpj)
  const pr = pref.slice(1).find((x) => x.origin_asn && String(x.origin_asn) !== String(a.asn))
  const m = mun.slice(1).find((x) => x.uf !== 'SP') || mun[1]
  // dependentes: a página do ASN consulta o grupo do CNPJ dele; a da operadora, a raiz do CNPJ; a do prefixo, o ASN de origem
  return {
    data, asn: String(a.asn), asn_cnpj: a.cnpj, code: ixps[1].code, cnpj: op.cnpj, cnpj8: op.cnpj.slice(0, 8),
    ibge: String(m.ibge), uf: m.uf, prefixo: pr.prefix, prefixo_asn: String(pr.origin_asn),
  }
}

// troca o valor da entidade pelo marcador só quando ele é um "token" inteiro (entre / = , & ? ou fim), cru ou codificado
function marcar(texto, ent) {
  if (!texto) return texto
  let t = texto
  for (const [k, v] of Object.entries(ent).sort((x, y) => String(y[1]).length - String(x[1]).length)) {
    for (const forma of new Set([v, encodeURIComponent(v)])) {
      const esc = forma.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      t = t.replace(new RegExp(`(^|[/=,&?:"\\[ ])${esc}(?=$|[/=,&?#"\\], ])`, 'g'), `$1{${k}}`)
    }
  }
  return t
}

function tipo(url, resourceType) {
  const p = new URL(url).pathname
  if (resourceType === 'document') return 'documento'
  if (p.startsWith('/api/') || p.startsWith('/auth/') || p === '/health') return 'api'
  if (p.startsWith('/tiles/')) return 'tiles'
  return 'estatico'
}

;(async () => {
  const browser = await chromium.launch()
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, extraHTTPHeaders: { 'X-Forwarded-For': XFF } })
  const ent = await entidades(ctx)
  const paginas = {
    home: '/', explorar: '/explorar', panorama_tecnico: '/panorama/tecnico', panorama_mercado: '/panorama/mercado',
    asn: `/asn/${ent.asn}`, ptt: `/ixp/${ent.code}`, operadora: `/operadora/${ent.cnpj}`, municipio: `/municipio/${ent.ibge}`,
    uf: `/uf/${ent.uf}`, prefixo: `/prefixo/${ent.prefixo}`, mapa: '/mapa', bgp: '/bgp', mudancas: '/mudancas', rankings: '/rankings',
    ases: '/ases', municipios: '/municipios', operadoras: '/operadoras?visao=ranking', qualidade: '/qualidade',
    seguranca_roteamento: '/seguranca-de-roteamento', uso_da_internet: '/uso-da-internet',
  }
  const out = { gravado_em: new Date().toISOString(), marcadores: Object.keys(ent), paginas: {} }
  for (const [nome, caminho] of Object.entries(paginas)) {
    const page = await ctx.newPage()
    const reqs = []
    const pend = []
    page.on('requestfinished', (req) => {
      if (!req.url().startsWith(BASE)) return
      pend.push(req.sizes().then(async (s) => {
        const h = await req.allHeaders()
        const resp = await req.response()
        reqs.push({
          metodo: req.method(), url: marcar(req.url().slice(BASE.length), ent), tipo: tipo(req.url(), req.resourceType()),
          range: h.range || null, corpo: req.method() === 'GET' ? null : marcar(req.postData(), ent),
          status: resp ? resp.status() : null, bytes: s.responseBodySize || 0,
        })
      }).catch(() => {}))
    })
    const t0 = Date.now()
    await page.goto(BASE + caminho, { waitUntil: 'networkidle', timeout: 90000 }).catch(() => {})
    await wait(2000)
    await Promise.all(pend)
    out.paginas[nome] = { caminho: marcar(caminho, ent), ms_ate_ocioso: Date.now() - t0, requisicoes: reqs }
    const n = (t) => reqs.filter((r) => r.tipo === t).length
    console.log(`${nome.padEnd(22)} api=${n('api')} estaticos=${n('estatico')} tiles=${n('tiles')} ` +
      `MB=${(reqs.reduce((a, r) => a + r.bytes, 0) / 1e6).toFixed(1)} erros=${reqs.filter((r) => r.status >= 400).length}`)
    await page.close()
  }
  fs.mkdirSync(require('path').dirname(SAIDA), { recursive: true })
  fs.writeFileSync(SAIDA, JSON.stringify(out, null, 1))
  await browser.close()
})()
