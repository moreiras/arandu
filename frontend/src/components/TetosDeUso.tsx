// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useLimites } from '../hooks/useLimites'
import { descreverJanelas, numeroBR as n } from '../lib/limites'

/**
 * Os tetos de uso (D9), com o que acontece ao esgotá-los: 429 com `Retry-After` até a meia-noite UTC. Usado no Sobre; todo número vem de
 * `GET /api/v1/limites` (lido do código e da configuração do servidor), nenhum é escrito aqui.
 */
export function TetosDeUso({ className = '' }: { className?: string }) {
  const { data: L, isError } = useLimites()
  if (isError) {
    return <p className={`text-sm text-gray-600 ${className}`} role="status">Os limites de uso não puderam ser carregados agora. Eles estão em <a className="text-primario-600 hover:underline" href="/api/v1/limites">/api/v1/limites</a>.</p>
  }
  if (!L) return <p className={`text-sm text-gray-500 ${className}`} role="status">Carregando os limites de uso…</p>
  const s = L.sem_conta
  const ch = L.mcp.chave
  return (
    <div className={`space-y-2 text-sm text-gray-700 ${className}`} data-testid="tetos-de-uso">
      <ul className="list-disc space-y-1 pl-5">
        <li>
          <strong>Orçamento diário sem login:</strong> {n(s.orcamento_diario_segundos)} s ({n(s.orcamento_diario_segundos / 60)} minutos) de uso das páginas avançadas e das chamadas medidas da API.
          A prévia das listas (as {s.previa_linhas} primeiras linhas) e as páginas de entrada não gastam orçamento.
        </li>
        <li>
          <strong>Custo por chamada de script:</strong> {s.custo_por_chamada_segundos} s por chamada medida de quem não tem sessão de navegador (curl, bibliotecas)
          {s.chamadas_medidas_por_dia != null ? <>, ou seja, cerca de {n(s.chamadas_medidas_por_dia)} chamadas por dia</> : null}.
        </li>
        <li>
          <strong>Quem conta como um cliente:</strong> a rede do endereço de origem, IPv4 inteiro e IPv6 pelo prefixo /64. Redes que compartilham o endereço (NAT, CGNAT) dividem o orçamento dos scripts; o navegador tem sessão própria.
        </li>
        <li>
          <strong>Limitador por rede (API sem conta):</strong> {descreverJanelas(L.api.sem_conta)}; <code>/query</code> custa {L.api.custo_por_rota['/api/v1/query']} unidades.
        </li>
        <li>
          <strong>MCP:</strong> sem chave, prévia (até {s.previa_linhas} itens, 1ª página, os {s.snapshots_atuais} snapshots mais recentes) e {descreverJanelas(L.mcp.sem_chave)} por rede.
          {ch.ativa ? <> Com chave de MCP, {descreverJanelas(L.mcp.com_chave)} e {ch.sem_teto_diario ? 'sem teto diário' : <>cota de {n(ch.cota_diaria ?? 0)} requisições por dia UTC</>}.</> : null}
        </li>
      </ul>
      <p className="text-xs text-gray-600">
        Ao esgotar o orçamento a API responde <code>429</code> com <code>Retry-After</code> (segundos até a renovação, à meia-noite UTC) e um corpo que explica o limite e a saída:
        entrar com uma conta gratuita{ch.ativa ? ' ou usar o MCP com chave' : ''}. Os valores são os desta instalação e podem ser ajustados por quem a opera.
      </p>
    </div>
  )
}
