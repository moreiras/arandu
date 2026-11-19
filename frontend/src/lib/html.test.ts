// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { cru, escapar, html, htmlSeguro } from './html'

describe('html com escape', () => {
  it('escapa toda interpolação; só o que é seguro passa', () => {
    const r = semTemplatesSeguros('a html`<b>${x ? htmlSeguro`<i>${y}</i>` : `${z}`}</b>\n c` d `<u>${w}</u>`')
    expect(r.startsWith('a html`')).toBe(true)
    expect(r.split('\n')).toHaveLength(2)
    expect(r.endsWith('` d `<u>${w}</u>`')).toBe(true)          // template sem tag continua visível para a guarda
    expect(r.slice(0, r.indexOf('` d'))).not.toMatch(/[<$]/)
    const nome = '<img src=x onerror=alert(1)> & "AS" \'x\''
    expect(escapar(nome)).toBe('&lt;img src=x onerror=alert(1)&gt; &amp; &quot;AS&quot; &#39;x&#39;')
    expect(html`<b>${nome}</b>`).toBe(`<b>${escapar(nome)}</b>`)
    expect(html`<i>${cru('<br/>')}</i>`).toBe('<i><br/></i>')
    expect(html`<p>${htmlSeguro`<b>${nome}</b>`}</p>`).toBe(`<p><b>${escapar(nome)}</b></p>`)
    expect(html`<p>${[nome, cru('<br/>')]}</p>`).toBe(`<p>${escapar(nome)}<br/></p>`)
    expect(html`${null}|${undefined}|${0}`).toBe('||0')
  })
})

// Guarda estática: nos arquivos que entregam texto a `setHTML`/`innerHTML`/`dangerouslySetInnerHTML`, toda interpolação numa linha de HTML
// (template com `<`) passa por `escapar(...)`, está num template com a tag `html`/`htmlSeguro`, ou é um trecho de HTML montado pelo código
// (lista abaixo). Nomes de AS, razões sociais e cadastros do PeeringDB são texto de terceiros.
function arquivos(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n)
    return statSync(p).isDirectory() ? arquivos(p) : /\.(ts|tsx)$/.test(n) && !/\.test\.tsx?$/.test(n) ? [p] : []
  })
}
// Fim de um template (índice da crase de fechamento), a partir do caractere logo depois da crase de abertura; atravessa `${…}` aninhados.
function fimDoTemplate(src: string, i: number): number {
  for (; i < src.length; i++) {
    const c = src[i]
    if (c === '\\') { i++; continue }
    if (c === '`') return i
    if (c === '$' && src[i + 1] === '{') i = fimDaExpressao(src, i + 2) - 1
  }
  return src.length
}
function fimDaExpressao(src: string, i: number): number {
  let prof = 1
  for (; i < src.length; i++) {
    const c = src[i]
    if (c === '`') { i = fimDoTemplate(src, i + 1); continue }
    if (c === "'" || c === '"') { const f = src.indexOf(c, i + 1); i = f < 0 ? src.length : f; continue }
    if (c === '{') prof++
    else if (c === '}' && --prof === 0) return i + 1
  }
  return src.length
}
/** O fonte com os templates de tag `html`/`htmlSeguro` (que escapam sozinhos) apagados, preservando as quebras de linha. */
function semTemplatesSeguros(src: string): string {
  let out = ''
  let i = 0
  const rx = /\b(?:html|htmlSeguro)`/g
  for (let m = rx.exec(src); m; m = rx.exec(src)) {
    if (m.index < i) continue
    const ini = m.index + m[0].length
    const fim = fimDoTemplate(src, ini)
    out += src.slice(i, ini) + src.slice(ini, fim).replace(/[^\n]/g, ' ')
    i = fim
    rx.lastIndex = fim + 1
  }
  return out + src.slice(i)
}
const RAIZ = join(__dirname, '..')
const HTML_DO_CODIGO = new Set(['SCM_TAG', 'SCM_BADGE', 'CNPJ_COLOR', 'COLOR_SCM', 'badge', 'body', 'share', 'asnsLine',
  'cov(entry.br_asns_direct_union_count)', 'cov(entry.br_asns_origin_union_count)'])

describe('HTML montado em texto não interpola dado sem escape', () => {
  it('toda interpolação em linha de HTML é escapada', () => {
    const consumidores = arquivos(RAIZ).filter((p) => /setHTML\(|innerHTML\s*=|dangerouslySetInnerHTML/.test(readFileSync(p, 'utf8')))
    // os que montam o HTML para outro arquivo (popups do explorador, balões do Localizador, popup de instalações)
    const construtores = ['components/maps/explorer/popups.ts', 'features/localizador/balloes.ts', 'features/instalacoes/comum.tsx'].map((r) => join(RAIZ, r))
    const crus: string[] = []
    for (const p of [...new Set([...consumidores, ...construtores])]) {
      semTemplatesSeguros(readFileSync(p, 'utf8')).split('\n').forEach((l, i) => {
        if (!l.includes('`') || !l.includes('<') || /className=|^\s*(\/\/|\*)/.test(l)) return
        for (const m of l.matchAll(/\$\{([^{}`]+)\}/g)) {
          const e = m[1].trim()
          if (e.startsWith('escapar(') || HTML_DO_CODIGO.has(e)) continue
          crus.push(`${p.slice(RAIZ.length + 1)}:${i + 1}: \${${e}}`)
        }
      })
    }
    expect(crus).toEqual([])
  })
})
