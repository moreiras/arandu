// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative, sep } from 'node:path'
import { describe, expect, it } from 'vitest'
import { ARQUIVOS_COM_TRAVESSAO } from './semTravessaoAllowlist'

/**
 * Lint de travessão (PT-30): o texto exibido na interface não usa "—" nem "–" como pontuação (diretriz de apresentação e linguagem do mantenedor).
 * Varre `frontend/src` sem comentários, testes, `test/` e `types/openapi*`. Duas exceções de forma:
 * - o travessão sozinho como valor ausente ("—" no lugar do dado que falta), que não é pontuação (`'—'`, `"—"`, `>—<`);
 * - os arquivos de `ARQUIVOS_COM_TRAVESSAO`, que ainda não foram revisados.
 * A lista só encolhe: arquivo fora dela com travessão reprova; arquivo nela que já não tem travessão também reprova (tire-o da lista).
 */
const RAIZ = join(process.cwd(), 'src')   // o vitest roda em `frontend/`
const TRAVESSAO = /[—–]/

function arquivos(dir: string): string[] {
  return readdirSync(dir).flatMap((nome) => {
    const caminho = join(dir, nome)
    if (statSync(caminho).isDirectory()) return nome === 'test' ? [] : arquivos(caminho)
    if (!/\.(ts|tsx)$/.test(nome) || /\.test\.(ts|tsx)$/.test(nome) || /^openapi/.test(nome)) return []
    return [caminho]
  })
}

/** O texto de código sem comentários de bloco, de linha e sem o travessão-valor-ausente. */
export function semComentarios(codigo: string): string {
  return codigo
    .replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, ''))
    .split('\n')
    .map((l) => l.replace(/(^|\s)\/\/.*$/, '$1'))
    .map((l) => l.replace(/(['"`])[—–]\1/g, '').replace(/>\s*[—–]\s*</g, '><'))
    .join('\n')
}

export function linhasComTravessao(codigo: string): number[] {
  return semComentarios(codigo).split('\n').flatMap((l, i) => (TRAVESSAO.test(l) ? [i + 1] : []))
}

describe('travessão no texto da interface', () => {
  const todos = arquivos(RAIZ).map((a) => ({ caminho: relative(RAIZ, a).split(sep).join('/'), codigo: readFileSync(a, 'utf8') }))
  const permitidos = new Set(ARQUIVOS_COM_TRAVESSAO)

  it('a lista de arquivos pendentes aponta para arquivos que existem, sem repetição', () => {
    const existentes = new Set(todos.map((t) => t.caminho))
    expect(ARQUIVOS_COM_TRAVESSAO.filter((c) => !existentes.has(c))).toEqual([])
    expect(permitidos.size).toBe(ARQUIVOS_COM_TRAVESSAO.length)
  })

  it('nenhum arquivo fora da lista de pendentes usa travessão', () => {
    const falhas = todos.filter((t) => !permitidos.has(t.caminho)).flatMap((t) => linhasComTravessao(t.codigo).map((n) => `${t.caminho}:${n}`))
    expect(falhas).toEqual([])
  })

  it('arquivo da lista de pendentes que já não tem travessão sai da lista', () => {
    const limpos = todos.filter((t) => permitidos.has(t.caminho) && linhasComTravessao(t.codigo).length === 0).map((t) => t.caminho)
    expect(limpos).toEqual([])
  })

  it('o detector reconhece travessão no texto e ignora comentário e valor ausente', () => {
    expect(linhasComTravessao("const a = 'x — y'")).toEqual([1])
    expect(linhasComTravessao('<p>de 1 – 3</p>')).toEqual([1])
    expect(linhasComTravessao("// comentário — ok\n/* bloco — ok */\nconst v = x ?? '—'\n<td>—</td>")).toEqual([])
    expect(linhasComTravessao("const u = 'https://exemplo.org'\nconst t = 'a — b'")).toEqual([2])
  })
})
