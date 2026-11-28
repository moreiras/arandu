// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative, sep } from 'node:path'
import { describe, expect, it } from 'vitest'

/**
 * Lint de linguagem dos resumos em texto (diretriz do mantenedor: linguagem simples, sem vícios de IA): os geradores de frases (`sintese*.ts`) não usam o
 * contraste "é X, não Y" nem "não é X, é Y", fórmulas de transição e de efeito, nem coloquialismos como "nessa conta" e "chega-se a". Varre o código sem
 * comentários e sem testes. É uma rede de segurança por padrão de texto: não pega tríade retórica nem adjetivo de juízo, que a revisão humana confere.
 * `PENDENTES` lista geradores ainda não revisados nesta rodada; a lista só encolhe (arquivo nela que já passa também reprova).
 */
const RAIZ = join(process.cwd(), 'src')   // o vitest roda em `frontend/`

const PADROES: Array<[string, RegExp]> = [
  ['contraste "não é X, é Y"', /(?<![\wÀ-ÿ])não (é|são|foi|foram) [^.;:`]{1,60}, (mas )?(é|são|foi|foram)(?![\wÀ-ÿ])/i],
  ['contraste "é X, não Y"', /(?<![\wÀ-ÿ])(é|são) [^.;:`]{1,60}, não (é|são|um|uma|o|a|os|as)(?![\wÀ-ÿ])/i],
  ['fórmula de transição ou de efeito', /\b(vale|cabe) (notar|destacar|ressaltar|lembrar|mencionar)|\bem suma\b|\bem resumo,|\bnão por acaso\b|\bna prática,|\bde fato,|\bsem dúvida\b|\bimportante (notar|destacar|ressaltar)|\bé bom lembrar\b/i],
  ['coloquialismo', /chega-se a|\bnessa conta\b|\bnesta conta\b|\bbate com\b|\bbatem com\b|\b[Aa] conta (é|usa|soma|inclui|conta)\b/],
  ['plural entre parênteses', /\w\(s\)/],
  ['ênfase e adjetivo de efeito', /\b(simplesmente|literalmente|verdadeiramente|realmente|extremamente|incrivelmente|robust[oa]s?|crucial|crucialmente|poderos[oa]s?|impressionante)\b/i],
]

/** Geradores ainda não revisados: pertencem a outra frente de trabalho nesta rodada. */
const PENDENTES: string[] = []

function geradores(dir: string): string[] {
  return readdirSync(dir).flatMap((nome) => {
    const caminho = join(dir, nome)
    if (statSync(caminho).isDirectory()) return nome === 'test' ? [] : geradores(caminho)
    return /^sintese[A-Za-z]*\.ts$/.test(nome) ? [caminho] : []
  })
}

/** O código sem comentários de bloco e de linha. */
function semComentarios(codigo: string): string {
  return codigo
    .replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, ''))
    .split('\n')
    .map((l) => l.replace(/(^|\s)\/\/.*$/, '$1'))
    .join('\n')
}

function achados(codigo: string): string[] {
  const limpo = semComentarios(codigo)
  return PADROES.filter(([, re]) => re.test(limpo)).map(([nome]) => nome)
}

describe('fórmulas de linguagem de IA nos resumos em texto', () => {
  const todos = geradores(RAIZ).map((a) => ({ caminho: relative(RAIZ, a).split(sep).join('/'), codigo: readFileSync(a, 'utf8') }))

  it('encontra os geradores de frases', () => {
    expect(todos.length).toBeGreaterThanOrEqual(14)
    expect(PENDENTES.filter((p) => !todos.some((t) => t.caminho === p))).toEqual([])
  })

  it('nenhum gerador revisado usa as fórmulas proibidas', () => {
    const falhas = todos.filter((t) => !PENDENTES.includes(t.caminho)).flatMap((t) => achados(t.codigo).map((a) => `${t.caminho}: ${a}`))
    expect(falhas).toEqual([])
  })

  it('gerador da lista de pendentes que já passa sai da lista', () => {
    expect(todos.filter((t) => PENDENTES.includes(t.caminho) && achados(t.codigo).length === 0).map((t) => t.caminho)).toEqual([])
  })

  it('o detector reconhece as fórmulas e deixa passar a frase simples', () => {
    expect(achados("texto: 'É uma estimativa, não um censo.'").length).toBeGreaterThan(0)
    expect(achados("texto: 'Isso não é opinião, é medição.'").length).toBeGreaterThan(0)
    expect(achados("texto: 'Um bloco alocado e não anunciado não entra nessa conta.'")).toContain('coloquialismo')
    expect(achados("texto: 'Vale notar que o total muda.'").length).toBeGreaterThan(0)
    expect(achados("texto: 'A UF é a da sede, não a de operação.'").length).toBeGreaterThan(0)
    expect(achados("texto: 'Esse número é estimado pelo APNIC a partir de amostras de anúncios.'")).toEqual([])
    expect(achados("// A UF é a da sede, não a de operação.\nconst a = 1")).toEqual([])
  })
})
