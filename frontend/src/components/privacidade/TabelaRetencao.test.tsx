// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TabelaRetencao } from './TabelaRetencao'
import retencao from '../../lib/retencao.gen.json'
import { Privacidade } from '../../pages/Privacidade'

describe('TabelaRetencao (D10)', () => {
  it('mostra uma linha por registro do JSON gerado, com prazo e indicação de IP', () => {
    render(<TabelaRetencao />)
    expect(screen.getAllByRole('row')).toHaveLength(retencao.linhas.length + 1)
    for (const l of retencao.linhas) {
      expect(screen.getByText(l.registro)).toBeTruthy()
      expect(screen.getAllByText(l.prazo).length).toBeGreaterThan(0)
    }
  })

  it('a página /privacidade exibe a tabela com todas as linhas do JSON gerado', () => {
    render(<Privacidade />)
    expect(screen.getByText('Registros e prazos de retenção')).toBeTruthy()
    for (const l of retencao.linhas) expect(screen.getAllByText(l.registro).length).toBeGreaterThan(0)
  })

  it('a linha do servidor web diz tempo indeterminado, sem valores de rotação', () => {
    const l = retencao.linhas.find(x => x.id === 'log_servidor_web')!
    expect(l.prazo).toBe('tempo indeterminado')
    expect(l.prazo).not.toMatch(/\d|rotação/)
  })
})

describe('Privacidade: textos aprovados (PT-13b)', () => {
  const texto = () => {
    render(<Privacidade />)
    return (document.body.textContent ?? '').replace(/\s+/g, ' ')
  }

  it('(a) servidor web com IP e prazo indeterminado, sem números de rotação, e última frase sem negar o IP do log de páginas', () => {
    const t = texto()
    expect(t).toContain('O servidor web registra, a cada acesso, o endereço IP, a URL acessada e o horário, para operação e segurança do serviço. Esse registro é mantido por tempo indeterminado.')
    expect(t).toContain('Os registros de uso descritos na seção 2.2 não guardam o endereço IP; o registro de páginas visitadas por quem tem conta, descrito na seção 2.3, guarda.')
    expect(t).not.toContain('Os registros da própria aplicação')
    expect(t).not.toMatch(/\d+ ?MB|\d+ arquivos|rotação por tamanho/)
  })

  it('(a) não contradiz (e): nenhuma frase afirma que nenhum registro da aplicação guarda IP', () => {
    const t = texto()
    expect(t).not.toMatch(/(registros|registro) da (própria )?aplicação[^.]*não guardam? o endereço IP/)
    expect(t).toContain('endereço IP e caminho da página, por 3 meses')
  })

  it('(b) contagens por dia, conta, origem e classe de rota', () => {
    expect(texto()).toContain('ficam apenas contagens por dia, conta, origem da chamada (site, API ou MCP) e classe de rota, por até 12 meses. O identificador interno da conta só é retirado dessas contagens quando a conta é excluída.')
  })

  it('(c) tetos de chamadas do MCP', () => {
    const t = texto()
    expect(t).toContain('os tetos de chamadas do MCP por minuto, por hora e por dia')
    expect(t).not.toContain('limite diário de chamadas do MCP')
  })

  it('(d) seção 2.5 sobre localStorage', () => {
    const t = texto()
    expect(t).toContain('2.5 Armazenamento no navegador')
    expect(t).toContain('O site guarda no armazenamento local do seu navegador (localStorage) a sua preferência de leitura confortável, as buscas recentes da barra de busca e a orientação do mapa. Esses dados ficam só no seu navegador, não são enviados ao servidor e deixam de existir quando você limpa os dados do site.')
  })

  it('(e) log de páginas de quem tem conta, com IP e 3 meses', () => {
    expect(texto()).toContain('Para quem tem conta, as páginas visitadas no site também são registradas com data e hora, identificador interno da conta, endereço IP e caminho da página, por 3 meses.')
  })
})
