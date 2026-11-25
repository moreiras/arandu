// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Os universos de contagem (PT-15): cada rótulo designa um só universo, e o texto de `/sobre#contagens` sai da mesma tabela. */
import { describe, expect, it } from 'vitest'
import { LISTA_UNIVERSOS, RELACAO_PTT, rotuloDe, UNIVERSOS, type ChaveUniverso } from './universos'

describe('universos de contagem', () => {
  it('o mesmo rótulo nunca designa dois universos, e nenhuma definição fica vazia', () => {
    const rotulos = LISTA_UNIVERSOS.map((u) => u.rotulo.toLowerCase())
    expect(new Set(rotulos).size).toBe(rotulos.length)
    for (const u of LISTA_UNIVERSOS) expect(u.definicao.length, u.chave).toBeGreaterThan(20)
  })

  it('as duas listas de ASNs brasileiros têm nomes distintos: a delegação da LACNIC e a lista do Registro.br', () => {
    expect(rotuloDe('asnsLacnic')).toBe('ASNs brasileiros (delegados pela LACNIC ao Brasil)')
    expect(rotuloDe('asnsRegistroBr')).toBe('ASNs na lista do Registro.br')
    expect(rotuloDe('asnsRegistroBr')).not.toBe(rotuloDe('asnsLacnic'))
  })

  it('sessão em route server, cadastro de participantes e originador são três rótulos, e sessão não se chama peering direto', () => {
    const tres: ChaveUniverso[] = ['sessaoRs', 'membroCadastro', 'originadores']
    expect(new Set(tres.map(rotuloDe)).size).toBe(3)
    expect(rotuloDe('sessaoRs')).toBe('ASNs com sessão em route server do IX.br')
    expect(rotuloDe('sessaoRsBr')).toContain('brasileiros')
    for (const k of Object.keys(UNIVERSOS) as ChaveUniverso[]) expect(rotuloDe(k)).not.toMatch(/peering direto/i)
  })

  it('rótulos curtos da relação com o PTT: sessão no route server e cadastro são distintos e nenhum se chama peering direto', () => {
    expect(RELACAO_PTT.sessaoRs).not.toBe(RELACAO_PTT.membroCadastro)
    for (const v of Object.values(RELACAO_PTT)) expect(v).not.toMatch(/peering direto|peers? diretos?|par direto/i)
  })

  it('os três universos de declarantes do SICI e os dois de municípios têm rótulo próprio', () => {
    const sici: ChaveUniverso[] = ['declarantesFixo', 'scmDeclarantes', 'scmFixoOuMovel']
    expect(new Set(sici.map(rotuloDe)).size).toBe(3)
    expect(rotuloDe('municipiosIbge')).not.toBe(rotuloDe('municipiosCenso'))
  })

  it('usuários do APNIC: por país, por UF da sede, por PTT (não aditivo) e pelo IX.br sem dupla contagem têm rótulos distintos', () => {
    const usuarios: ChaveUniverso[] = ['usuariosPais', 'usuariosUf', 'usuariosPtt', 'usuariosIx']
    expect(new Set(usuarios.map(rotuloDe)).size).toBe(4)
    expect(UNIVERSOS.usuariosPtt.definicao).toMatch(/Não aditivos/)
    expect(rotuloDe('usuariosUf')).toMatch(/sede/)
  })
})
