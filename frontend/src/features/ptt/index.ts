// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { registrarAbas, registrarBloco, type BlocoDef } from '../entidade/registry'
import type { PttCtx } from './contexto'
import { LinhaDoTempoPtt } from '../historico/blocos'
import { DestaqueBloco } from './blocks/DestaqueBloco'
import { HilbertV4Bloco } from './blocks/HilbertV4Bloco'
import { HilbertV6Bloco } from './blocks/HilbertV6Bloco'
import { IndicadoresAsBloco } from './blocks/IndicadoresAsBloco'
import { IndicadoresV4Bloco } from './blocks/IndicadoresV4Bloco'
import { IndicadoresV6Bloco } from './blocks/IndicadoresV6Bloco'
import { MapaGeoBloco } from './blocks/MapaGeoBloco'
import { MembrosSemDiretoBloco } from './blocks/MembrosSemDiretoBloco'
import { PeersV4Bloco } from './blocks/PeersV4Bloco'
import { PeersV6Bloco } from './blocks/PeersV6Bloco'
import { RouteServersBloco } from './blocks/RouteServersBloco'
import { RejeicoesBloco } from './blocks/RejeicoesBloco'
import { PotencialBloco } from './blocks/PotencialBloco'
import { InstalacoesBloco } from './blocks/InstalacoesBloco'
import { ConteudoBloco } from './blocks/ConteudoBloco'
import { EntrouSaiuBloco } from './blocks/EntrouSaiuBloco'
import { ParticipantesFiltradosBloco } from './blocks/ParticipantesFiltradosBloco'

/** Blocos da página de PTT, na ordem em que aparecem (passos de 10). Corpos idênticos aos da página de antes; ver `features/asn/index.ts`. */
const base = { entidade: 'ixp' as const }

/** Lentes da página: cada bloco pertence a uma; aba sem bloco aplicável some. */
registrarAbas('ixp', [
  { id: 'resumo', rotulo: 'Resumo', descricao: 'Indicadores em destaque e o potencial de crescimento do PTT.' },
  { id: 'participantes', rotulo: 'Participantes', descricao: 'Quem tem peering direto, quem está registrado sem peering e os pares por família de IP.' },
  { id: 'route-servers', rotulo: 'Route servers', descricao: 'Sessões, rejeições e a política dos route servers do PTT.' },
  { id: 'cobertura', rotulo: 'Cobertura', descricao: 'Prefixos e ASNs visíveis no PTT, em IPv6 e IPv4, e o espaço de endereços (Hilbert).' },
  { id: 'geografia', rotulo: 'Geografia', descricao: 'Distribuição geográfica dos prefixos e as instalações do PTT.' },
  { id: 'conteudo', rotulo: 'Conteúdo', descricao: 'CDNs e provedores de conteúdo com presença no PTT.' },
  { id: 'historico', rotulo: 'Histórico', descricao: 'O que mudou no PTT entre os snapshots.' },
])
const ABA: Record<string, string> = {
  destaque: 'resumo', potencial: 'resumo', 'indicadores-as': 'resumo',
  'peers-v4': 'participantes', 'peers-v6': 'participantes', 'participantes-filtrados': 'participantes', 'entrou-saiu': 'participantes', conteudo: 'conteudo', 'membros-sem-direto': 'participantes',
  'route-servers': 'route-servers', rejeicoes: 'route-servers',
  'indicadores-v4': 'cobertura', 'indicadores-v6': 'cobertura', 'hilbert-v4': 'cobertura', 'hilbert-v6': 'cobertura',
  mapa: 'geografia', instalacoes: 'geografia',
  'linha-do-tempo': 'historico',
}
const def = (b: Omit<BlocoDef<PttCtx>, 'entidade'>) => registrarBloco<PttCtx>({ ...base, aba: ABA[b.id], ...b })

def({ id: 'destaque', titulo: 'Indicadores em destaque', ordem: 10, depende: ['useIxp', 'ixps', 'ixp-est-users', 'snapshot-details'], fontes: ['ixbr_api', 'lg_ixbr', 'registro_br', 'apnic_pop'],
  selo: 'estimado', nota: 'participantes e originadores são medidos; usuários são estimativa APNIC Labs', Componente: DestaqueBloco })
def({ id: 'indicadores-as', titulo: 'Indicadores de AS', ordem: 20, depende: ['ixps', 'snapshot-details'], fontes: ['ixbr_api', 'lg_ixbr', 'registro_br', 'fulltable_routeviews'], selo: 'fato', Componente: IndicadoresAsBloco })
def({ id: 'indicadores-v6', titulo: 'Indicadores IPv6', ordem: 30, depende: ['useIxp', 'ixps'], fontes: ['lg_ixbr', 'fulltable_routeviews', 'registro_br'], selo: 'fato', Componente: IndicadoresV6Bloco })
def({ id: 'indicadores-v4', titulo: 'Indicadores IPv4', ordem: 40, depende: ['useIxp', 'ixps'], fontes: ['lg_ixbr', 'fulltable_routeviews', 'registro_br'], selo: 'fato', Componente: IndicadoresV4Bloco })
def({ id: 'potencial', titulo: 'Potencial de crescimento', ordem: 50, depende: ['ixp-potential'], fontes: ['prefix_geo', 'global_prefix_geo', 'curada_pix', 'apnic_pop'], selo: 'estimado',
  nota: 'ASes e espaço a até 80 km de algum ponto do PTT', Componente: PotencialBloco })
def({ id: 'route-servers', titulo: 'Route servers', ordem: 55, depende: ['useIxpPerfil'], fontes: ['ixbr_alice', 'ixbr_api'], selo: 'fato',
  nota: 'estado das sessões BGP no route server na data da coleta; sem causa atribuída', aplicavel: (c) => !!c.routeServers, Componente: RouteServersBloco })
def({ id: 'rejeicoes', titulo: 'Rejeições e política nos route servers', ordem: 56, depende: ['useIxpPerfil'], fontes: ['ixbr_alice_rotas', 'ixbr_alice'], selo: 'inferido',
  nota: 'rotas rejeitadas por motivo e communities declaradas, só dos vizinhos coletados; o perfil é inferido', aplicavel: (c) => !!c.rejeicoes, Componente: RejeicoesBloco })
def({ id: 'instalacoes', titulo: 'Instalações (PeeringDB)', ordem: 57, depende: ['useIxpPerfil'], fontes: ['peeringdb_fac'], selo: 'fato',
  nota: 'cadastro autodeclarado no PeeringDB; o indicador de cadastro é inferido das datas e não diz nada da operação', aplicavel: (c) => !!c.facilities || !!c.portas, Componente: InstalacoesBloco })
def({ id: 'mapa', semTitulo: true, titulo: 'Distribuição geográfica', ordem: 60, depende: ['ixp-geo'], fontes: ['prefix_geo', 'curada_pix'], selo: 'inferido', nota: 'geolocalização por prefixo, com confiança variável', Componente: MapaGeoBloco })
def({ id: 'hilbert-v6', semTitulo: true, titulo: 'Espaço IPv6 — Curva de Hilbert', ordem: 70, depende: ['useIxp', 'ixp-members'], fontes: ['lg_ixbr', 'registro_br'], selo: 'fato', aplicavel: (c) => !!c.v6, Componente: HilbertV6Bloco })
def({ id: 'hilbert-v4', semTitulo: true, titulo: 'Espaço IPv4 — Curva de Hilbert', ordem: 80, depende: ['useIxp', 'ixp-members'], fontes: ['lg_ixbr', 'registro_br'], selo: 'fato', aplicavel: (c) => !!c.v4, Componente: HilbertV4Bloco })
def({ id: 'linha-do-tempo', titulo: 'Linha do tempo', ordem: 85, depende: ['useIxpPerfil'], fontes: ['registro_br', 'fulltable_routeviews', 'lg_ixbr', 'rpki_collector', 'apnic_pop'], selo: 'fato', nota: 'diferenças observadas entre snapshots; o histórico começou em 2026-10',
  aplicavel: (c) => !!c.historico, Componente: LinhaDoTempoPtt })
def({ id: 'membros-sem-direto', semTitulo: true, titulo: 'Membros registrados sem peering direto', ordem: 90, depende: ['useIxp', 'ixp-members', 'asn-names'], fontes: ['ixbr_api', 'lg_ixbr', 'asn_names'], selo: 'fato',
  aplicavel: (c) => c.membersWithoutDirect.length > 0, Componente: MembrosSemDiretoBloco })
def({ id: 'peers-v6', semTitulo: true, titulo: 'ASNs em peering direto — IPv6', ordem: 100, depende: ['useIxp', 'ixp-peers-v6', 'ixp-members', 'ixp-assinantes'], fontes: ['lg_ixbr', 'anatel_sici', 'apnic_pop'], selo: 'fato',
  nota: 'assinantes: acessos SCM declarados ao SICI', Componente: PeersV6Bloco })
def({ id: 'peers-v4', semTitulo: true, titulo: 'ASNs em peering direto — IPv4', ordem: 110, depende: ['useIxp', 'ixp-peers-v4', 'ixp-members', 'ixp-assinantes'], fontes: ['lg_ixbr', 'anatel_sici', 'apnic_pop'], selo: 'fato',
  nota: 'assinantes: acessos SCM declarados ao SICI', Componente: PeersV4Bloco })

def({ id: 'participantes-filtrados', titulo: 'Participantes e filtros', ordem: 88, depende: ['useIxp', 'ixp-members', 'useIxpPerfil'], fontes: ['ixbr_api', 'lg_ixbr', 'ixbr_alice', 'asn_names'], selo: 'fato',
  nota: 'família de IP: peering direto observado nas rotas coletadas; "sem sessão" é o cruzamento com o cadastro do IX.br e pode ser peering bilateral', Componente: ParticipantesFiltradosBloco })
def({ id: 'entrou-saiu', titulo: 'Quem entrou e quem saiu', ordem: 89, depende: ['useMudancas'], fontes: ['ixbr_api', 'lg_ixbr'], selo: 'fato',
  nota: 'diferenças entre snapshots com histórico (a partir de 2026-10); saída observada só vale depois da janela de confirmação', Componente: EntrouSaiuBloco })
def({ id: 'conteudo', titulo: 'CDNs e conteúdo no PTT', ordem: 95, depende: ['cdns-presence', 'useIxp'], fontes: ['curada_cdns', 'lg_ixbr'], selo: 'inferido',
  nota: 'presença pelo peering direto de ASNs de CDN nas rotas coletadas; não mede tráfego', Componente: ConteudoBloco })
