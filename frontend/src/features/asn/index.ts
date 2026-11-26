// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { ProntidaoAsnBloco } from '../prontidao/blocos'
import { registrarAbas, registrarBloco, type BlocoDef } from '../entidade/registry'
import type { AsnCtx } from './contexto'
import { AcessosBloco } from './blocks/AcessosBloco'
import { RadarAsnBloco } from '../radar/blocos'
import { ExposicaoAsnBloco } from '../exposicao/blocos'
import { AlertasBloco } from './blocks/AlertasBloco'
import { AspaBloco } from './blocks/AspaBloco'
import { DiagnosticoBloco } from './blocks/DiagnosticoBloco'
import { EstabilidadeBloco } from './blocks/EstabilidadeBloco'
import { IxpsExternosBloco } from './blocks/IxpsExternosBloco'
import { InterconexaoMensuravelBloco } from './blocks/InterconexaoMensuravelBloco'
import { MapaGeoBloco } from './blocks/MapaGeoBloco'
import { MetricasBloco } from './blocks/MetricasBloco'
import { OutorgaScmBloco, OutorgaSeacBloco, OutorgaSmpBloco, OutorgaStfcBloco } from './blocks/Outorgas'
import { PeeringDbBloco } from './blocks/PeeringDbBloco'
import { PrefixosRirBloco } from './blocks/PrefixosRirBloco'
import { HilbertIpv4Bloco, HilbertIpv6Bloco, temPrefixos } from './blocks/CurvaHilbertAsnBloco'
import { PresencaBloco } from './blocks/PresencaBloco'
import { SegurancaBloco } from './blocks/SegurancaBloco'
import { RouteServersAsnBloco } from './blocks/RouteServersAsnBloco'
import { PoliticaRsAsnBloco } from './blocks/PoliticaRsAsnBloco'
import { OrganizacaoAsnBloco } from './blocks/OrganizacaoAsnBloco'
import { BloqueiosAsnBloco } from './blocks/BloqueiosAsnBloco'
import { InstalacoesAsnBloco } from './blocks/InstalacoesAsnBloco'
import { RelacoesBloco } from './blocks/RelacoesBloco'
import { RoaBloco } from './blocks/RoaBloco'
import { TabelaGlobalBloco } from './blocks/TabelaGlobalBloco'
import { UsuariosBloco } from './blocks/UsuariosBloco'
import { LinhaDoTempoAsn } from '../historico/blocos'
import { RecursosIpv4AsnBloco } from '../ipv4/blocos'

/**
 * Blocos da página de ASN, na ordem em que aparecem (passos de 10: bloco novo encaixa entre dois sem renumerar).
 * Cada bloco tem título (aria-label), dependências e fontes.
 * `semTitulo`/`plana`: o bloco traz os próprios títulos e não tem cartão, só o rodapé de proveniência.
 */
const base = { entidade: 'asn' as const }

/** Lentes da página: cada bloco pertence a uma, e a ordem de exibição dentro da aba segue `ordem`. A primeira é a padrão. */
registrarAbas('asn', [
  { id: 'resumo', rotulo: 'Resumo', descricao: 'O que este AS é e onde chamar atenção, em poucos números.' },
  { id: 'numeracao', rotulo: 'Numeração', descricao: 'Blocos de endereço delegados ao AS, onde aparecem no espaço IPv6 e IPv4 e se estão anunciados.' },
  { id: 'roteamento', rotulo: 'Roteamento', descricao: 'Que prefixos anuncia, por onde as rotas passam e se são estáveis.' },
  { id: 'seguranca', rotulo: 'Segurança', descricao: 'RPKI, ROV, ASPA, bogons e outras medições de terceiros sobre este AS.' },
  { id: 'interconexao', rotulo: 'Interconexão', descricao: 'Em que PTTs e instalações está e como se conecta aos route servers.' },
  { id: 'mercado', rotulo: 'Mercado', descricao: 'Organização, assinantes declarados e outorgas da empresa dona do AS.' },
  { id: 'historico', rotulo: 'Histórico', descricao: 'O que mudou neste AS entre os snapshots.' },
])
const ABA: Record<string, string> = {
  metricas: 'resumo', usuarios: 'resumo', alertas: 'resumo',
  'prefixos-rir': 'numeracao', 'hilbert-ipv6': 'numeracao', 'hilbert-ipv4': 'numeracao', 'tabela-global': 'roteamento', mapa: 'roteamento', estabilidade: 'roteamento', diagnostico: 'roteamento', relacoes: 'roteamento', radar: 'roteamento', 'recursos-ipv4': 'numeracao',
  seguranca: 'seguranca', prontidao: 'seguranca', roa: 'seguranca', aspa: 'seguranca', bloqueios: 'seguranca', exposicao: 'seguranca',
  presenca: 'interconexao', 'interconexao-mensuravel': 'interconexao', 'route-servers': 'interconexao', 'politica-rs': 'interconexao', 'ixps-externos': 'interconexao', instalacoes: 'interconexao', peeringdb: 'interconexao',
  organizacao: 'mercado', acessos: 'mercado', 'outorga-scm': 'mercado', 'outorga-smp': 'mercado', 'outorga-stfc': 'mercado', 'outorga-seac': 'mercado',
  'linha-do-tempo': 'historico',
}
/** "Como ler" dos blocos em que a leitura errada é mais provável: o que o número mostra e o que ele não prova. */
const COMO_LER: Record<string, string> = {
  usuarios: 'O APNIC estima os usuários a partir de amostras de anúncios, numa janela de 60 dias. O número não é um censo e não equivale à quantidade de clientes da empresa.',
  seguranca: 'ROV e DNSSEC são medições por amostragem do APNIC. A falta de medição não prova que não há proteção. O AS Rank é uma inferência do CAIDA.',
  prontidao: 'O índice vai de 0 a 100 e reúne medições de terceiros com regras públicas. Ele retrata o que se observa e não é um veredito sobre a empresa.',
  relacoes: 'As relações entre ASes são inferidas do AS_PATH nas tabelas observadas. O peering bilateral não aparece nos dados públicos, então a falta de uma relação não indica ausência de peering.',
  presenca: '"Direto" é a sessão do AS nos route servers do PTT. "Originador" é o prefixo do AS visto no PTT por outro participante.',
  acessos: 'Os assinantes são os declarados pela empresa à Anatel (SICI), num mês de referência próprio. ASes do mesmo CNPJ dividem o mesmo total.',
  'hilbert-ipv6': 'É o mesmo mapa do panorama técnico, só com os prefixos do AS. Cada célula é um /32 de um bloco de RIR (resolução /32): um prefixo menor que o /32, como um /48, marca o /32 que o contém, e um mais curto, como um /29, pinta todas as células que cobre. A curva mostra onde os prefixos estão, não uso nem tráfego. "Alocado e visível" é o alocado pelo Registro.br que também aparece na tabela global; "visto no PTT" reúne todos os PTTs ou o escolhido.',
  'hilbert-ipv4': 'É o mesmo mapa do panorama técnico, só com os prefixos do AS. Cada célula é um /16 (resolução /16; os números são os /8): um prefixo menor que o /16, como um /24, marca o /16 que o contém, com a intensidade proporcional aos /24 do AS ali, e um mais curto pinta todas as células que cobre. A curva mostra onde os prefixos estão, não uso nem tráfego. "Alocado e visível" é o alocado pelo Registro.br que também aparece na tabela global; "visto no PTT" reúne todos os PTTs ou o escolhido.',
  'recursos-ipv4': 'São blocos delegados e sua aparição na tabela. Um bloco não anunciado pode estar em uso, e o sinal de terceiros é uma hipótese.',
}
const RECOLHIDO = new Set(['diagnostico', 'politica-rs', 'instalacoes'])
const def = (b: Omit<BlocoDef<AsnCtx>, 'entidade'>) => registrarBloco<AsnCtx>({ ...base, aba: ABA[b.id], comoLer: COMO_LER[b.id], recolhido: RECOLHIDO.has(b.id) && !b.semTitulo, ...b })

const FONTES_ALERTAS = ['registro_br', 'fulltable_routeviews', 'rpki_collector', 'peeringdb_networks', 'lg_ixbr']
const outorga = (id: string, titulo: string, ordem: number, campo: 'scm' | 'smp' | 'stfc' | 'seac', Componente: BlocoDef<AsnCtx>['Componente']) =>
  def({ id, titulo, ordem, semTitulo: true, depende: ['useAsn'], fontes: ['anatel_outorgas'], selo: 'fato', nota: 'cruzamento por CNPJ', aplicavel: (c) => (c.doc[campo]?.length ?? 0) > 0, Componente })

def({ id: 'metricas', titulo: 'Métricas', ordem: 10, depende: ['useAsn'], fontes: ['registro_br', 'fulltable_routeviews', 'lg_ixbr'], selo: 'fato', Componente: MetricasBloco })
def({ id: 'usuarios', semTitulo: true, titulo: 'Usuários estimados', ordem: 20, depende: ['useAsn'], fontes: ['apnic_pop'], selo: 'estimado', nota: 'janela de 60 dias',
  aplicavel: (c) => c.doc.apnic_users != null, Componente: UsuariosBloco })
def({ id: 'linha-do-tempo', titulo: 'Linha do tempo', ordem: 25, depende: ['useAsnPerfil'], fontes: ['registro_br', 'fulltable_routeviews', 'lg_ixbr', 'rpki_collector', 'apnic_pop'], selo: 'fato', nota: 'diferenças observadas entre snapshots',
  aplicavel: (c) => !!c.historico, Componente: LinhaDoTempoAsn })
def({ id: 'alertas', semTitulo: true, titulo: 'Pontos de atenção', ordem: 30, depende: ['useAsn'], fontes: FONTES_ALERTAS, selo: 'inferido', nota: 'regras versionadas (rules_version do manifesto)', Componente: AlertasBloco })
def({ id: 'seguranca', titulo: 'Segurança de roteamento', ordem: 35, depende: ['useAsnPerfil'], fontes: ['apnic_irov', 'apnic_dnssec', 'caida_asrank', 'bogons'], selo: 'estimado',
  nota: 'ROV e DNSSEC: medição do APNIC por amostragem; AS Rank: inferência do CAIDA; bogon: fato contra as listas da IANA e do Team Cymru',
  aplicavel: (c) => !!c.seguranca, Componente: SegurancaBloco })
def({ id: 'prontidao', titulo: 'Prontidão em segurança de roteamento', ordem: 35.5, depende: ['useAsnPerfil'], fontes: ['apnic_irov', 'bogons', 'caida_spoofer', 'irr_route_objects', 'peeringdb_networks', 'rpki_collector'], selo: 'estimado',
  nota: 'índice de 0 a 100: soma ponderada de medições de terceiros, com regras públicas e versionadas; não é veredito sobre a empresa', aplicavel: (c) => !!c.prontidao, Componente: ProntidaoAsnBloco })
def({ id: 'recursos-ipv4', titulo: 'Recursos IPv4', ordem: 63, depende: ['useAsn'], fontes: ['ipv4_delegated', 'ipv4_listas', 'fulltable_routeviews', 'rpki_collector'], selo: 'inferido',
  nota: 'blocos do delegated cruzados com a tabela de origens e os ROAs; não anunciado não é sem uso; sinal de terceiros é hipótese', Componente: RecursosIpv4AsnBloco })
def({ id: 'route-servers', titulo: 'Nos route servers do IX.br', ordem: 37, depende: ['useAsnPerfil'], fontes: ['ixbr_alice', 'ixbr_api'], selo: 'fato',
  nota: 'estado das sessões BGP no route server na data da coleta; sem causa atribuída', aplicavel: (c) => !!c.routeServers, Componente: RouteServersAsnBloco })
def({ id: 'politica-rs', titulo: 'Política de roteamento nos route servers', ordem: 38, depende: ['useAsnPerfil'], fontes: ['ixbr_alice_rotas', 'ixbr_alice'], selo: 'inferido',
  nota: 'communities declaradas e rotas rejeitadas, só de quem foi coletado; o perfil (aberto, seletivo, restritivo) é inferido', aplicavel: (c) => !!c.politicaRs, Componente: PoliticaRsAsnBloco })
def({ id: 'organizacao', titulo: 'Organização e abuso', ordem: 37.5, depende: ['useAsnPerfil'], fontes: ['caida_as2org', 'abusech'], selo: 'estimado',
  nota: 'organização inferida pelo CAIDA a partir do WHOIS (não é grupo societário); abuso é contagem de terceiros (Feodo Tracker), sem veredito', aplicavel: (c) => !!c.organizacao || !!c.abuso, Componente: OrganizacaoAsnBloco })
def({ id: 'bloqueios', titulo: 'Bloqueios e interferência (OONI)', ordem: 37.7, depende: ['useAsnPerfil'], fontes: ['ooni_bloqueios'], selo: 'estimado',
  nota: 'veredito da própria sonda do OONI, não do backend; não é prova de censura; sondas de voluntários; dados CC BY-NC-SA 4.0', aplicavel: (c) => !!c.bloqueios, Componente: BloqueiosAsnBloco })
def({ id: 'radar', titulo: 'IPv6, tráfego e BGP (Cloudflare Radar)', ordem: 37.8, depende: ['useAsnPerfil'], fontes: ['cloudflare_radar'], selo: 'estimado',
  nota: 'mede quem usa a Cloudflare, não a rede toda; tráfego e velocidade só dos ASNs de topo (ausência não é zero); eventos de BGP não provam intenção nem dano; dados CC BY-NC 4.0', aplicavel: (c) => !!c.radar, Componente: RadarAsnBloco })
def({ id: 'exposicao', titulo: 'Exposição de serviços (Shodan)', ordem: 37.85, depende: ['useAsnPerfil'], fontes: ['shodan_exposicao'], selo: 'estimado',
  nota: 'contagem de serviços observada pelo Shodan na data da leitura; não é prova de vulnerabilidade; ASN sem leitura não é zero; só contagens, nunca lista de IPs; dados do Shodan', aplicavel: (c) => !!c.exposicao, Componente: ExposicaoAsnBloco })
def({ id: 'instalacoes', titulo: 'Instalações e peering (PeeringDB)', ordem: 39, depende: ['useAsnPerfil'], fontes: ['peeringdb_fac', 'peeringdb_ixps'], selo: 'fato',
  nota: 'cadastro autodeclarado no PeeringDB; o indicador de cadastro é inferido das datas e não diz nada da operação', aplicavel: (c) => !!c.facilities || !!c.peering, Componente: InstalacoesAsnBloco })
def({ id: 'estabilidade', titulo: 'Estabilidade BGP', ordem: 40, depende: ['bgp-stability', 'bgp-stability-history'], fontes: ['bgp_updates_routeviews'], selo: 'fato',
  aplicavel: (c) => !!c.asnStability, Componente: EstabilidadeBloco })
def({ id: 'diagnostico', titulo: 'Diagnóstico aprofundado', ordem: 50, depende: ['bgp-stability-deep'], fontes: ['bgp_stability_deep'], selo: 'inferido',
  aplicavel: (c) => !!c.asnDiagnosis, Componente: DiagnosticoBloco })
def({ id: 'prefixos-rir', titulo: 'Prefixos alocados pelo Registro.br', ordem: 60, depende: ['useAsn'], fontes: ['registro_br'], selo: 'fato', Componente: PrefixosRirBloco })
def({ id: 'hilbert-ipv6', titulo: 'Curva de Hilbert IPv6', ordem: 61, depende: ['useAsn'], fontes: ['registro_br', 'fulltable_routeviews', 'lg_ixbr'], selo: 'fato',
  nota: 'posição calculada do próprio prefixo (alocado, observado na tabela global, visto no PTT); não mostra uso nem tráfego', aplicavel: (c) => temPrefixos(c.doc, 'v6'), Componente: HilbertIpv6Bloco })
def({ id: 'hilbert-ipv4', titulo: 'Curva de Hilbert IPv4', ordem: 62, depende: ['useAsn'], fontes: ['registro_br', 'fulltable_routeviews', 'lg_ixbr'], selo: 'fato',
  nota: 'posição calculada do próprio prefixo (alocado, observado na tabela global, visto no PTT); não mostra uso nem tráfego', aplicavel: (c) => temPrefixos(c.doc, 'v4'), Componente: HilbertIpv4Bloco })
def({ id: 'roa', semTitulo: true, titulo: 'RPKI: ROAs autorizados', ordem: 70, depende: ['useAsn'], fontes: ['rpki_collector'], selo: 'fato', Componente: RoaBloco })
def({ id: 'aspa', titulo: 'ASPA', ordem: 80, depende: ['useAsn'], fontes: ['rpki_collector'], selo: 'fato',
  aplicavel: (c) => c.doc.aspa_providers != null || c.doc.aspa_customers != null, Componente: AspaBloco })
def({ id: 'tabela-global', semTitulo: true, titulo: 'Tabela de rotas global', ordem: 90, depende: ['useAsn'], fontes: ['fulltable_routeviews', 'rpki_collector'], selo: 'fato',
  aplicavel: (c) => (c.doc.global_prefixes_v6?.length ?? 0) > 0 || (c.doc.global_prefixes_v4?.length ?? 0) > 0, Componente: TabelaGlobalBloco })
def({ id: 'presenca', titulo: 'Presença em PTTs', ordem: 100, depende: ['useAsn', 'asn-paths', 'asn-ixp-peers'], fontes: ['lg_ixbr', 'fulltable_routeviews'], selo: 'fato', Componente: PresencaBloco })
def({ id: 'acessos', titulo: 'Assinantes declarados à Anatel (SICI)', ordem: 110, depende: ['useAsn', 'acessos-asn'], fontes: ['anatel_sici', 'apnic_pop'], selo: 'fato',
  nota: 'duas datas: o snapshot e o mês de referência da declaração', aplicavel: (c) => c.doc.is_br, Componente: AcessosBloco })
def({ id: 'mapa', semTitulo: true, titulo: 'Distribuição geográfica de prefixos', ordem: 120, depende: ['useAsn', 'asn-geo'], fontes: ['prefix_geo', 'global_prefix_geo'], selo: 'inferido',
  nota: 'geolocalização por prefixo, com confiança variável', Componente: MapaGeoBloco })
def({ id: 'ixps-externos', semTitulo: true, titulo: 'Presença em outros PTTs', ordem: 130, depende: ['useAsn'], fontes: ['peeringdb_ixps'], selo: 'fato', nota: 'autodeclarado no PeeringDB',
  aplicavel: (c) => c.doc.is_br && (c.doc.external_ixps?.length ?? 0) > 0, Componente: IxpsExternosBloco })
def({ id: 'peeringdb', semTitulo: true, titulo: 'PeeringDB', ordem: 140, depende: ['useAsn'], fontes: ['peeringdb_networks'], selo: 'fato', nota: 'autodeclarado no PeeringDB',
  aplicavel: (c) => c.doc.is_br, Componente: PeeringDbBloco })
outorga('outorga-scm', 'Outorgas SCM', 150, 'scm', OutorgaScmBloco)
outorga('outorga-smp', 'Outorgas SMP', 160, 'smp', OutorgaSmpBloco)
outorga('outorga-stfc', 'Outorgas STFC', 170, 'stfc', OutorgaStfcBloco)
outorga('outorga-seac', 'Outorgas SeAC', 180, 'seac', OutorgaSeacBloco)
def({ id: 'relacoes', titulo: 'Relações inferidas', ordem: 190, depende: ['useAsn'], fontes: ['lg_ixbr', 'fulltable_routeviews', 'rpki_collector', 'caida_asrel'], selo: 'inferido',
  aplicavel: ({ doc: d }) => d.relacoes != null || d.upstreams.length > 0 || d.downstreams.length > 0 || (d.upstreams_global_v4?.length ?? 0) > 0 || (d.upstreams_global_v6?.length ?? 0) > 0
    || (d.downstreams_global_v4?.length ?? 0) > 0 || (d.downstreams_global_v6?.length ?? 0) > 0,
  Componente: RelacoesBloco })

def({ id: 'interconexao-mensuravel', titulo: 'Interconexão: o que é mensurável', ordem: 101, depende: ['useInterconexaoAsn'], fontes: ['lg_ixbr', 'ixbr_alice', 'ixbr_alice_rotas'], selo: 'fato',
  nota: 'fatos observados na data da coleta; peering bilateral não é visível nesses dados, então nada aqui diz com quem o AS troca tráfego', Componente: InterconexaoMensuravelBloco })
