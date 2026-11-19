// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
//
// HTML montado em texto para popups de mapa e dicas de grafo. Nomes de AS, razões sociais e
// cadastros do PeeringDB são texto de terceiros: interpolados crus em `setHTML`/`innerHTML`, viravam HTML. A CSP impede script, mas não um
// link falso ou conteúdo enganoso dentro do popup.
//
// Use a tag `html` em vez da crase pura: toda interpolação é escapada; só o que vem de `cru(...)` (HTML já montado aqui, por outra chamada de
// `html` ou constante do código) entra como está.

const ENTIDADES: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }

/** Texto qualquer pronto para ir dentro de HTML (conteúdo ou valor de atributo entre aspas). */
export function escapar(v: unknown): string {
  return String(v ?? '').replace(/[&<>"']/g, (c) => ENTIDADES[c])
}

/** HTML confiável (montado pelo próprio código). Só ele atravessa a tag `html` sem escape. */
export class HtmlSeguro {
  constructor(readonly valor: string) {}
  toString(): string {
    return this.valor
  }
}

/** Marca como confiável um trecho de HTML montado pelo código (nunca texto vindo de dado). */
export function cru(valor: string | HtmlSeguro): HtmlSeguro {
  return valor instanceof HtmlSeguro ? valor : new HtmlSeguro(valor)
}

function parte(v: unknown): string {
  if (v instanceof HtmlSeguro) return v.valor
  if (Array.isArray(v)) return v.map(parte).join('')
  return escapar(v)
}

/** Template de HTML com escape automático: html`<strong>${nome}</strong>` escapa `nome`; listas são concatenadas, cada item escapado. */
export function html(partes: TemplateStringsArray, ...valores: unknown[]): string {
  let out = partes[0]
  valores.forEach((v, i) => {
    out += parte(v) + partes[i + 1]
  })
  return out
}

/** Como `html`, mas devolve um trecho confiável para ser interpolado em outro `html` sem ser escapado de novo. */
export function htmlSeguro(partes: TemplateStringsArray, ...valores: unknown[]): HtmlSeguro {
  return new HtmlSeguro(html(partes, ...valores))
}
