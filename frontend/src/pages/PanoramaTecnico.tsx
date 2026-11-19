// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { AbaFamilia } from '../features/panorama/AbaFamilia'
import { AbaInterconexao } from '../features/panorama/AbaInterconexao'
import { AbaSeguranca } from '../features/panorama/AbaSeguranca'
import { PaginaPanorama, type AbaPanorama } from '../features/panorama/PaginaPanorama'
import { ResumoTecnico } from '../features/panorama/ResumoTecnico'

const AbaIpv6 = () => <AbaFamilia familia="v6" />
const AbaIpv4 = () => <AbaFamilia familia="v4" />

/** Cinco abas, um número por conceito no Resumo, IPv6 e IPv4 com a mesma estrutura, e a segurança (RPKI, ROV, prontidão, DNSSEC) junta. */
export const ABAS_TECNICO: AbaPanorama[] = [
  { id: 'resumo', rotulo: 'Resumo', descricao: 'Os números centrais da rede brasileira, um por tema, cada um levando ao detalhe; o mapa no fim é ilustrativo.', Conteudo: ResumoTecnico },
  { id: 'ipv6', rotulo: 'IPv6', descricao: 'Usuários, alocação, visibilidade na tabela global e no IX.br, RPKI, território e espaço de endereços IPv6.', Conteudo: AbaIpv6 },
  { id: 'ipv4', rotulo: 'IPv4', descricao: 'Usuários, alocação, visibilidade na tabela global e no IX.br, RPKI, mercado secundário, território e espaço de endereços IPv4.', Conteudo: AbaIpv4 },
  { id: 'interconexao', rotulo: 'Interconexão', descricao: 'PTTs do IX.br, participantes, alcance e CDNs, com os ASNs de cada PTT.', Conteudo: AbaInterconexao },
  { id: 'seguranca', rotulo: 'Segurança', descricao: 'RPKI (ROA, ASPA e estado das rotas), ROV, saúde da tabela, prontidão em segurança de roteamento e DNSSEC.', Conteudo: AbaSeguranca },
]

/** Ids de aba que viraram aliases e para onde levam (regra 8 do AGENTS.md). */
export const ALIASES_TECNICO: Record<string, string> = { ixbr: 'interconexao', mapa: 'resumo', prontidao: 'seguranca', dnssec: 'seguranca' }

/** Panorama técnico: o conteúdo da Visão geral e as seções técnicas de Estatísticas, por lente e com carga por aba. */
export function PanoramaTecnico() {
  return <PaginaPanorama titulo="Panorama técnico" descricao="A rede brasileira em números: recursos e visibilidade em IPv6 e IPv4, interconexão e CDNs, e segurança (RPKI, ROV, prontidão e DNSSEC)."
    abas={ABAS_TECNICO} aliases={ALIASES_TECNICO} />
}
