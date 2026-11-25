// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { avisoLinkCitacao, linkPermanente, montarCitacao } from './citacao'

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
    expect(t).toContain('Fontes: fulltable_routeviews (referência 04/11/2026); registro_br (data de referência não informada).')
    expect(t).toContain('Snapshot de 05/11/2026.')
    expect(t).toContain('Disponível em: https://x/asn/64496?date=2026-11-05.')
    expect(t).toContain('Acesso em: 12/11/2026.')
    expect(montarCitacao({ entidade: 'E', bloco: 'B', fontes: [], url: 'u', acessoEm: new Date(2026, 0, 2) })).not.toContain('Fonte')
  })

  it('a citação é autossuficiente: leva os valores, o snapshot e as fontes com as datas (D3), com o aviso do prazo do link', () => {
    const t = montarCitacao({ entidade: 'Município de Vitória/ES', bloco: 'Banda larga fixa',
      valores: [{ rotulo: 'Acessos fixos', valor: '123.456' }, { rotulo: 'Sem dado', valor: '—' }, { rotulo: 'Operadoras', valor: '12' }],
      fontes: ['anatel_sici', 'curada_pix'], fontesEntradas: [{ id: 'anatel_sici', as_of: '2026-09' }], snapshot: '2026-11-08',
      url: 'https://x/municipio/3205309?date=2026-11-08', acessoEm: new Date(2026, 10, 25) })
    expect(t).toContain('Valores: Acessos fixos: 123.456; Operadoras: 12.')
    expect(t).not.toContain('Sem dado')                                     // valor ausente nunca entra como número
    expect(t).toContain('anatel_sici (referência 09/2026)')
    expect(t).toContain('curada_pix (data de referência não informada)')    // sem inventar a data da fonte
    expect(t).toContain('Snapshot de 08/11/2026.')
    expect(t).toContain('O endereço abre sem login enquanto o snapshot é um dos dois mais recentes; depois exige login.')
  })

  it('o aviso diz até quando o link abre sem login e quando já exige', () => {
    expect(avisoLinkCitacao('2026-11-15', ['2026-11-15', '2026-11-22'])).toMatch(/abre sem login enquanto o snapshot de 15\/11\/2026 estiver entre os dois mais recentes \(hoje: 15\/11\/2026 e 22\/11\/2026\).*duas semanas.*Depois exige login/)
    expect(avisoLinkCitacao('2026-11-08', ['2026-11-15', '2026-11-22'])).toMatch(/já não está entre os dois mais recentes.*exige login/)
    expect(avisoLinkCitacao(null, null)).toMatch(/mais recente/)
  })
})
