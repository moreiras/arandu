// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { nomeExibicao } from './nomes'

describe('nomeExibicao', () => {
  it('ajusta caixa, acentos conhecidos e siglas societárias', () => {
    expect(nomeExibicao('BRISANET SERVICOS DE TELECOMUNICACOES S.A.')).toBe('Brisanet Serviços de Telecomunicações S.A.')
    expect(nomeExibicao('FULANO INFORMATICA LTDA ME')).toBe('Fulano Informática LTDA ME')
  })
  it('não mexe em nome que já está em caixa mista nem inventa acento', () => {
    expect(nomeExibicao('Claro S.A.')).toBe('Claro S.A.')
    expect(nomeExibicao('PROVEDOR ZEBRA LTDA')).toBe('Provedor Zebra LTDA')
  })
  it('mantém identificadores e siglas curtas', () => {
    expect(nomeExibicao('AS64500')).toBe('AS64500')
    expect(nomeExibicao('TIM CELULAR S.A.')).toBe('TIM Celular S.A.')
  })
  it('vazio e espaços', () => {
    expect(nomeExibicao(null)).toBe('')
    expect(nomeExibicao('  TESTE   DE  REDE ')).toBe('Teste de Rede')
  })
})
