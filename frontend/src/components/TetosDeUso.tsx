// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { CHAMADAS_POR_DIA_SEM_SESSAO, TETOS } from '../lib/tetos'

const n = (v: number) => v.toLocaleString('pt-BR')

/**
 * Os tetos de uso sem conta (D9), com o que acontece ao esgotá-los: 429 com `Retry-After` até a meia-noite UTC. Usado em /dados e no Sobre,
 * com os mesmos números (`lib/tetos.ts`, conferidos contra o código por `tests/unit/test_tetos_publicados.py`).
 */
export function TetosDeUso({ className = '' }: { className?: string }) {
  return (
    <div className={`space-y-2 text-sm text-gray-700 ${className}`} data-testid="tetos-de-uso">
      <ul className="list-disc space-y-1 pl-5">
        <li>
          <strong>Orçamento diário sem login:</strong> {n(TETOS.orcamentoDiarioSegundos)} s ({TETOS.orcamentoDiarioSegundos / 60} minutos) de uso das páginas avançadas e das chamadas medidas da API.
          A prévia das listas (as {100} primeiras linhas) e as páginas de entrada não gastam orçamento.
        </li>
        <li>
          <strong>Custo por chamada de script:</strong> {TETOS.custoPorChamadaSegundos} s por chamada medida de quem não tem sessão de navegador (curl, bibliotecas), ou seja, cerca de {n(CHAMADAS_POR_DIA_SEM_SESSAO)} chamadas por dia.
        </li>
        <li>
          <strong>Quem conta como um cliente:</strong> a rede do endereço de origem, IPv4 inteiro e IPv6 pelo prefixo /64. Redes que compartilham o endereço (NAT, CGNAT) dividem o orçamento dos scripts; o navegador tem sessão própria.
        </li>
        <li>
          <strong>Limitador por rede (API sem conta):</strong> {n(TETOS.apiAnonimoPorMinuto)} por minuto, {n(TETOS.apiAnonimoPorHora)} por hora e {n(TETOS.apiAnonimoPorDia)} por dia; <code>/query</code> custa 3 unidades.
        </li>
        <li>
          <strong>MCP:</strong> sem chave, prévia (até 100 itens, 1ª página, os dois snapshots mais recentes) e {n(TETOS.mcpAnonimoPorMinuto)} por minuto, {n(TETOS.mcpAnonimoPorHora)} por hora e {n(TETOS.mcpAnonimoPorDia)} por dia por rede.
          Com chave de MCP, cota de {n(TETOS.mcpCotaDiariaComChave)} requisições por dia UTC.
        </li>
      </ul>
      <p className="text-xs text-gray-600">
        Ao esgotar o orçamento a API responde <code>429</code> com <code>Retry-After</code> (segundos até a renovação, à meia-noite UTC) e um corpo que explica o limite e a saída:
        entrar com uma conta gratuita ou usar o MCP com chave. Os valores são os padrões desta instalação e podem ser ajustados por quem a opera.
      </p>
    </div>
  )
}
