// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { linkPermanente, montarCitacao } from './citacao'

describe('citar este dado', () => {
  it('link permanente fixa o snapshot, mantém a aba e leva à âncora do bloco', () => {
    expect(linkPermanente('https://exemplo.example', '/asn/64496', '?aba=rede', '2026-11-05', 'transito'))
      .toBe('https://exemplo.example/asn/64496?aba=rede&date=2026-11-05#bloco-transito')
    expect(linkPermanente('https://x', '/uf/ES', '', null)).toBe('https://x/uf/ES')
  })

  it('o texto traz entidade, bloco, fonte com referência, snapshot, link e data de acesso, sem inventar o que não há', () => {
    const t = montarCitacao({ entidade: 'AS64496 · Rede Exemplo', bloco: 'Prefixos anunciados', valor: '1.204 prefixos IPv4', fontes: ['fulltable_routeviews', 'registro_br'],
      fontesEntradas: [{ id: 'fulltable_routeviews', as_of: '2026-11-04' }], snapshot: '2026-11-05', url: 'https://x/asn/64496?date=2026-11-05', acessoEm: new Date(2026, 10, 12) })
    expect(t).toContain('AS64496 · Rede Exemplo: Prefixos anunciados — 1.204 prefixos IPv4.')
    expect(t).toContain('Fontes: fulltable_routeviews (referência 04/11/2026); registro_br.')
    expect(t).toContain('Snapshot de 05/11/2026.')
    expect(t).toContain('Disponível em: https://x/asn/64496?date=2026-11-05.')
    expect(t).toContain('Acesso em: 12/11/2026.')
    expect(montarCitacao({ entidade: 'E', bloco: 'B', fontes: [], url: 'u', acessoEm: new Date(2026, 0, 2) })).not.toContain('Fonte')
  })
})
