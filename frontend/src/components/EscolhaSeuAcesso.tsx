// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from './layout/LinkDatado'
import { useLimites } from '../hooks/useLimites'
import { descreverJanelas, numeroBR as n } from '../lib/limites'

/**
 * Quadro "Escolha o seu acesso" de /dados: cada forma de usar os dados, o que ela libera e o teto que vale. Todo número vem de
 * `GET /api/v1/limites`; sem a chave de MCP ligada na instalação, a linha da chave não existe.
 */
export function EscolhaSeuAcesso() {
  const { data: L, isError } = useLimites()
  if (isError) {
    return <p className="text-sm text-gray-600" role="status">O quadro de limites não pôde ser carregado agora. Os valores estão em <a className="text-primario-600 hover:underline" href="/api/v1/limites">/api/v1/limites</a>.</p>
  }
  if (!L) return <p className="text-sm text-gray-500" role="status">Carregando os limites de uso…</p>
  const s = L.sem_conta
  const ch = L.mcp.chave
  const linhas: { acesso: string; como: React.ReactNode; libera: string; limites: React.ReactNode }[] = [
    {
      acesso: 'Navegador, sem conta',
      como: 'Abrir o site',
      libera: `Páginas de entrada, prévia das listas (até ${s.previa_linhas} linhas, 1ª página) e os ${s.snapshots_atuais} snapshots mais recentes; páginas avançadas enquanto durar o orçamento.`,
      limites: `Orçamento de ${n(s.orcamento_diario_segundos / 60)} minutos de uso por dia, renovado à ${s.renovacao}; a prévia e as páginas de entrada não gastam.`,
    },
    {
      acesso: 'Script (curl, bibliotecas), sem conta',
      como: 'API REST, sem chave',
      libera: 'A mesma prévia, sem sessão de navegador.',
      limites: (
        <>
          {s.custo_por_chamada_segundos} s do orçamento de {n(s.orcamento_diario_segundos)} s por chamada medida
          {s.chamadas_medidas_por_dia != null ? <> (cerca de {n(s.chamadas_medidas_por_dia)} por dia)</> : null}, por rede ({s.identificacao.replace('rede de origem: ', '')});
          além disso, {descreverJanelas(L.api.sem_conta)}. Ao esgotar: <code>429</code> com <code>Retry-After</code>.
        </>
      ),
    },
    {
      acesso: 'Navegador, com conta gratuita',
      como: <><Link to="/login" className="text-primario-700 underline">Entrar</Link> com Google, LinkedIn ou PeeringDB</>,
      libera: 'Listas completas, histórico de snapshots, CSV e contatos na interface.',
      limites: <>{descreverJanelas(L.api.com_conta)} (a API usa a sessão do navegador); contatos: {n(L.contatos.por_dia)} por dia e {n(L.contatos.por_30_dias)} em 30 dias por conta.</>,
    },
    {
      acesso: 'MCP, sem chave',
      como: 'Assistente de IA no endereço do MCP',
      libera: `Prévia (listas de até ${s.previa_linhas} itens, 1ª página, os ${s.snapshots_atuais} snapshots mais recentes).`,
      limites: <>{descreverJanelas(L.mcp.sem_chave)}, por rede.</>,
    },
  ]
  if (ch.ativa) {
    linhas.push({
      acesso: 'MCP, com chave',
      como: <>Chave pessoal gerada no <Link to="/perfil" className="text-primario-700 underline">perfil</Link></>,
      libera: 'Sem os cortes da prévia; contatos de ASN e de operadora, um por chamada, dentro da cota da conta.',
      limites: <>{descreverJanelas(L.mcp.com_chave)}; {ch.sem_teto_diario ? 'sem teto diário' : <>cota de {n(ch.cota_diaria ?? 0)} requisições por dia UTC</>}.</>,
    })
  }
  return (
    <div className="space-y-2">
      <div className="overflow-x-auto" role="region" aria-label="Quadro de formas de acesso, rolável na horizontal" tabIndex={0}>
        <table className="w-full min-w-[40rem] border-collapse text-left text-sm text-gray-700" data-testid="escolha-acesso">
          <caption className="sr-only">Escolha o seu acesso: o que cada forma de uso libera e os limites que valem, conforme a configuração desta instalação</caption>
          <thead>
            <tr className="border-b border-gray-300 text-xs text-gray-600">
              <th scope="col" className="py-2 pr-3 font-semibold">Acesso</th>
              <th scope="col" className="py-2 pr-3 font-semibold">Como</th>
              <th scope="col" className="py-2 pr-3 font-semibold">O que libera</th>
              <th scope="col" className="py-2 font-semibold">Limites</th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((l) => (
              <tr key={l.acesso} className="border-b border-gray-200 align-top">
                <th scope="row" className="py-2 pr-3 font-semibold text-gray-800">{l.acesso}</th>
                <td className="py-2 pr-3">{l.como}</td>
                <td className="py-2 pr-3">{l.libera}</td>
                <td className="py-2">{l.limites}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-gray-600">
        A rede de origem é o IPv4 inteiro ou o prefixo IPv6 /64; redes que compartilham o endereço (NAT, CGNAT) dividem o orçamento dos scripts. A API REST não tem chave própria.
        Os valores são os desta instalação, lidos de <a className="text-primario-600 hover:underline" href="/api/v1/limites">/api/v1/limites</a>.
      </p>
    </div>
  )
}
