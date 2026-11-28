export interface HealthResponse {
  status: string
  latest_snapshot: string | null
  snapshots_available: number
}

/** `GET /api/v1/limites`: os tetos de uso em vigor, lidos do código e da configuração do servidor (nenhum número é escrito no frontend). */
export interface LimiteJanela { janela: string; segundos: number; limite: number }
export interface Limites {
  sem_conta: {
    identificacao: string
    orcamento_diario_segundos: number
    custo_por_chamada_segundos: number
    chamadas_medidas_por_dia: number | null
    renovacao: string
    previa_linhas: number
    snapshots_atuais: number
  }
  api: { sem_conta: LimiteJanela[]; com_conta: LimiteJanela[]; custo_por_rota: Record<string, number>; chave_na_rest: boolean }
  mcp: {
    sem_chave: LimiteJanela[]
    com_chave: LimiteJanela[]
    chave: { ativa: boolean; cota_diaria: number | null; sem_teto_diario: boolean; contagem: string }
  }
  contatos: { por_10_minutos: number; por_hora: number; por_dia: number; por_30_dias: number; por_dia_conta_nova: number; dias_de_conta_nova: number }
}

export interface SnapshotListResponse {
  count: number
  latest: string | null
  snapshots: string[]
}

export interface SnapshotDetails {
  date: string
  summary: SnapshotSummary | null
  manifest: Record<string, unknown> | null
}

export interface GlobalTableStats {
  v4_prefixes?: number
  v4_space_24: number
  /** % do espaço IPv4 alocado ao BR visível na tabela global (rir_br_visible / rir_br) */
  v4_br_coverage_pct: number | null
  /** % do espaço total IPv4 da FT que é BR (rir_br_visible / global_all) */
  v4_br_pct_of_ft: number | null
  v6_prefixes?: number
  v6_space_48: number
  /** % do espaço IPv6 alocado ao BR visível na tabela global */
  v6_br_coverage_pct: number | null
  /** % do espaço total IPv6 da FT que é BR (rir_br_visible / global_all) */
  v6_br_pct_of_ft: number | null
  /** Espaço Registro.br alocado em /48s (células Hilbert × 65536) */
  v6_rir_total_48?: number | null
  /** Espaço BR alocado visível na FT em /48s (células Hilbert × 65536) — usar em vez de v6_space_48 × pct */
  v6_br_space_48?: number | null
  total_asns: number
  /** ASNs BR com ao menos um prefixo visível na tabela global */
  br_asns_in_ft: number | null
}

export interface IXPAggregateStats {
  asn_direct_union_count: number
  asn_origin_union_count?: number
  br_asns_origin_union_count: number
  v4_prefixes?: number
  v4_space_24: number
  v4_coverage_pct?: number
  v4_br_coverage_pct?: number
  v6_prefixes?: number
  v6_space_48: number
  v6_coverage_pct?: number
  v6_br_coverage_pct?: number
}

export interface SnapshotSummary {
  snapshot_date?: string
  generated_at?: string
  total_asns_br: number
  total_asns_global: number
  br_asns_with_ipv6: number
  br_ipv6_pct: number
  ixps_ok: number
  ixps_partial: number
  ixps_missing: number
  ixps_failed?: string[]
  /** Contagens do Registro.br. A API devolve também os mesmos números com o prefixo `m3_` (compatibilidade). */
  registro_br_asns: number
  registro_br_prefixes_v4: number
  registro_br_prefixes_v6: number
  registro_br_declared_space_v4: number
  registro_br_declared_space_v6: number
  /** @deprecated use registro_br_asns */
  m3_asns?: number
  /** @deprecated use registro_br_prefixes_v4 */
  m3_prefixes_v4?: number
  /** @deprecated use registro_br_prefixes_v6 */
  m3_prefixes_v6?: number
  /** @deprecated use registro_br_declared_space_v4 */
  m3_declared_space_v4?: number
  /** @deprecated use registro_br_declared_space_v6 */
  m3_declared_space_v6?: number
  /** Computed by backend: BR ASNs with ≥1 IPv4 prefix in global table */
  br_asns_ft_v4?: number
  /** Computed by backend: BR ASNs with ≥1 IPv6 prefix in global table */
  br_asns_ft_v6?: number
  /** Computed by backend: soma de usuários finais APNIC dos ASNs BR */
  br_apnic_users_total?: number
  /** Computed by backend: registro_br_declared_space_v4 / 256 */
  registro_br_declared_space_v4_24?: number
  /** Computed by backend: registro_br_declared_space_v6 / 2^80 */
  registro_br_declared_space_v6_48?: number
  /** @deprecated use registro_br_declared_space_v4_24 */
  m3_declared_space_v4_24?: number
  /** @deprecated use registro_br_declared_space_v6_48 */
  m3_declared_space_v6_48?: number
  /** Computed by backend: BR ASNs originating IPv4 in any IX.br IXP (may also have IPv6) */
  br_ixp_origin_v4?: number
  /** Computed by backend: BR ASNs originating IPv6 in any IX.br IXP (may also have IPv4) */
  br_ixp_origin_v6?: number
  br_ixp_origin_v4_only?: number
  br_ixp_origin_v6_only?: number
  br_ixp_origin_both?: number
  /** Computed by backend: usuários finais BR estimados (IPv4) visíveis no IX.br como um todo — mesma metodologia de /ixps/{code}/estimated-users, mas com os prefixos de cada AS unidos entre todos os IXPs antes de calcular a fração */
  ixp_estimated_users_v4?: number
  /** Computed by backend: ASNs BR distintos (união) presentes em qualquer IXP externo (PeeringDB) — deduplicado por ASN */
  external_ixps_br_asn_union_count?: number
  /** Computed by backend: ASNs BR com cadastro no PeeringDB */
  br_asns_peeringdb?: number | null
  /** Computed by backend: ASNs BR com geolocalização (lat/lon) */
  br_asns_geolocalized?: number | null
  global_table?: GlobalTableStats
  ixp_aggregate?: IXPAggregateStats
  /** Computed by backend: SCM (CNPJs) com ASN ou que informaram acessos ao SICI */
  provedores_fixos_ativos?: number
  /** Computed by backend: soma de acessos PJ (SICI fixo) */
  assinantes_b2b_fixos?: number
  /** Computed by backend: soma de acessos PF (SICI fixo) */
  assinantes_b2c_fixos?: number
  /** Computed by backend: SMP (CNPJs) com ASN ou que informaram acessos ao SICI móvel */
  provedores_moveis_ativos?: number
  /** Computed by backend: soma de acessos PJ (SICI móvel) */
  assinantes_b2b_moveis?: number
  /** Computed by backend: soma de acessos PF (SICI móvel) */
  assinantes_b2c_moveis?: number
}

// -------------------------------------------------------------------------
// IXPs
// -------------------------------------------------------------------------

/** Coleta de uma família no PTT: `ok` (o looking glass devolveu rotas), `vazia` (a coleta funcionou e o looking glass respondeu com a
 * tabela vazia: zero rotas, não zero de cobertura) ou `missing` (sem bruto). Ausente em respostas antigas. */
export type ColetaAfi = 'ok' | 'vazia' | 'missing'

/** Métricas compactas por AFI no índice de IXPs (/api/v1/ixps) */
export interface IXPIndexAfi {
  coleta?: ColetaAfi
  total_routes: number
  unique_prefixes: number
  ixp_space: number
  /** Espaço em /24 (IPv4) ou /32 (IPv6) */
  ixp_space_units: number
  asn_direct_count: number
  asn_origin_count: number
  asn_stub_count: number
  /** ASNs brasileiros originando prefixos neste IXP */
  br_asns_origin_count: number
  /** `null` com a tabela vazia (`coleta: 'vazia'`). */
  br_prefix_coverage_pct: number | null
  ixp_vs_fulltable_space_pct: number | null
}

/** Entrada no índice de IXPs — campos compactos, sem listas */
export interface IXPIndexEntry {
  code: string
  name: string
  uf: string
  status: 'ok' | 'partial' | 'missing'
  /** União de ASNs diretamente conectados (v4 ∪ v6) */
  asn_direct_union_count?: number
  /** União de ASNs BR diretos / presentes nos route servers (v4 ∪ v6, exato) */
  br_asns_direct_union_count?: number
  /** União de ASNs BR originadores (v4 ∪ v6, exato) */
  br_asns_origin_union_count?: number
  /** União de ASNs originadores, todos os países (v6 ∪ v4; snapshots anteriores a 2026-11 traziam max(v6, v4)) */
  asn_origin_union_count?: number
  /** Membros registrados no IX.br (inclui quem não usa Route Servers) */
  ixbr_members_count?: number
  /** Sessões nos route servers por família (só os route servers com cache de vizinhos atual); `null` sem route server consultado: n/d, não zero (PT-24). */
  route_servers?: { v6: SessoesRsFamilia | null; v4: SessoesRsFamilia | null; rs_sem_vizinhos_atuais: number } | null
  /** CDNs da lista curada com ASN no cadastro do PTT; `null` sem o produto no snapshot. */
  cdns_curados?: number | null
  v4: IXPIndexAfi | IXPAfiMissing
  v6: IXPIndexAfi | IXPAfiMissing
}
export interface SessoesRsFamilia { up: number; down: number; sessoes: number; rs: number }

/** Documento completo de IXP (/api/v1/ixps/{code}) — quando há dados para o AFI */
export interface IXPAfiFull {
  coleta?: ColetaAfi
  total_routes: number
  unique_prefixes: number
  ixp_space: number
  asn_direct_count: number
  asn_origin_count: number
  asn_stub_count: number
  /** Carregado via GET /ixps/{code}/members (progressivo) */
  asn_direct?: number[]
  /** Carregado via GET /ixps/{code}/members (progressivo) */
  asn_stub?: number[]
  /** Carregado via GET /ixps/{code}/members (progressivo) */
  br_asns_direct?: number[]
  br_asns_direct_count: number
  br_asns_direct_pct: number
  /** Carregado via GET /ixps/{code}/members (progressivo) */
  br_asns_origin?: number[]
  br_asns_origin_count: number
  br_asns_origin_pct: number
  br_prefix_covered_space: number
  br_prefix_declared_space: number
  br_prefix_coverage_pct: number
  ft_space: number
  ixp_vs_fulltable_space_pct: number
}

export interface IXPMembersAfi {
  asn_direct?: number[]
  asn_stub?: number[]
  br_asns_direct?: number[]
  br_asns_origin?: number[]
}

export interface IXPMembersResponse {
  snapshot_date: string
  ixp: string
  v4: IXPMembersAfi
  v6: IXPMembersAfi
}

/** Retornado quando não há dados coletados para um AFI neste IXP */
export interface IXPAfiMissing {
  status: string
  coleta?: ColetaAfi
}

export type IXPAfi = IXPAfiFull | IXPAfiMissing

/** Type guard: retorna true quando o AFI tem dados completos. A família com a tabela vazia (`coleta: 'vazia'`) não tem: zero rotas não
 * mede cobertura, e as porcentagens vêm nulas. */
export function isIXPAfiFull(afi: IXPAfi): afi is IXPAfiFull {
  return 'total_routes' in afi && afi.coleta !== 'vazia'
}

/** Estado da coleta de uma família, inclusive em respostas sem o campo `coleta`. */
export function coletaDaFamilia(afi: IXPAfi | IXPIndexAfi | null | undefined): ColetaAfi {
  if (!afi || !('total_routes' in afi)) return 'missing'
  return afi.coleta ?? (afi.total_routes ? 'ok' : 'vazia')
}

export interface PathNodeIXPStats {
  v4_count: number
  v4_space_24: number
  v4_pct: number | null
  v4_prefixes: string[] | null
  v6_count: number
  v6_space_48: number
  v6_pct: number | null
  v6_prefixes: string[] | null
}

export interface PathNodeMeta {
  name: string
  is_br: boolean
  space_v4?: number
  space_v6?: number
  ixp_stats?: Record<string, PathNodeIXPStats>
}

export interface ASNPathsResponse {
  snapshot_date: string
  asn: number
  ixp_paths: Record<string, number[][]>
  path_node_meta: Record<string, PathNodeMeta>
}

export interface IXPDocument {
  ixp: string
  name: string
  uf: string
  snapshot_date: string
  generated_at: string
  v4: IXPAfi
  v6: IXPAfi
  asn_members?: number[]
  ixbr_members_count?: number
}

export interface IXPPeerStats {
  total_prefixes: number
  own_prefixes: number
  third_prefixes: number
  origin_asns: number
  own_space_24: number
  third_space_24: number
}

export interface IXPPeersResponse {
  afi: string
  peers: Record<string, IXPPeerStats>
  /** `?peeringdb=1`: portas declaradas no PeeringDB e instalações inferidas, por ASN. */
  peeringdb?: PeeringDbPeers
}

export interface PeeringDbPeers {
  portas: Record<string, number[]>
  instalacoes: Record<string, { id: number; nome: string | null }[]>
  coletado_em?: string | null
  limites?: string
}

/** Stats de peering deste AS em cada IXP direto (/api/v1/asns/{asn}/ixp-peers) */
export interface ASNIXPPeersResponse {
  snapshot_date: string
  asn: number
  peers: Record<string, { v4?: IXPPeerStats; v6?: IXPPeerStats }>
}

export interface IXPHilbertData {
  /** Total IXP: array [65536] de densidade /24 por bloco /16 */
  all?: number[]
  /** Peer selecionado: prefixos próprios */
  own?: number[]
  /** Peer selecionado: prefixos de terceiros */
  third?: number[]
}

/** Índices esparsos /32 por bloco RIR (uma camada — all, own ou third). */
export type IXPHilbertV6Blocks = Record<string, number[]>

export interface IXPHilbertV6Data {
  /** Total IXP: índices esparsos por bloco */
  all?: IXPHilbertV6Blocks
  /** Peer selecionado: prefixos próprios */
  own?: IXPHilbertV6Blocks
  /** Peer selecionado: prefixos de terceiros */
  third?: IXPHilbertV6Blocks
}

/** Detalhe /24 por /16 dentro de um /8 — chave = segundo octeto (string), valor = lista de terceiros octetos */
export type IXPHilbertV4Detail = Record<string, number[]>

export interface IXPHilbertV4DetailData {
  all?: IXPHilbertV4Detail
  own?: IXPHilbertV4Detail
  third?: IXPHilbertV4Detail
}

/** Detalhe /24 global (dashboard) — mesma estrutura, mas uma única camada */
export type HilbertV4DetailLayer = Record<string, number[]>

export interface IXPListResponse {
  snapshot_date: string
  count: number
  /** Fonte e data das colunas `route_servers` e `cdns_curados`. */
  interligacao?: { route_servers: { fonte: string | null; coletado_em: string | null; versao_alice: string | null } | null; cdns: { fonte: string; snapshot: string; cdns_na_lista: number } | null } | null
  ixps: IXPIndexEntry[]
}

// -------------------------------------------------------------------------
// ASNs
// -------------------------------------------------------------------------

/** Entrada no índice de ASNs (/api/v1/asns) */
export interface ASNIndexEntry {
  asn: number
  name: string
  /** UF da organização (geo do CNPJ); nulo fora do Brasil. */
  uf?: string | null
  /** Só com `include=bgp_stability`: eventos de update BGP por prefixo por dia (total, v4, v6). */
  epppd?: number | null
  epppd_v4?: number | null
  epppd_v6?: number | null
  /** Só com `include=prontidao` e a lista nominal liberada: índice 0–100 e classe. */
  prontidao_indice?: number | null
  prontidao_classe?: string | null
  /** Quantos dos quatro pilares têm dado e entraram no índice e na classe. */
  prontidao_pilares_medidos?: number | null
  is_br: boolean
  has_ipv6: boolean
  rir_prefixes_v4_count: number
  rir_prefixes_v6_count: number
  global_prefixes_v4_count: number
  global_prefixes_v6_count: number
  ixps_direct_count: number
  /** PTTs do IX.br em cujo cadastro o AS consta (com ou sem sessão com o route server); `null` se o snapshot não tem a lista (PT-24). */
  ixps_membro_count?: number | null
  ixps_origin_count: number
  ixps_origin_v4_count?: number | null
  ixps_origin_v6_count?: number | null
  apnic_users?: number | null
  apnic_v6_users?: number | null
  pct_v6?: number | null
  has_rpki?: boolean | null
  has_aspa?: boolean | null
  pdb_registered?: boolean | null
  has_scm?: boolean | null
  has_smp?: boolean | null
  has_stfc?: boolean | null
  has_seac?: boolean | null
  cnpj?: string | null
  external_ixps_count?: number | null
}

/** Presença por AFI dentro de ixp_presence */
export interface IXPPresenceAfi {
  direct: boolean
  origin: boolean
  prefixes: string[]
}

/** Presença de um ASN em um IXP específico */
export interface IXPPresence {
  v4: IXPPresenceAfi
  v6: IXPPresenceAfi
}

export interface RoaEntry {
  prefix: string
  maxLength: number
  ta: string
}

/** Objeto ASPA publicado por um AS como customer: lista de providers autorizados */
export interface AspaProviderEntry {
  providers: number[]
  tal: string
}

/** Referência a um ASPA de outro AS que lista este AS como provider */
export interface AspaCustomerEntry {
  customer: number
  tal: string
}

/** Severidade e categoria de um ponto de atenção */
export type AlertSeverity = 'critico' | 'aviso' | 'info'
export type AlertCategory = 'roteamento' | 'rpki' | 'v4v6' | 'presenca' | 'geo'

/** Ponto de atenção computado pelo backend (api/asn_health.py) */
export interface ASNAlert {
  id: string
  category: AlertCategory
  severity: AlertSeverity
  title: string
  detail: string
  refs: Record<string, unknown>
  /** Versão da regra que gerou o alerta; séries só se comparam entre snapshots de mesmo `rules_version` do manifesto. */
  desde_versao?: number
}

/** Documento completo de ASN (/api/v1/asns/{asn}) */
/** Referências de comparação do AS (`include=referencias`): posição e medianas entre os ASes brasileiros do snapshot. */
export interface ReferenciasAsn {
  universo: string
  total: number
  usuarios_posicao: number | null
  usuarios_com_dado: number
  pct_v6_mediana: number | null
  prefixos_v4_mediana: number | null
  ixps_diretos_mediana: number | null
}

/** Cadastro público do CNPJ do ASN na Receita (`include=cadastro`, PT-26): situação, atividade e município, sem endereço nem contato. */
export interface AsnCadastro {
  cnpj: string
  razao_social?: string
  nome_fantasia?: string
  descricao_situacao_cadastral?: string
  descricao_motivo_situacao_cadastral?: string
  cnae_fiscal?: number | string
  cnae_fiscal_descricao?: string
  municipio?: string
  uf?: string
  codigo_municipio_ibge?: number | string
  /** Data (ISO) em que o cadastro foi lido pela coleta do OBINT. */
  lido_em?: string | null
  fonte: string
  selo: 'fato'
}
/** ASN na lista de recursos em recuperação do Registro.br (`include=recuperacao`, PT-26); `null` quando não está. A lista não informa o motivo. */
export interface AsnRecuperacao { asn: number; inicio: string; fim: string; primeira_vez_visto?: string | null; fonte: string; selo: 'fato' }
export interface ASNDocument {
  asn: number
  snapshot_date: string
  generated_at: string
  is_br: boolean
  name: string
  cnpj?: string
  /** Prefixos atribuídos pelo RIR/Registro.br (fonte autoritativa de alocação) */
  rir_prefixes_v4: string[]
  rir_prefixes_v6: string[]
  rir_prefixes_v4_count: number
  rir_prefixes_v6_count: number
  /** Prefixos observados na tabela de roteamento global */
  global_prefixes_v4: string[]
  global_prefixes_v6: string[]
  global_prefixes_v4_count: number
  global_prefixes_v6_count: number
  has_ipv6: boolean
  ixps_direct: string[]
  ixps_origin: string[]
  ixp_presence: Record<string, IXPPresence>
  /** União IPv4+IPv6, mantida para compatibilidade */
  upstreams: number[]
  downstreams: number[]
  /** Relações inferidas dos IXPs, separadas por AFI */
  upstreams_v4?: number[]
  upstreams_v6?: number[]
  downstreams_v4?: number[]
  downstreams_v6?: number[]
  /** Relações inferidas do RouteViews (múltiplos vantage points) */
  upstreams_global_v4?: number[]
  upstreams_global_v6?: number[]
  downstreams_global_v4?: number[]
  downstreams_global_v6?: number[]
  /** Características de conectividade derivadas do grafo global */
  is_multihomed_v4?: boolean
  is_multihomed_v6?: boolean
  single_upstream_v4?: number | null
  single_upstream_v6?: number | null
  /** Relações inferidas (ARC v1); ausente em snapshots anteriores */
  relacoes?: AsnRelacoes
  /** IXPs onde este AS consta no cadastro de participantes do IX.br */
  ixp_member_codes?: string[]
  /** ROAs que autorizam este AS: [{prefix, maxLength, ta}] */
  roa_list?: RoaEntry[]
  /** Status RPKI de cada prefixo anunciado: {prefix: 'valid'|'invalid'|'not_found'} */
  rpki_validation?: Record<string, 'valid' | 'invalid' | 'not_found'>
  /** Objetos ASPA publicados por este AS como customer */
  aspa_providers?: AspaProviderEntry[]
  /** Objetos ASPA de outros ASes que listam este AS como provider */
  aspa_customers?: AspaCustomerEntry[]
  /** Computed by backend: for origin-only IXPs, all unique AS_PATH chains (each: [next_hop_from_origin, ..., direct_peer_at_ixp]) */
  ixp_paths?: Record<string, number[][]>
  /** Computed by backend: metadata for each unique path ASN */
  path_node_meta?: Record<string, PathNodeMeta>
  /** PeeringDB */
  pdb_registered?: boolean
  external_ixps?: string[]
  pdb?: PDBNetworkInfo | null
  /** APNIC Labs — estimativas de usuários (janela de 60 dias) */
  apnic_users?: number | null
  apnic_users_pct_cc?: number | null
  apnic_v6_users?: number | null
  apnic_v6_pct_as?: number | null
  /** Endereços IPv4 anunciados na full table (soma dos /32 equivalentes) */
  announced_ipv4_addresses?: number | null
  /** Usuários estimados por endereço IPv4 anunciado — proxy de intensidade de CGNAT */
  users_per_ip?: number | null
  /** /48 equivalentes IPv6 anunciados na full table */
  announced_ipv6_48s?: number | null
  /** Usuários IPv6 estimados por /48 anunciado */
  users_per_v6_48?: number | null
  /** Pontos de atenção: divergências e práticas possivelmente mal feitas */
  alerts?: ASNAlert[]
  /** Outorgas SCM da Anatel associadas a este ASN via CNPJ (sem contatos) */
  scm?: SCMRecord[]
  /** True se o CNPJ deste AS possui outorga SCM */
  has_scm?: boolean
  /** Outorgas SMP da Anatel associadas a este ASN via CNPJ (sem contatos) */
  smp?: SMPRecord[]
  /** True se o CNPJ deste AS possui outorga SMP */
  has_smp?: boolean
  /** Outorgas STFC da Anatel associadas a este ASN via CNPJ (sem contatos) */
  stfc?: STFCRecord[]
  /** True se o CNPJ deste AS possui outorga STFC */
  has_stfc?: boolean
  /** Outorgas SeAC da Anatel associadas a este ASN via CNPJ (sem contatos) */
  seac?: SEACRecord[]
  /** True se o CNPJ deste AS possui outorga SeAC */
  has_seac?: boolean
  /** Outros ASNs do Registro.br com o mesmo CNPJ */
  same_cnpj_asns?: Array<{ asn: number; name: string }>
  /** Nomes alternativos com origem */
  alt_names?: Array<{ name: string; source: string }>
  /** Contagens de contatos disponíveis (sem valores) — valores em /asns/{asn}/contacts */
  contacts_available?: { peeringdb: number; anatel: number; receita: boolean; total: number; rdap?: number }
}

/** Um contato consolidado (origem + função). Só vem do endpoint protegido. */
export interface ASNContact {
  source: string
  role: string
  name: string | null
  email: string | null
  phone: string | null
}

/** Resposta de GET /asns/{asn}/contacts (protegido por login). */
export interface ASNContactsResponse {
  snapshot_date: string
  asn: number
  total: number
  contacts: ASNContact[]
  /** Cota de contatos da conta: consultas que ainda cabem nas últimas 24 h; null sem teto por conta. */
  cota?: { restante_hoje: number | null }
  /** situação da leitura do RDAP do Registro.br para este ASN e cobertura do rodízio (contagens e datas, sem dado pessoal). */
  rdap?: {
    leitura_em: string | null
    tentou_em: string | null
    status: string | null
    cobertura: {
      asns_no_universo: number
      com_leitura_valida: number
      leitura_mais_antiga: string | null
      leitura_mais_recente: string | null
    } | null
  }
}

// -------------------------------------------------------------------------
// IXPs externos (PeeringDB)
// -------------------------------------------------------------------------

export interface ExternalIXPIndexEntry {
  code: string
  name: string
  city: string
  country: string
  pdb_ix_id: number
  /** Redes (ASNs distintos) declaradas no PeeringDB; ausente em snapshots anteriores a 2026-11. */
  redes?: number
  redes_br?: number
  /** Portas (linhas netixlan): uma rede pode ter várias. */
  portas?: number
  /** Alias de `redes` (até 2026-11 contava portas). */
  member_count: number
  /** Alias de `redes_br` (até 2026-11 contava portas). */
  br_member_count: number
  last_updated: string
}

export interface ExternalIXPListResponse {
  snapshot_date: string
  count: number
  ixps: ExternalIXPIndexEntry[]
}

export interface ExternalIXPMember {
  asn: number
  name: string
  speed: number
  is_br: boolean
}

export interface ExternalIXPDocument {
  snapshot_date: string
  code: string
  name: string
  city: string
  country: string
  pdb_ix_id: number
  redes?: number
  redes_br?: number
  portas?: number
  /** Alias de `redes` (até 2026-11 contava portas). */
  member_count: number
  /** Alias de `redes_br` (até 2026-11 contava portas). */
  br_member_count: number
  last_updated: string
  /** Uma linha por porta (netixlan). */
  members: ExternalIXPMember[]
}

export interface IXPCompareParticipant {
  asn: number
  name: string | null
  cnpj: string | null
  ipv4_prefixes: string[]
  ipv6_prefixes: string[]
  member_of: string[]
  /** Tem documento no snapshot (`/asn/{asn}` abre). Ausente em respostas antigas: trate como true. */
  has_detail?: boolean
}

export interface IXPCompareMembersResponse {
  snapshot_date: string
  ixps: string[]
  count: number
  participants: IXPCompareParticipant[]
}

/** Cadastro do PeeringDB (`/api/net`) como a API o entrega: só os campos de `sources/peeringdb_networks` (`_KEEP`), vazios omitidos. */
export interface PDBNetworkInfo {
  name?: string
  aka?: string
  website?: string
  info_type?: string
  info_traffic?: string
  info_ratio?: string
  policy_general?: string
  policy_ratio?: boolean
  policy_contracts?: boolean
  policy_locations?: string
  irr_as_set?: string
  info_prefixes4?: number
  info_prefixes6?: number
}

// -------------------------------------------------------------------------
// CDN presence
// -------------------------------------------------------------------------

export interface CDNRow {
  name: string
  /** Categorias editoriais (config/cdns.yaml); ausente em snapshots anteriores a 1.6.0. */
  categorias?: string[]
  asns: number[]
  ixbr: string[]
  external: string[]
  ixbr_count: number
  external_count: number
  /** PT-24: estados no IX.br, calculados na leitura. `ixbr_rs` = membro com sessão no route server; `ixbr_sem_rs` = membro sem sessão observada (pode haver peering bilateral);
   *  `ixbr_origem` = não membro, prefixos vistos por outro participante (inferido); `ixbr_sem_coleta` = PTT sem coleta válida. Ausentes em resposta antiga. */
  ixbr_rs?: string[]
  ixbr_sem_rs?: string[]
  ixbr_sem_coleta?: string[]
  ixbr_origem?: string[]
  asns_sem_documento?: number[]
  sem_rs_em_nenhum_ptt?: boolean
}

export interface CDNColumn {
  code: string
  name: string
  cdn_count: number
}

export type CDNColumnOrigin = 'ixbr' | 'external'

export interface CDNMatrixColumn extends CDNColumn {
  origin: CDNColumnOrigin
  region?: string
}

export interface CDNPresenceResponse {
  snapshot_date: string
  cdns: CDNRow[]
  ixbr_columns: CDNColumn[]
  external_columns: CDNColumn[]
  /** PT-24: o que cada estado de `ixbr_rs`, `ixbr_sem_rs` e `ixbr_origem` quer dizer, e o limite de leitura. */
  estados?: Record<string, string>
  estados_limites?: string
}

/** `GET /asns?asns=`: documentos completos em lote; `paths` só com `include=paths`. */
export interface ASNsLote {
  snapshot_date: string
  total: number
  items: Array<ASNDocument & { paths?: ASNPathsResponse; epppd?: number | null; epppd_v4?: number | null; epppd_v6?: number | null }>
  not_found: number[]
}

export interface PaginatedASNs {
  snapshot_date: string
  total: number
  page: number
  limit: number
  pages: number
  items: ASNIndexEntry[]
}

// -------------------------------------------------------------------------
// Hilbert
// -------------------------------------------------------------------------

export interface HilbertV4Data {
  /** 65536 valores: count de /24 equivalentes no bloco /16 de índice i=a*256+b */
  rir_br: number[]
  global_br: number[]
  global_all: number[]
  ixp_all: number[]
  /** Interseção: alocado ao BR pelo Registro.br E visível na full table global */
  rir_br_visible: number[]
}

/** Índices esparsos de /32 ativos para um bloco IPv6 (5 camadas). */
export interface HilbertV6BlockData {
  /** Alocado ao Brasil pelo Registro.br/RIR responsável */
  rir_br: number[]
  /** Prefixos de ASNs brasileiros visíveis na tabela global */
  global_br: number[]
  /** Todos os prefixos presentes na tabela de roteamento global */
  global_all: number[]
  /** Prefixos presentes em algum IXP do IX.br */
  ixp_all: number[]
  /** Interseção: alocado ao BR e visível na tabela global */
  rir_br_visible: number[]
}

/**
 * Mapa de Hilbert IPv6: 6 blocos RIR com índices esparsos de /32.
 * Blocos /12 → grade 1024×1024 (d2xy(1024, d)). Legado /16 → grade 256×256.
 */
export interface HilbertV6Data {
  legacy:  HilbertV6BlockData  // 2001::/16
  lacnic:  HilbertV6BlockData  // 2800::/12
  arin:    HilbertV6BlockData  // 2600::/12
  ripe:    HilbertV6BlockData  // 2a00::/12
  apnic:   HilbertV6BlockData  // 2400::/12
  afrinic: HilbertV6BlockData  // 2c00::/12
}

// -------------------------------------------------------------------------
// SCM — Outorgas Anatel
// -------------------------------------------------------------------------

export interface SCMRecord {
  cnpj: string
  razao_social: string
  nome_fantasia?: string
  data_outorga?: string
  municipio?: string
  uf?: string
  codigo_ibge?: string
  telefone?: string
  email?: string
  situacao?: string
  geo_confidence?: 'exact_address' | 'cep_centroid' | 'city_centroid' | 'unknown'
  geo_source?: string
  /** ASNs do Registro.br com mesmo CNPJ */
  asns: number[]
  // --- Acessos declarados ao SICI (presentes quando anatel_sici e sici rodaram) ---
  /** Declarou ao menos um acesso no mês de referência. Ter outorga não é operar. */
  sici_ativo?: boolean
  /** Mês da declaração — diferente da data do snapshot */
  sici_mes_referencia?: string
  sici_acessos?: number
  /** Pessoa Física (B2C) */
  sici_pf?: number
  /** Pessoa Jurídica (B2B) */
  sici_pj?: number
  sici_municipios?: number
  sici_capacidade_mbps?: number
  sici_tecnologia?: string
  sici_empresa?: string
}

// ---------------------------------------------------------------------------
// SICI — Acessos de banda larga fixa declarados à Anatel
// ---------------------------------------------------------------------------

/** Ponto da série mensal: [mes, acessos, pessoa_fisica, pessoa_juridica] */
export type SiciSeriePoint = [string, number, number, number]

export interface SiciDivergencia {
  classificacao: 'normal' | 'apnic_alto' | 'apnic_baixo' | 'nao_comparavel' | 'sem_dados'
  razao?: number
  apnic_users?: number
  acessos_sici?: number
  faixa_normal?: [number, number]
  motivo?: string
}

export interface SiciAcessos {
  snapshot_date: string
  /** Mês da declaração ao SICI — cite junto com snapshot_date */
  mes_referencia: string
  asn?: number
  cnpj: string
  empresa?: string
  grupo?: string
  porte?: string
  acessos: number
  /** Pessoa Física (B2C) */
  pf: number
  /** Pessoa Jurídica (B2B) */
  pj: number
  acessos_internet?: number
  /** Capacidade CONTRATADA (Σ velocidade × acessos), não de trânsito */
  capacidade_mbps: number
  capacidade_internet_mbps?: number
  velocidade_media_mbps: number
  /** Mediana ponderada — preferível à média, distorcida por links de backbone */
  velocidade_mediana_mbps: number
  municipios: number
  tecnologia_predominante?: string
  meio_predominante?: string
  por_tecnologia?: Record<string, number>
  por_meio?: Record<string, number>
  por_faixa?: Record<string, number>
  por_produto?: Record<string, number>
  /** CNPJ com mais de um ASN: o total vale para cada um. Nunca some ASes do mesmo CNPJ. */
  acessos_compartilhados: boolean
  asns: number[]
  serie: SiciSeriePoint[]
  divergencia_apnic_anatel?: SiciDivergencia | null
}

export interface SiciMunicipioRow {
  ibge: string
  nome: string
  uf: string
  acessos: number
  pf: number
  pj: number
  capacidade_mbps: number
  municipio_acessos?: number | null
  /** Participação do operador no município (%) */
  share?: number | null
  /** Declarantes no município (empresas que declararam acessos ao SICI) */
  municipio_operadores?: number | null
  /** HHI local por CNPJ (0 a 10.000), método do projeto; o aviso `poucos_casos` é rótulo, nada é suprimido (PT-23) */
  municipio_hhi?: number | null
  avisos_hhi?: string[] | null
}

export interface SiciAsnMunicipios {
  snapshot_date: string
  mes_referencia: string
  asn: number
  cnpj: string
  total: number
  acessos_compartilhados: boolean
  items: SiciMunicipioRow[]
}

export interface SiciOperador {
  cnpj: string
  empresa: string
  acessos: number
  share: number
  asns: number[]
}

export interface SiciMunicipioMapaEntry {
  nome: string
  uf: string
  acessos: number
  operadores: SiciOperador[]
}

/** Índice IBGE → operadores, para geolocalizar no Localizador via centróide. */
export interface SiciMunicipiosMapaResponse {
  snapshot_date: string
  mes_referencia: string
  total: number
  municipios: Record<string, SiciMunicipioMapaEntry>
}

export interface SiciMunicipioDetalhe {
  snapshot_date: string
  mes_referencia: string
  ibge: string
  nome: string
  uf: string
  acessos: number
  pf: number
  pj: number
  capacidade_mbps: number
  operadores: SiciOperador[]
  operadores_count: number
  /** 10000 = monopólio; <1500 = competitivo. Satélite atende quase todo município. */
  hhi: number
  share_maior: number
  /** Acessos pelo meio "Fibra" (FTTH/FTTB) e % do total; ausentes em meses coletados antes do 1.4.1. */
  fibra?: number
  fibra_pct?: number
}

/** `GET /municipios/{ibge}`: fixo e móvel sem o envelope repetido, centróide e PTTs mais próximos. */
export interface PerfilMunicipio {
  snapshot_date: string
  ibge: string
  nome: string
  uf: string
  fixo?: Omit<SiciMunicipioDetalhe, 'snapshot_date' | 'ibge' | 'nome' | 'uf'> | null
  movel?: Omit<MovelMunicipioDetalhe, 'snapshot_date' | 'ibge' | 'nome' | 'uf'> | null
  centroide?: [number, number] | null
  ptts_proximos?: Array<{ codigo: string; nome: string; lon: number; lat: number; km: number }>
  indicadores?: IndicadoresMunicipio | null
  territorio?: TerritorioMunicipio | null
  /** Série mensal de acessos, HHI e participação das maiores operadoras (`include=serie_mercado`). */
  serie_mercado?: SerieMercadoMunicipio | null
  /** HHI por CNPJ e por grupo (inferido) do município (`include=mercado_grupos`). */
  mercado_grupos?: MercadoGruposMunicipio | null
  /** IPv6 estimado e dependência de trânsito do município (`include=rede_territorio`). */
  rede_territorio?: RedeTerritorioMunicipio | null
  /** Estações do SMP licenciadas no município (`include=erbs`). */
  erbs?: ErbsMunicipio | null
  /** Compromissos do FUST no município (`include=fust`). */
  fust?: FustMunicipio | null
  /** Último resultado do RQUAL no município, por prestadora (`include=qualidade`). */
  qualidade?: QualidadeMunicipio | null
  /** Reclamações na Anatel no município nos últimos anos (`include=reclamacoes`). */
  reclamacoes?: ReclamacoesMunicipio | null
  /** Reclamações finalizadas no Consumidor.gov.br no município (`include=consumidor`). */
  consumidor?: ConsumidorMunicipio | null
}

/** Uma linha de `GET /ufs`: números da UF para a página /estados. */
export interface ResumoUf {
  uf: string
  /** PTTs do IX.br na UF no snapshot, com ou sem coleta (a mesma lista da distância). */
  ptts: number
  /** Dos `ptts`, os que tiveram coleta neste snapshot (ausente em respostas antigas). */
  ptts_com_coleta?: number
  /** `null` quando o snapshot não tem o SICI (ausência, não zero); o mesmo vale para `acessos` e `municipios_sem_ptt`. */
  municipios: number | null
  acessos: number | null
  fibra_pct: number | null
  asns: number
  /** Soma APNIC dos ASNs BR da UF (estimativa). */
  usuarios: number
  municipios_sem_ptt: number | null
  /** Domicílios projetados (IBGE) dos municípios com dado de território; ausente se o snapshot não tem o produto. */
  domicilios?: number | null
  /** Acessos fixos ÷ domicílios projetados (razão; 0,8 = 80 acessos por 100 domicílios). */
  penetracao?: number | null
  /** Dos `asns`, os sem sessão direta em PTT do IX.br (mesmo critério do filtro municipal); ausente em respostas antigas. */
  asns_sem_sessao_ptt?: number
  /** `include=rede`: estimativas e inferências da camada de rede, cada uma com o n ou a cobertura; `null` sem o produto na data. */
  rede?: ResumoUfRede | null
  /** `include=territorio`: mercado não visto (estimativa); `null` sem o produto na data. */
  territorio?: { nao_visto: number; nao_visto_por_100_dom: number | null } | null
}

/** Camada de rede de uma UF em `GET /ufs?include=rede`. A UF é a da sede das redes; prontidão e HHI não são veredito nem ranking. */
export interface ResumoUfRede {
  ipv6_pct: number | null; ipv6_cobertura: number | null
  rov_pct: number | null; rov_cobertura: number | null
  transito_unico_pct: number | null; transito_unico_cobertura: number | null
  /** HHI dos provedores de trânsito inferidos (0 a 10.000) e o n: ASNs com sede na UF e ao menos um provedor inferido. */
  hhi_transito: number | null; hhi_transito_n: number | null
  /** Mediana do índice de prontidão e o n: ASNs com índice. */
  prontidao_mediana: number | null; prontidao_n: number | null
}
export interface RespostaUfs {
  snapshot_date: string; mes_referencia?: string | null; total: number; items: ResumoUf[]
  rede_meta?: { aviso: string; produtos: { rede_territorio: boolean; transito: boolean; prontidao: boolean } }
  territorio_meta?: { produto: boolean; mes_referencia_sici?: string | null; limites?: string; formula?: string }
}

/** `GET /ufs/{uf}`: totais, PTTs, municípios com a distância ao PTT mais próximo e as maiores operadoras sediadas. */
export interface PerfilUf {
  snapshot_date: string
  uf: string
  mes_referencia?: string | null
  totais: {
    /** `null` quando o snapshot não tem o SICI (ausência, não zero). */
    municipios: number | null; acessos: number | null; fibra_pct: number | null; asns: number; usuarios: number
    /** Dos `asns`, os sem sessão direta em PTT do IX.br; ausente em respostas antigas. */
    asns_sem_sessao_ptt?: number
    municipios_sem_ptt: number | null; acessos_sem_ptt: number | null; raio_sem_ptt_km: number
  }
  territorio?: TerritorioUf | null
  /** Acessos, HHI, variações e contagens de CNPJs sem declaração da UF (`include=indicadores`). */
  indicadores?: IndicadoresUf | null
  /** HHI por CNPJ e por grupo da UF (`include=mercado_grupos`). */
  mercado_grupos?: MercadoGruposUf | null
  /** IPv6 estimado, usuários atrás de ROV e dependência de trânsito da UF. */
  rede_territorio?: RedeTerritorioUf | null
  /** Estimativas da TIC Domicílios para a UF (`include=cetic`); null se o snapshot não as tem. */
  cetic?: CeticEstimativasUf | null
  /** Demanda × oferta de banda larga fixa (`include=cetic`); null se o snapshot não a tem. */
  demanda_oferta?: DemandaOfertaUf | null
  /** Estações do SMP licenciadas na UF (`include=erbs`). */
  erbs?: ErbsUf | null
  /** Compromissos do FUST na UF (`include=fust`). */
  fust?: FustUf | null
  /** RQUAL por prestadora (último ano) na UF (`include=qualidade`). */
  qualidade?: QualidadeUf | null
  /** Reclamações na Anatel na UF por ano e serviço (`include=reclamacoes`). */
  reclamacoes?: ReclamacoesUf | null
  /** Empresas com reclamações finalizadas na UF no Consumidor.gov.br (`include=consumidor`). */
  consumidor?: ConsumidorUf | null
  /** Prontidão em segurança de roteamento da UF (`include=prontidao`). */
  prontidao?: ProntidaoUf | null
  /** Concentração dos provedores de trânsito inferidos dos ASNs com sede na UF (`include=transito`). */
  transito?: TransitoUf | null
  radar?: RadarUf | null
  /** Exposição de serviços agregada dos ASNs da UF já lidos, derivada, do Shodan (`include=exposicao`). */
  exposicao?: ExposicaoUf | null
  ixps?: IXPIndexEntry[]
  municipios?: Array<{
    ibge: string; nome: string; acessos: number; operadores: number; hhi: number; fibra_pct?: number | null
    km_ptt: number | null; ptt: string | null; ptt_codigo: string | null
  }>
  /** Sediadas na UF, com acessos declarados no país. */
  operadoras?: { total: number; items: OperadoraRow[] }
  /** CNPJs com acesso fixo declarado em algum município da UF, com os acessos na UF (UF-E2); `acessos` = soma da UF. */
  operadoras_presentes?: { total: number; acessos: number; items: OperadoraPresenteUf[] }
  historico?: HistoricoBloco | null
}

export interface OperadoraPresenteUf {
  cnpj: string; empresa: string; razao_social: string; uf_sede: string
  /** Acessos declarados na UF; `share` é a parcela (%) na soma da UF; `acessos_brasil`, os do país. */
  acessos: number; share: number; municipios: number; acessos_brasil: number; asns: number[]
}

/** `GET /operadoras/{cnpj}`: um bloco por serviço (nulo se o CNPJ não o tem) e a rede uma vez no topo. */
export interface PerfilOperadora {
  snapshot_date: string
  cnpj: string
  scm?: Omit<OperadoraDetalhe, 'snapshot_date' | 'cnpj' | 'rede'> | null
  smp?: Omit<OperadoraMovelDetalhe, 'snapshot_date' | 'cnpj' | 'rede'> | null
  stfc?: Omit<STFCDetailResponse, 'snapshot_date' | 'cnpj'> | null
  seac?: Omit<SEACDetailResponse, 'snapshot_date' | 'cnpj'> | null
  rede?: OperadoraRede | null
  historico?: HistoricoBloco | null
  indicadores?: IndicadoresOperadora | null
  /** Operadoras que mais aparecem nos mesmos municípios (`include=mercado_grupos`). */
  mercado_grupos?: SobreposicaoOperadora | null
  /** Estações do SMP licenciadas da operadora (`include=erbs`); null se não há estação para o CNPJ. */
  erbs?: ErbsOperadora | null
  /** Prontidão em segurança de roteamento dos ASNs da operadora (`include=prontidao`): só o agregado. */
  prontidao?: ProntidaoOperadora | null
  /** Multas constituídas da Anatel contra a empresa (`include=multas`); null se não há multa em SCM, SMP, STFC nem SeAC. */
  multas?: MultasOperadora | null
  /** RQUAL das prestadoras ligadas ao CNPJ (`include=qualidade`); null se nenhuma casa. */
  qualidade?: QualidadeOperadora | null
  /** Reclamações das marcas ligadas ao CNPJ (`include=reclamacoes`); null se nenhuma casa. */
  reclamacoes?: ReclamacoesOperadora | null
  /** Reclamações finalizadas das empresas do Consumidor.gov.br ligadas ao CNPJ (`include=consumidor`); null se nenhuma casa. */
  consumidor?: ConsumidorOperadora | null
}

export interface CoberturaDeclaracao {
  licenciados: number
  informaram_sici: number
  pct_informaram_sici: number | null
  licenciados_com_asn: number
  com_asn_informaram_sici: number
  pct_com_asn_informaram_sici: number | null
}

export interface OperadoraPorAsnRow {
  cnpj: string
  asn: number
  empresa: string
  apnic_users: number | null
  acessos_sici: number | null
}

/** UF → tipo de cliente → faixa de velocidade → acessos. Só o mês de referência. */
export type DistribVelocidade = Record<string, { pf: Record<string, number>; pj: Record<string, number> }>

export interface SiciStats {
  snapshot_date: string
  mes_referencia: string
  meses_disponiveis: string[]
  total_acessos: number
  total_cnpjs: number
  matched_cnpjs: number
  matched_acessos: number
  acessos_pf: number
  acessos_pj: number
  operadoras_ativas: number
  municipios_atendidos: number
  cobertura_declaracao: CoberturaDeclaracao
  por_tecnologia: Record<string, number>
  por_meio: Record<string, number>
  por_uf: Record<string, { acessos: number; pf: number; pj: number }>
  distrib_velocidade: DistribVelocidade
  serie_total: { mes: string; acessos: number; cnpjs: number }[]
  top_operadoras: {
    cnpj: string; empresa: string; razao_social: string; acessos: number
    acessos_pf: number; acessos_pj: number; municipios: number
    tecnologia: string; asns: number[]; grupo_economico: string
  }[]
  top_operadoras_por_asn: OperadoraPorAsnRow[]
}

/** Vínculo ASN ↔ CNPJ (decisão D5), do mais forte ao mais fraco: `cnpj` = mesmo CNPJ (fato); `raiz` = outro CNPJ da mesma raiz de 8
 *  dígitos, matriz ou filial (inferido); `marca` = raiz de outra empresa da mesma marca na tabela curada (inferido); `estrangeiro` = AS de
 *  fora do Brasil ligado pela marca (inferido). */
export type AsnVinculo = 'cnpj' | 'raiz' | 'marca' | 'estrangeiro'

export interface AsnVinculado {
  asn: number
  vinculo: AsnVinculo
  selo: 'fato' | 'inferido'
  /** CNPJ do ASN no Registro.br; nulo no `estrangeiro`. */
  cnpj_registro: string | null
  marca?: string
  base?: string
  data?: string
}

export interface OperadoraRow {
  cnpj: string
  razao_social: string
  nome_fantasia?: string
  empresa?: string
  grupo_economico?: string
  porte?: string
  municipio_sede?: string
  uf_sede?: string
  data_outorga?: string
  outorgas: number
  licenciado: boolean
  ativo: boolean
  mes_referencia?: string
  acessos: number
  acessos_pf: number
  acessos_pj: number
  capacidade_mbps?: number
  velocidade_media_mbps?: number
  velocidade_mediana_mbps?: number
  municipios: number
  tecnologia?: string
  meio?: string
  asns: number[]
  /** ASN brasileiro vinculado (`asn_vinculo` cnpj, raiz ou marca). */
  com_asn: boolean
  asn_vinculo?: AsnVinculo | 'nenhum'
  asns_vinculados?: number[]
  acessos_compartilhados?: boolean
}

export interface PaginatedOperadoras {
  snapshot_date: string
  mes_referencia: string
  total: number
  page: number
  limit: number
  pages: number
  items: OperadoraRow[]
}

export interface OperadoraRedeAsn {
  asn: number
  name: string
  apnic_users: number | null
  apnic_v6_users: number | null
  rir_prefixes_v4_count: number
  rir_prefixes_v6_count: number
  global_prefixes_v4_count: number
  global_prefixes_v6_count: number
  has_rpki: boolean
  has_aspa: boolean
  ixps_direct_count: number
  alerts_count: number
  /** `cnpj` ou `raiz`: a rede soma só os ASNs da mesma pessoa jurídica. */
  vinculo?: AsnVinculo
}

export interface OperadoraRedeAlertGroup {
  category: string
  severity: string
  count: number
  asns: Array<{ asn: number; title: string }>
}

/** Agregação de BGP/RPKI/IX.br/alertas de todos os ASNs do CNPJ — soma direta para
 *  contagens, união para IXPs/RPKI/ASPA, concatenação (nunca soma) para alertas. */
export interface OperadoraRede {
  asn_count: number
  total_apnic_users: number
  total_apnic_v6_users: number
  total_rir_prefixes_v4: number
  total_rir_prefixes_v6: number
  total_global_prefixes_v4: number
  total_global_prefixes_v6: number
  ixps_direct: string[]
  ixps_origin: string[]
  has_rpki: boolean
  has_aspa: boolean
  alertas: { total: number; por_categoria: OperadoraRedeAlertGroup[] }
  asns: OperadoraRedeAsn[]
}

/** Outro CNPJ do mesmo grupo econômico declarado ao SICI (fixo ou móvel). */
export interface GrupoCnpjEntry {
  cnpj: string
  empresa: string
  has_scm?: boolean
  has_smp?: boolean
  has_stfc?: boolean
  has_seac?: boolean
}

// -------------------------------------------------------------------------
// Grupos societários (Receita Federal — enrich.socios_grupos)
// -------------------------------------------------------------------------

/** Classificação de um grupo (cluster transitivo): 'total' = toda relação
 *  interna é quadro idêntico/controle exclusivo; 'parcial' = toda relação é
 *  sócio em comum/controle não exclusivo; 'misto' = tem as duas;
 *  'individual' = empresa sem relação societária com nenhuma outra da base
 *  ("grupo de uma empresa só"). */
export type GrupoClassificacao = 'total' | 'misto' | 'parcial' | 'individual'

/** Tipo de relação direta entre duas empresas (par a par, não a cadeia do grupo). */
export type TipoRelacaoSocietaria =
  | 'quadro_identico'
  | 'controle_exclusivo_exercido'
  | 'controle_exclusivo_recebido'
  | 'socios_em_comum'
  | 'controle_parcial_exercido'
  | 'controle_parcial_recebido'

export interface GrupoSocietarioMunicipio {
  ibge: string
  nome: string
  uf: string
  acessos: number
  pf: number
  pj: number
}

export interface GrupoSocietarioCnpj {
  cnpj: string
  empresa: string
  assinantes: number
  /** `false` só na S.A.: o quadro da Receita traz gestão, não acionistas (P8). Ausente nas demais. */
  grupo_inferivel?: false
  asns?: number[]
  has_scm?: boolean
  has_smp?: boolean
  has_stfc?: boolean
  has_seac?: boolean
}

/** Regra pela qual o nome do grupo foi escolhido (D5): marca curada, o CNPJ com mais acessos no SICI, ou o menor CNPJ (nenhum declara acessos). */
export type NomeGrupoRegra = 'marca_curada' | 'maior_acesso_sici' | 'menor_cnpj'

/** S.A. no agrupamento (P8): o quadro da Receita de S.A. não traz acionistas, então não liga. Presente só quando `grupo_inferivel` é `false`. */
export interface GrupoNaoInferivel {
  grupo_inferivel?: false
  grupo_inferivel_motivo?: string
  grupo_inferivel_rotulo?: string
  como_ler?: string
}

export interface GrupoSocietarioRow extends GrupoNaoInferivel {
  grupo_id: string
  /** Quantas empresas (raízes) do grupo são S.A. */
  sociedades_anonimas?: number
  /** Nome de exibição do grupo e a regra visível que o escolheu; é rótulo de navegação do conjunto inferido, não "o grupo econômico" da marca. */
  nome: string
  nome_regra: NomeGrupoRegra
  nome_regra_texto: string
  /** Marca curada (justificativa) ou o CNPJ de onde veio o nome. */
  nome_base: string
  classificacao: GrupoClassificacao
  tamanho: number
  assinantes: number
  usuarios_apnic: number
  /** Algum AS de alguma empresa do grupo origina bloco na tabela BGP global. */
  visibilidade_bgp: boolean
  /** ASNs do grupo (mesmo CNPJ e mesma raiz, cada um uma vez) e os que entram só pela raiz (vínculo inferido, D5). */
  asns?: number[]
  asns_raiz?: number[]
  cnpjs: GrupoSocietarioCnpj[]
  municipios: GrupoSocietarioMunicipio[]
}

export interface GrupoSocietarioListResponse {
  snapshot_date: string
  total: number
  total_grupos?: number
  total_individuais?: number
  grupos: GrupoSocietarioRow[]
}

/** `GET /grupos/{grupo_id}`: o grupo consolidado, só estrutura entre empresas (PJ); cada soma diz quantas empresas têm o dado. */
export interface GrupoDetalhe extends GrupoNaoInferivel {
  sociedades_anonimas?: number
  snapshot_date: string
  grupo_id: string
  /** Preenchido quando a rota recebeu um `grupo_id` antigo (raiz da union-find de snapshots anteriores): o id pedido; `grupo_id` é o estável (GRUPO-E14). */
  redirecionado_de?: string | null
  nome: string
  nome_regra: NomeGrupoRegra
  nome_regra_texto: string
  nome_base: string
  classificacao: GrupoClassificacao
  tamanho: number
  empresas: number
  assinantes: number
  usuarios_apnic: number
  visibilidade_bgp: boolean
  cnpjs: GrupoSocietarioCnpj[]
  /** ASNs do grupo: mesmo CNPJ de uma das empresas (fato) e mesma raiz de 8 dígitos (inferido), cada um uma vez. */
  asns: number[]
  asns_vinculados?: Array<Omit<AsnVinculado, 'marca' | 'base' | 'data'>>
  regra_vinculo?: string
  municipios: GrupoSocietarioMunicipio[]
  credito_publico: { empresas_com_registro: number; operacoes: number; contratado: number; desembolsado: number; natureza: string }
  sancoes: { empresas_com_registro: number; vigentes: number; futuras: number; encerradas: number; natureza: string }
  contratos: { empresas_lidas: number; empresas_com_resultado: number; itens: number; contratacoes: number; valor_homologado: number; natureza: string }
  limites: string
}

/** Empresa relacionada a um CNPJ com evidência direta (par a par, não a cadeia do grupo). */
export interface EmpresaRelacionada {
  cnpj: string
  empresa: string
  tipo_relacao: TipoRelacaoSocietaria
  asns: number[]
  socios_em_comum?: number
  nomes_em_comum?: string[]
  total_socios_da_controlada?: number
  /** Classes de qualificação dos sócios que sustentam a ligação (`socio`, `socio_administrador`, `acionista`, `titular`); sem nomes. */
  classes_qualificacao?: string[]
  has_scm?: boolean
  has_smp?: boolean
  has_stfc?: boolean
  has_seac?: boolean
}

/** O grupo societário do CNPJ para o cabeçalho da operadora: nome por regra visível e os outros integrantes (inferido do quadro da Receita). */
export interface GrupoSocietarioResumo extends GrupoNaoInferivel {
  grupo_id: string
  classificacao: GrupoClassificacao
  tamanho: number
  nome: string
  nome_regra: NomeGrupoRegra
  nome_regra_texto: string
  nome_base: string
  integrantes: GrupoCnpjEntry[]
  integrantes_total: number
}

export interface EmpresasRelacionadasResponse extends GrupoNaoInferivel {
  snapshot_date: string
  cnpj: string
  /** `null` se o CNPJ não está no cruzamento. */
  grupo_societario?: GrupoSocietarioResumo | null
  /** Grupo societário do CNPJ: `GET /grupos/{grupo_id}` e a página `/grupo/:id`; `null` se o CNPJ não está no cruzamento. */
  grupo_id?: string | null
  mesmo_grupo: EmpresaRelacionada[]
  relacionadas_parcial: EmpresaRelacionada[]
}

/** Dados de uma operadora por CNPJ. Existe se houver ASN, outorga SCM OU SICI —
 *  os campos de SICI (herdados de SiciAcessos, exceto cnpj/asns/serie) vêm ausentes
 *  quando o CNPJ não declara acesso. */
export interface OperadoraDetalhe extends Partial<Omit<SiciAcessos, 'cnpj' | 'asns'>> {
  snapshot_date: string
  cnpj: string
  asns: number[]
  /** Vínculo ASN ↔ CNPJ (D5): `asns` são os do mesmo CNPJ; `asns_vinculados`, todos, com o vínculo e o selo de cada um. */
  asn_vinculo?: AsnVinculo | 'nenhum'
  asns_vinculados?: AsnVinculado[]
  regra_vinculo?: string
  outorgas_scm: SCMRecord[]
  rede: OperadoraRede | null
  municipios_detalhe?: (SiciMunicipioRow & { ibge: string })[]
  /** Contagens de contatos disponíveis (sem valores) — valores em .../contacts */
  contacts_available?: { peeringdb: number; anatel: number; receita: boolean; total: number }
  grupo_cnpjs?: GrupoCnpjEntry[]
}

/** Resposta de GET /acessos/operadora/{cnpj}/contacts (protegido por login). */
export interface OperadoraContactsResponse {
  cnpj: string
  contacts: ASNContact[]
  /** Cota de contatos da conta (a operadora custa o número de ASNs do CNPJ). */
  cota?: { restante_hoje: number | null }
}

export interface SiciDivergenciaRow extends SiciDivergencia {
  asn: number
  name: string
  cnpj?: string | null
}

export interface SiciDivergenciasResponse {
  snapshot_date: string
  mes_referencia: string
  distribuicao: Record<string, number>
  total: number
  items: SiciDivergenciaRow[]
}

export interface SiciDivergenciaSCMRow {
  asn: number
  name: string
  cnpj: string
  empresa: string
  apnic_users: number
  /** Acessos de Pessoa Física (B2C) declarados ao SICI */
  acessos_pf: number
  /** Acessos de Pessoa Jurídica (B2B) declarados ao SICI */
  acessos_pj: number
  /** k_pf × acessos_pf + k_pj × acessos_pj */
  esperado: number
  excesso: number
  /** apnic_users / esperado; null quando esperado = 0 */
  razao: number | null
}

export interface SiciDivergenciasSCMResponse {
  snapshot_date: string
  mes_referencia: string
  k_pf: number
  k_pj: number
  min_razao: number
  total: number
  sem_acessos: number
  items: SiciDivergenciaSCMRow[]
}

export interface PaginatedSCMs {
  snapshot_date: string
  total: number
  page: number
  limit: number
  pages: number
  items: SCMRecord[]
}

export interface SCMStats {
  snapshot_date: string
  total: number
  unique_cnpjs: number
  geolocated: number
  matched_asns: number
  cnpjs_with_asn: number
  total_asns_br: number
  as_with_scm: number
  as_without_scm: number
  by_uf: Record<string, number>
  uf_breakdown: Array<{ uf: string; with_asn: number; without_asn: number }>
  top_municipios: Array<{ municipio: string; uf: string; count: number }>
}

export interface AsnDaOrganizacao {
  asn: number
  name: string
  apnic_users: number | null
  apnic_v6_users: number | null
  pct_v6: number | null
  global_prefixes_v4_count: number
  global_prefixes_v6_count: number
  rir_prefixes_v4_count: number
  rir_prefixes_v6_count: number
  has_rpki: boolean | null
  has_aspa: boolean | null
  ixps_direct_count: number
}

export interface OrganizacaoVariosAsns {
  cnpj: string
  razao_social: string
  nome_fantasia: string
  uf: string
  asn_count: number
  total_apnic_users: number
  total_v4_blocks: number
  total_v6_blocks: number
  asns: Array<AsnDaOrganizacao & { cnpj?: string; vinculo?: 'cnpj' | 'raiz' }>
  /** Só com `chave=raiz`: a raiz de 8 dígitos e quantos CNPJs distintos dela têm ASN. */
  raiz?: string
  cnpjs?: number
}

export interface AsnsPorOrganizacaoResponse {
  snapshot_date: string
  chave?: 'cnpj' | 'raiz'
  total: number
  groups: OrganizacaoVariosAsns[]
}

export interface SCMDetailResponse {
  snapshot_date: string
  cnpj: string
  total: number
  outorgas: SCMRecord[]
}

// -------------------------------------------------------------------------
// SMP — Outorgas Anatel (Serviço Móvel Pessoal)
// -------------------------------------------------------------------------

/** Rede virtual (MVNO/MVNA).
 *  "host" = Prestadora Origem, dona da outorga/rede, que credencia terceiros.
 *  "credenciada" = MVNO puro, opera por contrato homologado, sem outorga SMP
 *  própria na maioria dos casos (por isso pode aparecer como registro sintético,
 *  sem endereço/data_outorga). Não distingue MVNA (autorizada de rede virtual)
 *  por falta de dataset aberto que identifique esse papel. */
export interface SMPRedeVirtual {
  papel: 'host' | 'credenciada'
  prestadora_origem_cnpj?: string
  prestadora_origem_nome?: string
  credenciadas_count?: number
}

/** Espelha SCMRecord, sem os campos de SICI fixo (o bloco de acessos móveis vem
 *  à parte, em SiciMovelAcessos). Universo pequeno (~30 CNPJs "próprias" + ~230
 *  credenciadas de rede virtual). */
export interface SMPRecord {
  cnpj: string
  razao_social: string
  nome_fantasia?: string
  data_outorga?: string
  municipio?: string
  uf?: string
  codigo_ibge?: string
  telefone?: string
  email?: string
  situacao?: string
  geo_confidence?: 'exact_address' | 'cep_centroid' | 'city_centroid' | 'unknown'
  geo_source?: string
  asns: number[]
  rede_virtual?: SMPRedeVirtual
}

export interface PaginatedSMPs {
  snapshot_date: string
  total: number
  page: number
  limit: number
  pages: number
  items: SMPRecord[]
}

export interface SMPStats {
  snapshot_date: string
  total: number
  unique_cnpjs: number
  geolocated: number
  matched_asns: number
  cnpjs_with_asn: number
  by_uf: Record<string, number>
  uf_breakdown: Array<{ uf: string; with_asn: number; without_asn: number }>
  rede_virtual: { hosts: number; credenciadas: number; credenciadas_sem_outorga_propria: number }
}

export interface SMPDetailResponse {
  snapshot_date: string
  cnpj: string
  total: number
  outorgas: SMPRecord[]
}

// -------------------------------------------------------------------------
// STFC — Outorgas Anatel (Serviço Telefônico Fixo Comutado)
// -------------------------------------------------------------------------

/** Espelha STFCRecord/SCMRecord — sem SICI (não há acessos declarados para STFC). Universo maior que SMP: ~1.700 CNPJs. */
export interface STFCRecord {
  cnpj: string
  razao_social: string
  nome_fantasia?: string
  data_outorga?: string
  municipio?: string
  uf?: string
  codigo_ibge?: string
  telefone?: string
  email?: string
  situacao?: string
  geo_confidence?: 'exact_address' | 'cep_centroid' | 'city_centroid' | 'unknown'
  geo_source?: string
  asns: number[]
}

export interface PaginatedSTFCs {
  snapshot_date: string
  total: number
  page: number
  limit: number
  pages: number
  items: STFCRecord[]
}

export interface STFCStats {
  snapshot_date: string
  total: number
  unique_cnpjs: number
  geolocated: number
  matched_asns: number
  cnpjs_with_asn: number
  by_uf: Record<string, number>
  uf_breakdown: Array<{ uf: string; with_asn: number; without_asn: number }>
}

export interface STFCDetailResponse {
  snapshot_date: string
  cnpj: string
  total: number
  outorgas: STFCRecord[]
}


// -------------------------------------------------------------------------
// SEAC — Outorgas Anatel (Serviço de Acesso Condicionado)
// -------------------------------------------------------------------------

/** Espelha SEACRecord/SCMRecord — sem SICI (não há acessos declarados para SEAC). TV por assinatura: ~1.400 CNPJs. */
export interface SEACRecord {
  cnpj: string
  razao_social: string
  nome_fantasia?: string
  data_outorga?: string
  municipio?: string
  uf?: string
  codigo_ibge?: string
  telefone?: string
  email?: string
  situacao?: string
  geo_confidence?: 'exact_address' | 'cep_centroid' | 'city_centroid' | 'unknown'
  geo_source?: string
  asns: number[]
}

export interface PaginatedSEACs {
  snapshot_date: string
  total: number
  page: number
  limit: number
  pages: number
  items: SEACRecord[]
}

export interface SEACStats {
  snapshot_date: string
  total: number
  unique_cnpjs: number
  geolocated: number
  matched_asns: number
  cnpjs_with_asn: number
  by_uf: Record<string, number>
  uf_breakdown: Array<{ uf: string; with_asn: number; without_asn: number }>
}

export interface SEACDetailResponse {
  snapshot_date: string
  cnpj: string
  total: number
  outorgas: SEACRecord[]
}


// -------------------------------------------------------------------------
// SICI móvel — Acessos de telefonia móvel (SMP) declarados à Anatel
// -------------------------------------------------------------------------

export interface SiciMovelAcessos {
  snapshot_date: string
  /** Mês da declaração ao SICI — cite junto com snapshot_date */
  mes_referencia: string
  asn?: number
  cnpj: string
  empresa?: string
  grupo?: string
  porte?: string
  /** Acessos padrão (voz/dados de linha pessoal) — exclui M2M e PONTO_DE_SERVICO */
  acessos: number
  /** Pessoa Física (B2C) */
  pf: number
  /** Pessoa Jurídica (B2B) */
  pj: number
  /** Chips M2M, à parte do total `acessos` */
  acessos_m2m?: number
  acessos_outros?: number
  municipios: number
  geracao_predominante?: string
  por_geracao?: Record<string, number>
  por_modalidade?: Record<string, number>
  por_produto?: Record<string, number>
  /** CNPJ com mais de um ASN: o total vale para cada um. Nunca some ASes do mesmo CNPJ. */
  acessos_compartilhados: boolean
  asns: number[]
  serie: SiciSeriePoint[]
}

export interface MovelMunicipioRow {
  ibge: string
  nome: string
  uf: string
  acessos: number
  pf: number
  pj: number
  municipio_acessos?: number
  share?: number | null
  municipio_operadores?: number
}

export interface MovelMunicipioDetalhe {
  snapshot_date: string
  mes_referencia: string
  ibge: string
  nome: string
  uf: string
  acessos: number
  pf: number
  pj: number
  operadores: SiciOperador[]
  operadores_count: number
  hhi: number
  share_maior: number
}

export interface SiciMovelStats {
  snapshot_date: string
  mes_referencia: string
  meses_disponiveis: string[]
  total_acessos: number
  total_cnpjs: number
  matched_cnpjs: number
  matched_acessos: number
  acessos_pf: number
  acessos_pj: number
  acessos_m2m: number
  operadoras_ativas: number
  municipios_atendidos: number
  cobertura_declaracao: { licenciados: number; informaram_sici: number; pct_informaram_sici: number | null }
  por_geracao: Record<string, number>
  por_modalidade: Record<string, number>
  distrib_modalidade: Record<string, { pf: Record<string, number>; pj: Record<string, number> }>
  serie_total: { mes: string; acessos: number; cnpjs: number }[]
  top_operadoras: {
    cnpj: string; empresa: string; razao_social: string; acessos: number
    acessos_pf: number; acessos_pj: number; acessos_m2m: number; municipios: number
    geracao_predominante: string; asns: number[]; grupo_economico: string
  }[]
}

export interface OperadoraMovelRow {
  cnpj: string
  razao_social: string
  nome_fantasia?: string
  empresa?: string
  grupo_economico?: string
  porte?: string
  municipio_sede?: string
  uf_sede?: string
  data_outorga?: string
  outorgas: number
  licenciado: boolean
  ativo: boolean
  mes_referencia?: string
  acessos: number
  acessos_pf: number
  acessos_pj: number
  acessos_m2m?: number
  municipios: number
  geracao_predominante?: string
  asns: number[]
  com_asn: boolean
  acessos_compartilhados?: boolean
  rede_virtual?: SMPRedeVirtual
}

export interface PaginatedOperadorasMovel {
  snapshot_date: string
  mes_referencia: string
  total: number
  page: number
  limit: number
  pages: number
  items: OperadoraMovelRow[]
}

/** Dados de uma operadora móvel por CNPJ. Existe se houver ASN, outorga SMP OU
 *  acesso móvel declarado — os campos de SICI vêm ausentes quando não há declaração. */
export interface OperadoraMovelDetalhe extends Partial<Omit<SiciMovelAcessos, 'cnpj' | 'asns'>> {
  snapshot_date: string
  cnpj: string
  asns: number[]
  /** Vínculo ASN ↔ CNPJ (D5): `asns` são os do mesmo CNPJ; `asns_vinculados`, todos, com o vínculo e o selo de cada um. */
  asn_vinculo?: AsnVinculo | 'nenhum'
  asns_vinculados?: AsnVinculado[]
  regra_vinculo?: string
  outorgas_smp: SMPRecord[]
  rede: OperadoraRede | null
  municipios_detalhe?: (MovelMunicipioRow & { ibge: string })[]
  contacts_available?: { peeringdb: number; anatel: number; receita: boolean; total: number }
  grupo_cnpjs?: GrupoCnpjEntry[]
}

// -------------------------------------------------------------------------
// PeeringDB Contacts
// -------------------------------------------------------------------------

export interface RpkiSummary {
  snapshot_date: string
  br_asns_total: number
  br_asns_with_roa: number
  br_asns_with_aspa: number
  br_asns_with_aspa_of_roa: number
  br_space_v4_total_24: number
  br_space_v4_roa_24: number
  br_space_v6_total_48: number
  br_space_v6_roa_48: number
}

export type EstratoRelacao = 'ambos' | 'so_caida' | 'so_tripla' | 'conflito' | 'sem_evidencia'
export type NivelRelacao = 'declarado' | 'confirmado' | 'provavel' | 'possivel' | 'sem_classificacao'
export interface RelacaoItem {
  asn: number
  nome?: string
  p: number
  nivel: NivelRelacao
  afi: ('v4' | 'v6')[]
  /** Relação complexa (v4 e v6 divergem com força): `hibrida` (p2c numa família e p2p na outra) ou `inversa`; o papel do outro AS em cada família. */
  subtipo?: 'hibrida' | 'inversa' | null
  v4?: 'provedor' | 'cliente' | 'par' | null
  v6?: 'provedor' | 'cliente' | 'par' | null
  /** Mudança vista mas ainda não confirmada pela histerese: o estado mostrado é o anterior. */
  mudanca_pendente?: boolean
  /** Estrato de evidência independente do elo provedor-cliente: só p2c. */
  estrato?: EstratoRelacao
  /** Taxa de acerto observada no ASPA para o estrato; ausente ou null quando o estrato não tem eventos suficientes para estimar. */
  p_calibrada?: number | null
}
type PorAfi<T> = { v4: T; v6: T }
/** Fragmento `relacoes` do documento do ASN: o que o ARC inferiu sobre os elos deste AS. `null` = indeterminado. */
export interface AsnRelacoes {
  algoritmo: string
  provedores: RelacaoItem[]
  clientes: RelacaoItem[]
  pares: RelacaoItem[]
  irmaos: RelacaoItem[]
  /** v4 e v6 divergentes com força (ARC v2). */
  complexas?: RelacaoItem[]
  sem_classificacao: RelacaoItem[]
  /** A probabilidade foi calibrada contra o ASPA dentro do limite de ECE (régua do painel), por família. */
  p_calibrada?: { v4: boolean; v6: boolean }
  clientes_total?: number
  pares_total?: number
  irmaos_total?: number
  sem_classificacao_total?: number
  /** Provedores de nível confirmado ou superior. */
  n_provedores: PorAfi<number>
  /** Provedores de nível provável ou superior, sem o próprio AS nem irmãos inferidos (ausente em snapshots anteriores a 2026-11). */
  n_provedores_provavel?: PorAfi<number>
  visibilidade: PorAfi<{ vps: number; ptts: number; coletores: boolean }>
  multihomed: PorAfi<boolean | null>
  single_homed: PorAfi<boolean | null>
}

/** Uma linha de `GET /outorgas`: um CNPJ com os serviços de outorga que ele tem e o que declarou ao SICI. */
export interface OutorgaCnpj {
  cnpj: string
  razao_social: string
  nome_fantasia: string
  uf: string
  municipio: string
  /** A mais antiga entre os serviços (DD/MM/AAAA); `data_outorga_por_servico` traz cada uma. */
  data_outorga: string
  data_outorga_por_servico: Partial<Record<'SCM' | 'SMP' | 'STFC' | 'SeAC', string>>
  servicos: Array<'SCM' | 'SMP' | 'STFC' | 'SeAC'>
  outorgas: number
  asns: number[]
  acessos: number
  acessos_fixo: number
  acessos_movel: number
  pj_fixo: number
  pj_movel: number
  municipios_fixo: number
  municipios_movel: number
  tecnologia_fixo: string
  ativo: boolean
  porte: string
}

export interface PaginatedOutorgas {
  snapshot_date: string
  total: number
  page: number
  limit: number
  pages: number
  items: OutorgaCnpj[]
}


/** Bloco `historico` dos perfis consolidados: série e eventos recentes da entidade. O anônimo recebe só as datas atuais (`completo: false`). */
export interface HistoricoBloco {
  completo: boolean
  snapshots_com_historico: number
  colunas: string[]
  serie: Array<{ date: string } & Record<string, number | string | null | undefined>>
  /** Comparabilidade de cada coluna da série (PT-28, `core/comparabilidade.py`): cortes, trechos, linha só com pontos comparáveis e variação só entre comparáveis. */
  metricas?: MetricaHistorico[]
  regra?: { versao: number; min_pontos_linha: number; motivos: Record<string, string>; texto: string[] }
  eventos: HistoricoEvento[]
  eventos_total: number
}

/** Diferença observada entre dois snapshots. `estado`: pendente = ainda em confirmação; confirmado = persistiu pela janela. */
export interface HistoricoEvento {
  data: string
  tipo: string
  entidade: string
  chave: string
  de?: unknown
  para?: unknown
  estado: 'pendente' | 'confirmado' | 'revertido'
  destaque?: boolean
  /** Motivo da data atípica marcada (D7): o evento é mantido, mas a data é sinalizada. */
  atipico?: string
}

export interface MetricaHistorico {
  id: string
  desenhar_linha: boolean
  segmentos: number[][]
  pontos: Array<{ date: string; comparavel_com_anterior: boolean | null; motivos: string[] }>
  variacao?: { de: string; para: string; calculada: boolean; absoluta: number | null; unidade: string | null; pct: number | null; motivos: string[] }
  nota?: string
}

/** Indicadores do SICI. Dado DECLARADO à Anatel; parcela e HHI são sobre acessos declarados, não sobre receita. */
export interface VariacaoSici { abs: number; pct: number | null }
export interface IndicadoresOperadora {
  mes_referencia: string
  metodologia: string
  empresa?: string
  acessos?: number
  share_br?: number
  posicao_br?: number
  var_mm?: VariacaoSici
  var_aa?: VariacaoSici
  meses_declinio?: number
  em_declinio?: boolean
  parou_de_declarar?: { empresa: string; ultimo_mes_declarado: string; meses_sem_declarar: number; acessos_no_ultimo_mes: number; empresa_fonte?: 'sici' | 'cadastro_scm'; scm_vigente?: boolean; grupo_id?: string | null; grupo_declara?: boolean }
  sem_declaracao?: ItemSemDeclaracao
}
/** Maior ganho ou perda em 12 meses; `cnpjs` presente quando os CNPJs de uma mesma marca foram somados (mudança de CNPJ provável, inferido). */
export interface GanhoPerdaMunicipio { cnpj: string; empresa: string; acessos: number; cnpjs?: string[] }
/** CNPJs de mesmo nome fantasia com movimento oposto em 12 meses que se compensa em 80% ou mais (inferido; não prova sucessão). */
export interface MudancaCnpjMunicipio { marca: string; de_cnpj: string; para_cnpj: string; acessos_de: number; acessos_para: number }
export interface IndicadoresMunicipio {
  mes_referencia: string
  metodologia: string
  acessos: number
  n_operadoras: number
  hhi: number
  avisos?: string[]
  lider?: { cnpj: string; empresa: string; share: number }
  var_mm_pct?: number | null
  var_aa_pct?: number | null
  ganho_aa?: GanhoPerdaMunicipio
  perda_aa?: GanhoPerdaMunicipio
  /** Fatos sobre a declaração no município (PT-26): CNPJ sem declaração desde um mês e primeira declaração. Ausente sem evento. */
  eventos?: EventoDeclaracaoMunicipio[]
  /** Mudança de CNPJ provável entre CNPJs da mesma marca (inferido); ganho e perda já vêm com os dois somados. */
  mudancas_cnpj?: MudancaCnpjMunicipio[]
}
/** `include=indicadores` da UF: acessos, HHI e variações da UF e as contagens de CNPJs sem declaração (PT-26). */
export interface IndicadoresUf {
  mes_referencia: string
  metodologia: string
  acessos: number
  n_operadoras: number
  hhi: number
  var_mm_pct?: number | null
  var_aa_pct?: number | null
  sem_declaracao?: { cnpjs_sem_declaracao: number; com_usuarios_apnic: number; sem_usuarios: number; nao_comparavel: number; usuarios_apnic: number }
}
export type EventoDeclaracaoMunicipio = {
  cnpj: string
  empresa: string
  tipo: 'sem_declaracao_desde' | 'primeira_declaracao'
  /** AAAA-MM: primeiro mês sem declaração (sem_declaracao_desde) ou o da primeira declaração. */
  mes: string
  ultimo_mes_declarado?: string
  /** Acessos no município no mês `mes_acessos` (o último mês em que o município o tem, ou o da primeira declaração). */
  acessos: number | null
  mes_acessos: string
}
export interface RankingBase { snapshot_date: string; mes_referencia: string; fonte: string; metodologia: string; criterio: string; escopo: { uf?: string; pais?: string }; total: number }
export interface LinhaRankingOperadora {
  posicao: number
  cnpj: string
  empresa: string
  uf_sede: string
  acessos: number
  share: number
  meses_declinio: number
  em_declinio: boolean
  var_mm_abs?: number
  var_mm_pct?: number | null
  var_aa_abs?: number
  var_aa_pct?: number | null
  /** Acessos no mesmo mês do ano anterior (a base da variação); 0 = ainda não declarava. */
  base_aa?: number
  /** Base abaixo de `base_pequena_abaixo_de`: só rótulo, a linha fica onde está. */
  base_pequena?: boolean
}
export interface RankingOperadoras extends RankingBase { base_pequena_abaixo_de?: number; items: LinhaRankingOperadora[] }
export interface LinhaRankingMunicipio extends IndicadoresMunicipio0 { posicao: number; ibge: string; uf: string; nome: string }
interface IndicadoresMunicipio0 { acessos: number; n_operadoras: number; hhi: number; avisos?: string[]; lider?: { cnpj: string; empresa: string; share: number }; var_mm_pct?: number | null; var_aa_pct?: number | null; ganho_aa?: GanhoPerdaMunicipio; perda_aa?: GanhoPerdaMunicipio }
export interface RankingMunicipios extends RankingBase { items: LinhaRankingMunicipio[] }
export type ClasseSemDeclaracao = 'com_usuarios_apnic' | 'sem_usuarios' | 'nao_comparavel'
export interface ItemSemDeclaracao {
  razao_social: string
  uf: string
  n_outorgas: number
  desde: string | null
  asns: number[]
  usuarios_apnic: number | null
  classe: ClasseSemDeclaracao
  grupo_id?: string | null
  grupo_declara?: boolean
  /** CNPJ da prestadora de origem, quando o CNPJ é credenciado de rede virtual no SMP (a origem declara os acessos dele; RGST, Res. 777/2025). */
  rede_virtual_origem?: string
}
export interface LinhaSemDeclaracao extends Partial<ItemSemDeclaracao> { posicao: number; cnpj: string }
export interface LinhaParou {
  posicao: number; cnpj: string; empresa: string; ultimo_mes_declarado: string; meses_sem_declarar: number; acessos_no_ultimo_mes: number
  /** De onde vem `empresa`: o último nome declarado ao SICI ou, na falta, a razão social do cadastro SCM. Ausente em snapshots antigos. */
  empresa_fonte?: 'sici' | 'cadastro_scm'
  /** O CNPJ tem outorga SCM no snapshot. Ausente em snapshots antigos (a tela mostra "—", não "não"). */
  scm_vigente?: boolean
  grupo_id?: string | null
  grupo_declara?: boolean
}
export interface SemDeclaracaoSici {
  snapshot_date: string
  mes_referencia: string
  fonte: string
  metodologia: string
  criterio: string
  tipo: 'outorga_sem_declaracao' | 'parou_de_declarar'
  total: number
  parametros: Record<string, number>
  por_uf?: Record<string, { cnpjs_sem_declaracao: number; com_usuarios_apnic: number; sem_usuarios: number; nao_comparavel: number; usuarios_apnic: number; grupo_declarou?: number; credenciadas_rede_virtual?: number }>
  items: Array<LinhaSemDeclaracao & Partial<LinhaParou>>
}

/** Penetração e mercado não visto. `nao_visto` é ESTIMATIVA (a taxa da PNAD inclui quem usa só o celular). */
export interface TerritorioMeta {
  snapshot_date: string
  mes_referencia_sici: string
  censo_ano: string
  estimativa_ano?: string | null
  pnad_ano: string
  ano_projecao_domicilios?: string | null
  fonte: string
  formulas: Record<string, string>
  limites: string
}
interface TerritorioNumeros {
  populacao?: number
  populacao_estimada?: number
  domicilios?: number
  domicilios_projetados?: number
  fator_projecao_uf?: number
  penetracao_censo?: number
  acessos?: number
  acessos_pf?: number
  penetracao?: number
  penetracao_pf?: number
  domicilios_com_internet_est?: number
  nao_visto?: number
  nao_visto_pct?: number
}
export interface TerritorioMunicipio extends TerritorioMeta, TerritorioNumeros {
  nome: string
  uf: string
  area_km2?: number
  sem_declaracao_sici?: boolean
  ptt_proximo?: string
  ptt_proximo_nome?: string
  pix_proximo?: string | null
  km_ptt?: number
  sem_ptt_proximo?: boolean
}
export interface TerritorioUf extends TerritorioMeta, TerritorioNumeros {
  municipios: number
  taxa_internet_pnad?: number
  cv_domicilios_pnad_pct?: number
}
export interface LinhaTerritorio extends TerritorioNumeros {
  posicao: number
  ibge: string
  nome: string
  uf: string
  km_ptt?: number
  fibra_pct?: number
  /** Reclamações na Anatel por 100 mil habitantes no último ano completo (`reclam_ano`); só com 30 ou mais reclamações */
  reclam_100mil?: number
  reclam_ano?: number
  ptt_proximo?: string
  ptt_proximo_nome?: string
  /** Nome do PIX (local de interconexão) mais próximo, do cadastro do IX.br; o PTT é `ptt_proximo`. */
  pix_proximo?: string | null
  /** ASNs brasileiros com sede no município (pelo CNPJ), com sessão direta em PTT e com rotas vistas num PTT; ausente se o produto não foi publicado. Sede não é área de operação. */
  redes_sede?: { asns: number; sessao_ptt: number; rotas_ptt: number }
  sem_ptt_proximo?: boolean
}
/** Uma feição próxima: distância ao ponto e propriedades curtas da camada (nome, status, dono…). */
export interface ItemInfra { distancia_km: number; name?: string; status?: string; [propriedade: string]: string | number | boolean | undefined }
export interface CamadaInfra { camada: string; fonte: string; total: number; itens: ItemInfra[]; por_status?: Record<string, number> }
/** `GET /territorio/infra-proximos`: camadas leves do mapa e instalações do PeeringDB num raio. Distância em linha reta (inferido); geometria aproximada. */
export interface InfraProximos {
  snapshot_date: string
  ponto: { lat: number; lon: number }
  raio_km: number
  camadas: Partial<Record<'cabos' | 'pontos_aterrissagem' | 'enlaces' | 'linhas_transmissao', CamadaInfra>>
  indisponiveis: string[]
  instalacoes: { raio_km: number; total: number; fonte: string; itens: Array<{ distancia_km: number; id: number | null; nome: string | null; cidade: string | null; uf: string | null }> }
}
/** Soma de um grupo de municípios em `GET /territorio/resumo`; a razão é nula sem município com domicílios projetados (nunca zero). */
export interface AgregadoTerritorio {
  municipios: number
  populacao_estimada: number
  domicilios_projetados: number
  acessos: number
  nao_visto: number
  acessos_por_domicilio: number | null
}
/** `GET /territorio/resumo` (PT-22): agregados do país ou da UF por distância em linha reta ao PTT do IX.br mais próximo; os três grupos somam o `total`. */
export interface ResumoTerritorio extends TerritorioMeta {
  escopo: { uf?: string; pais?: string }
  raio_sem_ptt_km: number
  total: AgregadoTerritorio
  a_mais_de_100km: AgregadoTerritorio
  ate_100km: AgregadoTerritorio
  sem_distancia: AgregadoTerritorio
  penetracao: { porte_minimo_domicilios: number; municipios_com_penetracao: number; municipios_abaixo_do_porte: number; municipios_sem_domicilios: number; com_mais_acessos_que_domicilios: number }
  criterio: string
}
export interface RankingTerritorio {
  snapshot_date: string
  mes_referencia_sici: string
  censo_ano: string
  estimativa_ano?: string | null
  pnad_ano: string
  limites: string
  criterio: string
  escopo: { uf?: string; pais?: string }
  total: number
  items: LinhaTerritorio[]
}

/** Segurança de roteamento por ASN, parte A. ROV/DNSSEC: MEDIÇÃO do APNIC por amostragem (alto = valida); AS Rank: inferência do CAIDA; bogon: fato contra as listas citadas. */
export interface SegurancaFontes {
  rov: { fonte: string; as_of?: string | null; janela_dias?: number | null; copyright?: string | null }
  dnssec: { fonte: string; as_of?: string | null; janela_dias?: number | null; copyright?: string | null }
  asrank: { fonte: string; coletado_em?: string | null; citacao?: string | null }
  bogons: { fonte: string; lista_cymru_em?: string | null }
}
export interface SegurancaAsn {
  snapshot_date: string
  fontes: SegurancaFontes
  parametros: { min_amostras: number }
  limites: string
  rov?: { validates_pct: number; amostras: number }
  dnssec?: { validates_pct: number; parcial_pct: number; amostras: number }
  asrank?: { rank?: number; cone?: { asns?: number; prefixos?: number; enderecos?: number }; grau?: { total?: number; cliente?: number; par?: number; provedor?: number } }
  prefixos_em_bogon?: Array<{ prefixo: string; lista: 'iana' | 'cymru' }>
  n_prefixos_bogon?: number
  asn_reservado?: string
}
/** Campos do recorte agregado (D6): quantos casos, parcela do maior integrante (0 a 1) e os avisos (`poucos_casos`, `maior_integrante`). Ausentes em snapshots anteriores. */
export interface RecorteAgregado { n_asns_com_dado?: number; peso_top1?: number | null; avisos?: string[] }
export interface AgregadoSinal extends RecorteAgregado {
  asns: number
  mediana_pct?: number
  media_ponderada_pct?: number
  faixas?: { ate_10: number; de_10_a_90: number; acima_de_90: number }
}
export interface AgregadoSeguranca {
  asns: number
  rov: AgregadoSinal
  dnssec: AgregadoSinal
  asns_com_prefixo_bogon: number
}
export interface SegurancaResumo {
  snapshot_date: string
  fontes: SegurancaFontes
  parametros: { min_amostras: number }
  limites: string
  escopo: { uf?: string; pais?: string }
  agregado: AgregadoSeguranca
  por_uf?: Record<string, AgregadoSeguranca>
  por_faixa_porte?: Record<string, AgregadoSeguranca>
}

/** Route servers do IX.br: sessões BGP dos membros vistas no Alice-LG, cruzadas com o cadastro. Fato medido no route server na data da coleta; sem causa nem veredito. */
export interface RouteServersMeta {
  snapshot_date: string
  coletado_em: string | null
  fonte: string | null
  versao_alice: string | null
  parametros: { dias_down: number; uso_limite: number; idade_max_vizinhos_h: number }
  limites: string
}
export interface RsSessao {
  rs: string; afi: 'v4' | 'v6'; ip: string; estado: 'up' | 'down'; dias: number | null; erro?: string; rs_incerto?: boolean
  recebidas: number | null; aceitas: number | null; filtradas: number | null; limite: number | null; uso_limite: number | null
}
export interface RsResumoMembro {
  sessoes: number; up: number; down: number; down_certo: number; max_dias_down?: number; max_uso_limite?: number; rs_incerto?: number
  todas_down: boolean; membro_down: boolean; perto_do_limite: boolean
}
export interface RsMembro extends RsResumoMembro { asn: number; nome: string | null; cadastrado: boolean; cadastrado_sem_sessao?: boolean }
export interface RsServidor { rs: string; numero: string; afi: 'v4' | 'v6'; estado_rotas: string | null; rotas_atualizadas_em: string | null; vizinhos_em: string | null; vizinhos_incerto: boolean; rotas_importadas: number | null; consultado: boolean; erro: string | null; sessoes: number; sessoes_up: number }
export interface RouteServersIxp extends RouteServersMeta {
  nome: string
  rs: RsServidor[]
  resumo: { rs: number; rs_consultados: number; rs_rotas_prontas: number; rs_vizinhos_atuais: number; cadastrados: number; cadastrados_com_sessao: number; cadastrados_sem_sessao: number; sessao_sem_cadastro: number
    sessoes: number; sessoes_up: number; sessoes_down: number; membros_down: number; membros_com_rs_incerto: number; membros_perto_do_limite: number }
  /** `destaque`: só os membros com algo a dizer (membro, perto do limite, cadastrado sem sessão, sessão sem cadastro); `membros_total` é o PTT inteiro. */
  membros_listados: 'destaque' | 'todos'
  membros_total: number
  membros: RsMembro[]
}
export interface RouteServersAsn extends RouteServersMeta {
  ixps: Record<string, RsResumoMembro & { cadastrado: boolean; lista: RsSessao[] }>
  total: { ixps: number; sessoes: number; up: number; down: number; ixps_down: number; ixps_perto_do_limite: number }
}
/** Tabela única de participantes de um PTT (`GET /ixps/{code}/participantes`, PT-24). `null` em `direto` e `originador` = família sem coleta válida ou ASN fora do Brasil (só ele): nunca "não tem". */
export interface ParticipantePtt {
  asn: number; nome: string | null; uf: string | null; is_br: boolean | null
  /** No cadastro de participantes do IX.br. Diferente de ter sessão com o route server. */
  membro: boolean
  direto: { v6: boolean | null; v4: boolean | null }
  originador: { v6: boolean | null; v4: boolean | null }
  sessao_rs: { sessoes: number; up: number; down: number; incertas: number } | null
  cadastrado_sem_sessao_rs: boolean
  sessao_rs_sem_cadastro: boolean
  rejeicao: { filtradas: number; recebidas: number; pct: number | null; sessoes_up: number } | null
  rejeicao_detalhe: { rotas: number; coletado_ate: string | null; idade_dias: number | null; herdado: boolean; contagem: string | null } | null
  cdns: string[]
  /** Acessos de banda larga fixa que o CNPJ do ASN declarou ao SICI (Anatel) no mês de referência; `null` sem vínculo ASN→CNPJ ou sem declaração. */
  sici: { acessos: number; compartilhado: boolean } | null
  /** Nome comercial do CNPJ vinculado ao ASN (Anatel). `nome` nulo sem nome nas fontes: o CNPJ nunca faz as vezes de nome. */
  empresa: { cnpj: string; nome: string | null } | null
  /** Política de peering que a própria rede declarou no PeeringDB (`policy_general`); sem verificação. */
  politica_peering: string | null
  /** Usuários estimados pela APNIC para o ASN inteiro; só ASN brasileiro. */
  usuarios_apnic: number | null
  /** ESTIMADO: usuários do ASN via os prefixos IPv4 vistos no PTT (APNIC × parte do espaço IPv4 do AS que aparece no PTT). Não arredondado. */
  usuarios_ptt: number | null
  /** Prefixos próprios e de terceiros vistos no PTT, por família (os mesmos de `/ixps/{code}/peers`); `null` se o ASN não tem sessão direta na família. */
  prefixos: { v6: PrefixosPeer | null; v4: PrefixosPeer | null }
  /** Portas declaradas e instalações inferidas, do PeeringDB. */
  peeringdb: { portas_mbps: number[] | null; instalacoes: { id: number; nome: string | null }[] | null } | null
  /** Assinantes SICI dos CNPJs nos AS-paths anunciados pelo ASN no PTT, por família. */
  sici_alcancado: { v6: number | null; v4: number | null }
}
export interface PrefixosPeer { total_prefixes: number; own_prefixes: number; third_prefixes: number; origin_asns: number; own_space_24: number; third_space_24: number }
export type FiltroParticipantes = 'todos' | 'sem-v6' | 'sem-v4' | 'sem-direto' | 'membro-sem-sessao-rs' | 'sessao-sem-cadastro' | 'com-cdn' | 'com-rejeicao'
export interface ParticipantesPtt {
  snapshot_date: string; ixp: string; limites: string
  filtros: { q: string | null; uf: string | null; filtro: FiltroParticipantes; definicao_do_filtro: string }
  ordem: string; page: number; limit: number; route_servers_medido: boolean
  /** "Como ler" das duas colunas de usuários. */
  limites_usuarios: string
  /** Fecha a conta da coluna `usuarios_ptt` com o total do PTT; `null` sem coleta IPv4 válida. */
  usuarios_ptt_resumo: { na_tabela: number; fora_da_tabela: { asns: number; usuarios: number }; total_do_ptt: number } | null
  fontes: {
    cadastro: { fonte: string; snapshot: string }
    looking_glass: { fonte: string; snapshot: string; coleta: { v6: string; v4: string } }
    route_servers: { fonte: string | null; coletado_em: string | null; versao_alice: string | null; rs_consultados: number | null; rs_total: number | null }
    rejeicoes_por_motivo: { fonte: string | null; coletado_nivel2: string | null; cobertura: Record<string, number | null> | null }
    cdns: { fonte: string; snapshot: string }
    sici: { fonte: string; mes_referencia: string | null; snapshot: string }
    apnic: { fonte: string; snapshot: string; limites: string }
    peeringdb: { fonte: string; snapshot: string; coletado_em: string | null; limites: string | null }
    prefixos: { fonte: string; snapshot: string }
  }
  total: number; total_participantes: number; contagens: Record<FiltroParticipantes, number>; ufs: string[]
  items: ParticipantePtt[]
}
export interface RankingRouteServersItem {
  posicao: number; ixp: string; asn: number; nome: string | null; sessoes: number; up: number; down: number; down_certo: number
  max_dias_down: number | null; max_uso_limite: number | null; membro_down: boolean; rs_incerto: number
}
export interface RankingRouteServers extends RouteServersMeta {
  criterio: string; escopo: { ixp?: string; pais?: string }; filtros: { apenas_down: boolean }; total: number; items: RankingRouteServersItem[]
}

/** Rejeições, communities e política nos route servers do IX.br (Alice-LG níveis 2 e 3). Declaração do membro e decisão do route server; o perfil é INFERIDO e só existe para quem foi coletado. */
export interface RsPolMeta {
  snapshot_date: string
  coletado_nivel2: string | null
  coletado_nivel3: string | null
  /** Cobertura do rodízio somada nos PTTs, por nível (2 = rejeições, 3 = communities das rotas recebidas). Ausente em snapshot anterior ao PT-16. */
  cobertura_total_nivel2?: RsPolCobertura | null
  cobertura_total_nivel3?: RsPolCobertura | null
  rs_pulados?: { rs: string; motivo?: string }[] | null
  fonte: string | null
  versao_alice: string | null
  parametros: { amostra_prefixos: number; min_rotas_perfil: number; fracao_seletivo: number; fracao_restritivo: number; alvos_restritivo: number }
  limites: string
}
/** `coletados` e `herdados` são os campos de sempre; os demais vêm do rodízio do coletor (só sobre os vizinhos elegíveis) e faltam em coleta antiga. */
export interface RsPolCobertura {
  elegiveis: number; coletados: number; herdados: number
  lidos_na_rodada?: number; sem_leitura?: number; pulados_lentos?: number
  /** Idade da leitura mais antiga em dias; nulo sem leitura nenhuma. */
  idade_max_dias?: number | null
}
export interface RsPolMotivo { codigo: string; rotulo: string | null; classe: string; rotas: number; amostra: { p: string | null; o: number | null }[] }
export interface RsPolRejeicoesAsn {
  rotas: number; sessoes: number; afis: string[]; motivos: RsPolMotivo[]; sem_motivo: number; coletado_de: string | null; coletado_ate: string | null; contagem: 'exata' | 'amostra'; herdado?: boolean
}
export interface RsPolAlvo { alvo: number | null; rotulo: string; rotas: number; fracao: number | null; forma: 'dicionario' | 'equivalente_padrao' }
export interface RsPolAcao { alvos: RsPolAlvo[]; alvos_total: number; rotas_max: number; fracao_max: number | null }
export interface RsPolPolitica {
  rotas: number; sessoes: number; afis: string[]; perfil: 'aberto' | 'seletivo' | 'restritivo' | null; perfil_criterio: string; perfil_inferido: true
  acoes: Record<string, RsPolAcao>; blackhole_rotas: number; rpki: { valid: number; unknown: number; not_checked: number; invalid: number }; communities_distintas: number
  coletado_de: string | null; coletado_ate: string | null; contagem: 'exata' | 'amostra'; herdado?: boolean
}
export interface PoliticaAsn extends RsPolMeta {
  asn: number
  nome?: string
  /** Rotas rejeitadas pelo route server por tipo, somadas nos PTTs coletados: evidência do route server, não veredito sobre o ASN. */
  evidencia_rs?: Record<string, number> | null
  ixps: Record<string, { rejeicoes?: RsPolRejeicoesAsn; politica?: RsPolPolitica }>
}
export interface RsPolRejeicoesIxp {
  cobertura: RsPolCobertura; asns_com_rejeicao: number; rotas_rejeitadas: number; rotas_com_motivo_decodificado: number
  /** Soma das rotas por motivo; passa de `rotas_rejeitadas` quando uma rota tem mais de um motivo. */
  soma_dos_motivos: number
  por_motivo: { codigo: string; rotulo: string | null; classe: string; rotas: number; asns: number }[]
  asns_total: number; asns: { asn: number; nome?: string; rotas: number; motivos: Record<string, number> }[]
}
export interface RsPolPoliticaIxp {
  cobertura: RsPolCobertura; asns_com_dado: number; perfis: Record<string, number>; acoes: Record<string, { asns: number }>; blackhole: { asns: number; rotas: number }
  rpki: { valid: number; unknown: number; not_checked: number; invalid: number }
}
export interface RejeicoesIxp extends RsPolMeta { ixp: string; nome: string; rejeicoes: RsPolRejeicoesIxp | null; politica: RsPolPoliticaIxp | null }
export interface CommunityUso { asns: number; rotas: number; top: { asn: number; nome?: string; rotas: number }[] }
export interface CommunityItem {
  community: string; classe: string; rotulo: string | null; forma: 'dicionario' | 'equivalente_padrao' | 'nao_decodificada'; alvo?: number
  /** ASNs distintos que usam a community (um membro em vários PTTs conta uma vez). */
  asns_total: number
  /** Soma por PTT do número de membros (a contagem exibida até 2026-11). */
  asns_soma_ptts?: number
  /** PTTs onde a community aparece. */
  ptts?: number
  /** Rotas, soma por PTT: a mesma rota anunciada em dois PTTs conta duas vezes. */
  rotas_total: number; ixps: Record<string, CommunityUso>
}
export interface CommunitiesResp extends RsPolMeta { filtros: { q: string | null; ixp: string | null; classe: string | null }; total: number; por_classe: Record<string, number>; items: CommunityItem[] }

// Pesquisas TIC do Cetic.br: tabelas oficiais em formato longo
export interface CeticMeta { pesquisa: string; edicao: number; fonte: string; licenca: string; pagina: string; coletado_em: string | null; snapshot_date: string; aviso: string }
export interface CeticTabela { tabela: string; codigo: string; titulo: string; universo: string; notas: string[] }
export interface CeticTabelas extends CeticMeta { total: number; items: CeticTabela[] }
export interface CeticLinha {
  tabela: string; titulo_tabela: string; dimensao: string; recorte: string; item: string; resposta: string
  proporcao: number | null; margem_proporcao: number | null; total: number | null; margem_total: number | null
}
export interface CeticIndicadores extends CeticMeta { filtros: Record<string, string | null>; total: number; items: CeticLinha[] }

// TIC Domicílios por UF: estimativas do Arandurapé sobre os microdados do Cetic.br
export interface CeticEstimativa {
  proporcao?: number; erro_padrao?: number; margem?: number; cv?: number | null; total?: number; total_erro_padrao?: number; precisao?: 'adequada' | 'baixa'; suprimido?: string
}
export interface CeticGrupo { tipo: 'brasil' | 'regiao' | 'uf'; nome: string; n: number; domicilios: number; indicadores: Record<string, CeticEstimativa> }
export interface CeticMetaUf {
  natureza: string; pesquisa: string; edicao: number; fonte: string; licenca: string; pagina: string; coletado_em: string | null; snapshot_date: string; aviso: string
  metodo: { replicas: number; supressao_n_minimo: number; precisao_baixa_cv: number }
  validacao: { comparados: number; diferenca_max_proporcao_pp: number; razao_margem_oficial_min: number | null; razao_margem_oficial_max: number | null } | null
  indicadores: Record<string, { rotulo: string; definicao: string }>
}
export interface CeticEstimativasUf extends CeticMetaUf { uf: string; regiao: string | null; estimativas: CeticGrupo; comparacao: { regiao: CeticGrupo | null; brasil: CeticGrupo | null } }
export interface CeticEstimativas extends CeticMetaUf { total: number; items: Array<{ grupo: string; tipo: string; n: number; domicilios: number; indicadores: Record<string, CeticEstimativa> }> }

// Demanda × oferta de banda larga fixa: estimativa do Arandurapé (TIC Domicílios × IBGE × SICI), com intervalo de 95%
export type DemandaOfertaClasse = 'oferta_abaixo_da_demanda' | 'compativel' | 'oferta_acima_da_demanda' | 'indeterminado'
export interface DemandaOfertaLinha {
  classe: DemandaOfertaClasse; motivo?: string; domicilios_projetados: number; oferta_acessos_pf: number
  proporcao_bl_fixa?: number; proporcao_margem?: number; demanda_domicilios?: number; demanda_margem?: number
  razao?: number | null; razao_min?: number; razao_max?: number; nao_visto?: number; nao_visto_min?: number; nao_visto_max?: number
}
export interface DemandaOfertaMeta {
  natureza: string; fonte: string; tic_edicao: number; mes_referencia_sici: string | null; pnad_ano: string | null; intervalo: string; limites: string; snapshot_date: string
}
export interface DemandaOferta extends DemandaOfertaMeta { brasil: DemandaOfertaLinha; regioes: Record<string, DemandaOfertaLinha>; ufs: Record<string, DemandaOfertaLinha> }
export interface DemandaOfertaUf extends DemandaOfertaMeta {
  uf: string; regiao: string | null; demanda_oferta: DemandaOfertaLinha; comparacao: { regiao: DemandaOfertaLinha | null; brasil: DemandaOfertaLinha }
}

// Estações do SMP licenciadas: cadastro de licenciamento da Anatel, não cobertura
export type Geracao = '2G' | '3G' | '4G' | '5G'
export type ErbsGeracoes = Record<Geracao, number>
export interface ErbsMeta { natureza: string; fonte: string; data_arquivo: string | null; limites: string; snapshot_date: string }
export interface ErbsBrasil { estacoes: number; municipios: number; municipios_com_estacao: number; municipios_com_5g: number; geracoes: ErbsGeracoes; operadoras: number }
export interface ErbsUfResumo { estacoes: number; municipios: number; municipios_com_estacao: number; municipios_com_5g: number; geracoes: ErbsGeracoes; operadoras: number }
export interface ErbsUf extends ErbsMeta { uf: string; resumo: ErbsUfResumo; brasil: ErbsBrasil }
export interface ErbsMunicipio extends ErbsMeta {
  estacoes: number; geracoes: ErbsGeracoes; por_10mil_hab: number | null; operadoras: Array<{ cnpj: string | null; marca: string; estacoes: number }>
  uf: string | null; comparacao_uf: ErbsUfResumo | null; brasil: ErbsBrasil
}
export interface ErbsOperadora extends ErbsMeta {
  cnpj: string | null; marca: string; entidade: string; estacoes: number; municipios: number; ufs: number; geracoes: ErbsGeracoes; tipo_5g: Record<string, number>
  brasil: { estacoes: number; municipios_com_estacao: number }
}
export interface ErbsMunicipioLinha {
  ibge: string; nome: string | null; uf: string | null; estacoes: number; estacoes_2g: number; estacoes_3g: number; estacoes_4g: number; estacoes_5g: number
  por_10mil_hab: number | null; operadoras: number; operadora_principal: string | null
}
export interface ErbsMunicipios extends ErbsMeta { geracao: Geracao | null; uf: string | null; ordem: string; total: number; limit: number; offset: number; items: ErbsMunicipioLinha[] }

// Mercado de IPv4: o que as listas do Registro.br e do LACNIC declaram e o que o delegated mostra; diferenças observadas, sem causa nem intenção
export type Ipv4Direcao = 'br_br' | 'br_exterior' | 'exterior_br'
export interface Ipv4Meta { natureza: string; fonte: string; limites: string; snapshot_date: string }
export interface Ipv4Parte { nome: string | null; pais: string | null; rir: string | null; pessoa: string | null }
export interface Ipv4Operacao {
  id: string; data: string; origem: Ipv4Parte; destino: Ipv4Parte; blocos: string[]; n_blocos: number; enderecos: number; tamanho: string; direcao: Ipv4Direcao; fontes: string[]
  primeira_vez_visto: string | null; anterior_a_coleta: boolean; defasagem_dias: number | null; casamento?: { asn: number; org: string | null }
}
export interface Ipv4Transferencias extends Ipv4Meta { filtros: Record<string, string | number | null>; total: number; limit: number; offset: number; items: Ipv4Operacao[] }
export interface Ipv4PorDirecao { operacoes: number; enderecos: number }
export interface Ipv4Mercado extends Ipv4Meta {
  periodo: [string | null, string | null]; operacoes: number; blocos: number; enderecos: number
  por_ano: Record<string, { operacoes: number; blocos: number; enderecos: number; por_direcao: Partial<Record<Ipv4Direcao, Ipv4PorDirecao>> }>
  por_tamanho: Record<string, number>
  concentracao: { top_destinos: Array<{ nome: string; enderecos: number; pct: number }>; top_origens: Array<{ nome: string; enderecos: number; pct: number }> }
  maior_operacao: { data: string; blocos: number; enderecos: number } | null
  defasagem: { operacoes_com_medida: number; mediana_dias: number | null; maximo_dias: number | null }
  casamento: { destino_br: number; com_asn: number; pct: number | null }
}
export interface Ipv4RecursoRecuperacao { tipo: string; recurso: string; inicio: string; fim: string; primeira_vez_visto: string | null; status_delegated: string | null }
export interface Ipv4Recuperacao extends Ipv4Meta {
  em_recuperacao: { total: number; por_tipo: Record<string, number>; janelas: Array<[string, string]>; itens: Ipv4RecursoRecuperacao[] }
  recuperados: { total: number; por_tipo: Record<string, number> }
  eventos_por_mes: Record<string, Partial<Record<'recuperacao' | 'liberacao', number>>>
}
export interface Ipv4CicloDeVida extends Ipv4Meta {
  bloco: string; aviso: string
  espaco?: Ipv4EspacoLinha[]; sinais_de_terceiros?: Ipv4UsoItem[]
  atual: Array<{ inicio: string; quantidade: number; status: string; data_registro: string | null; opaque_id: string | null; asn: number | null; organizacao: string | null }>
  linha_do_tempo: Array<{ data: string; fonte: string; tipo: string; detalhe: Record<string, unknown> }>
}

// Espaço IPv4 não plenamente anunciado e hipóteses de uso por terceiros: inferido; não anunciado não é sem uso; sinal é hipótese, nunca aluguel
export type Ipv4Classe = 'nao_anunciado' | 'roa_sem_anuncio' | 'parcial' | 'em_recuperacao'
export interface Ipv4EspacoLinha {
  inicio: string; quantidade: number; classe: Ipv4Classe; anunciado_pct: number; asn: number | null; org: string | null; cnpj: string | null; uf: string | null
  tabelas_sem_anuncio: number | null; sem_anuncio_desde: string | null; ano_registro: string | null; roa_asns: number[]
}
export interface Ipv4Espaco extends Ipv4Meta {
  ultima_foto: string | null; total: number; limit: number; offset: number; items: Ipv4EspacoLinha[]
  resumo: { total_blocos: number; total_enderecos: number; por_classe: Record<string, { blocos: number; enderecos: number }>; por_uf: Record<string, { blocos: number; enderecos: number; nao_anunciado: number }>
    maiores_titulares_nao_anunciado: Array<{ asn: number; org: string; enderecos: number }> }
  duracao: { tabelas_anteriores_consultadas: string[]; maximo_de_tabelas: number }
}
export interface Ipv4SinalDef { nome: string; avaliado: boolean; falsos_positivos?: string; motivo?: string }
export interface Ipv4UsoItem {
  inicio: string; quantidade: number; classe: string; anunciado_pct: number; origens: number[]; roa_asns: number[]; confianca: 'baixa' | 'media' | 'alta'
  titular: { asn: number; org: string | null; cnpj: string | null } | null; sinais: Array<{ id: string; confianca: string; evidencia: string }>
}
export interface Ipv4Uso extends Ipv4Meta {
  rotulo: string; sinais: Record<string, Ipv4SinalDef>; por_sinal: Record<string, number>; por_confianca: Record<string, number>; blocos_avaliados: number
  total: number; limit: number; offset: number; items: Ipv4UsoItem[]
}
export interface Ipv4RecursosAsn extends Ipv4Meta {
  asn: number; blocos: number; enderecos: number; nao_plenamente_anunciados: Ipv4EspacoLinha[]; sinais_como_titular: Ipv4UsoItem[]; sinais_como_origem: Ipv4UsoItem[]; aviso: string
}

// Sub-asignações de IPv4: aguardando a bitácora oficial da LAC-2025-5; esquema hipotético
export interface Ipv4Subasignacao {
  id: string; bloco: string; receptor_asn: number; cedente_asn: number | null; inicio: string; fim: string | null; rir: string | null
  validacoes: Record<string, boolean | null>; em_conformidade: boolean; pendentes: string[]
}
export interface Ipv4Subasignacoes extends Ipv4Meta {
  ativa: boolean; aguardando: boolean; aviso: string | null; esquema_hipotetico: boolean; politica: { nome: string; estado: string; fonte_oficial: string }; validacoes: Record<string, string>
  vigia: { ultima_varredura: string | null; alertas_30_dias: Array<{ data: string; tipo: string; url?: string; nome?: string; padrao?: string }> }
  indicador_terceiros: { com_registro: number | null; sem_registro: number | null; nota: string }; eventos: Array<{ tipo: string; data: string; bloco: string; receptor_asn: number }>
  total: number; limit: number; offset: number; items: Ipv4Subasignacao[]
}

// ── FUST ─────────────────────────────────────────────────────────
export interface FustMeta { natureza: string; fonte: string; data_arquivo: string | null; limites: string; snapshot_date: string }
export interface FustTotais { compromissos: number; atendidos: number; a_vencer: number; em_apuracao: number; investimento: number }
export interface FustBrasil extends FustTotais { municipios: number; municipios_com_compromisso: number; programas: number; editais: number }
export interface FustUfResumo extends FustTotais { municipios: number; municipios_com_compromisso: number; programas: Record<string, number> }
export interface FustMunicipio extends FustMeta, FustTotais {
  programas: Record<string, number>; tipos: Record<string, number>; por_10mil_hab?: number; uf: string | null; comparacao_uf: FustUfResumo | null; programas_nomes: Record<string, string>
}
export interface FustUf extends FustMeta { uf: string; resumo: FustUfResumo; brasil: FustBrasil; programas_nomes: Record<string, string> }
export interface FustMunicipioLinha extends FustTotais { ibge: string; nome: string | null; uf: string | null; por_10mil_hab: number | null; programas: string[] }
export interface FustMunicipios extends FustMeta { uf: string | null; programa: string | null; ordem: string; total: number; limit: number; offset: number; items: FustMunicipioLinha[] }

// ── Multas, espectro e satélites ──────────────────────────────────
export interface RegMeta { natureza: string; fonte: string; data_arquivo: string | null; limites: string; snapshot_date: string }
export type GrupoServico = 'SCM' | 'SMP' | 'STFC' | 'SeAC'
export interface MultasTotais { empresas: number; multas: number; original: number; pago: number; saldo: number; situacoes: Record<string, number> }
export interface MultasResumo extends RegMeta {
  /** Raízes de CNPJ distintas; `brasil.empresas` conta raiz × serviço. Ausente em respostas antigas. */
  raizes?: number
  leitura: { linhas: number; pessoa_fisica: number; fora_do_escopo: number; sem_servico: number; empresas: number; multas: number }
  brasil: MultasTotais; por_grupo: Record<GrupoServico, MultasTotais>; por_ano: Array<{ ano: number; total: number } & Record<GrupoServico, number>>
}
export interface MultaEmpresa {
  raiz: string; cnpj_matriz: string | null; entidade: string; grupo: GrupoServico; uf: string | null; multas: number; original: number; pago: number; saldo: number
  situacoes: Record<string, number>; primeiro_ano: string | null; ultimo_ano: string | null
}
/** Linha da lista de multas: por raiz e serviço (`grupo`) ou, com `visao=raiz`, por raiz com `servicos` somados e os outros nomes em `nomes_alternativos`. */
export type MultaLinha = Omit<MultaEmpresa, 'grupo'> & { grupo?: GrupoServico; servicos?: GrupoServico[]; nomes_alternativos?: string[] }
export interface MultasEmpresas extends RegMeta { visao?: 'servico' | 'raiz'; grupo: string | null; ordem: string; regra_ordem?: string; aviso?: string; total: number; limit: number; offset: number; items: MultaLinha[] }
export interface MultasOperadora extends RegMeta {
  raiz: string; multas: number; original: number; pago: number; saldo: number; por_grupo: MultaEmpresa[]; brasil: { empresas: number; multas: number; saldo: number }
}
export interface ServicoFaixa { servico: string; carater: 'Primário' | 'Secundário' | string }
export interface FaixaReferencia { nome: string; ini_mhz: number; fim_mhz: number; faixas: number; destinacao: ServicoFaixa[] }
export interface Faixa { ini_mhz: number; fim_mhz: number; destinacao: ServicoFaixa[]; atribuicao: ServicoFaixa[] }
export interface EspectroResumo extends RegMeta { resumo: { faixas: number; com_destinacao: number; com_atribuicao: number; de_interesse: number }; referencias: FaixaReferencia[] }
export interface EspectroFaixas extends RegMeta {
  de: number | null; ate: number | null; servico: string | null; carater: string | null; total: number; limit: number; offset: number; items: Faixa[]; referencias: FaixaReferencia[] | null
}
export interface SatelitesResumo extends RegMeta {
  resumo: { direitos: number; operadoras: number; satelites: number; por_tipo: Record<string, number>; por_status: Record<string, number>; vencidos_na_data: number; ngeo: number; ngeo_sistemas?: number; operando: number; ngeo_por_orbita: Record<string, number> }
  /** Registros como a Anatel publica: um por sistema e ano de agenda (`agenda_ano`, quando o arquivo traz). */
  ngeo: Array<NgeoRegistro & { agenda_ano?: number | null; nu_estacao?: string }>
  /** Um por sistema (REGULATORIO-E1): campos do registro mais recente e a faixa de satélites declarada nos registros. */
  ngeo_sistemas: Array<NgeoRegistro & { registros: number; anos_agenda: number[]; constelacao_min: number | null; constelacao_max: number | null }>
  operando: Array<{ satelite: string; posicao: string; bandas: string; tipo: string; operadora: string }>
}
interface NgeoRegistro { cnpj: string | null; prestadora: string; lancamento: string | null; estacao: string; objeto: string; status: string; orbita: string; planos: number | null; constelacao: number | null }
export interface SateliteDireito {
  operadora: string; satelite: string; codigo: string; posicao: string; banda: string; tipo: string; status: string; lancamento: string | null; validade: string | null; prorrogado: boolean; vencido: boolean
}
export interface SatelitesDireitos extends RegMeta { operadora: string | null; tipo: string | null; status: string | null; total: number; limit: number; offset: number; items: SateliteDireito[] }
export interface FustPrograma extends FustTotais { codigo: string; nome: string; municipios: number }
export interface FustEdital extends FustTotais { origem: string; municipios: number }
export interface FustResumo extends FustMeta {
  brasil: FustBrasil; ufs: Record<string, FustUfResumo>; programas: FustPrograma[]; editais: FustEdital[]
  casamento: { compromissos: number; com_municipio_no_ibge: number; sem_municipio_no_ibge: number; base_2010: number; base_2022: number; sem_investimento: number }
}

// ── Prontidão em segurança de roteamento ──────────────────────────
export type ClassePronto = 'pronto' | 'em_progresso' | 'atrasado' | 'sem_dados'
export type PilarId = 'filtragem' | 'anti_spoofing' | 'coordenacao' | 'validacao_global'
export interface ProntidaoComponenteRegra { peso: number; descricao: string }
export interface ProntidaoRegras {
  versao: number; hash: string; minimos: { amostras_rov: number; pilares: number }; classes: { pronto: number; em_progresso: number }
  pilares: Record<PilarId, { nome: string; peso: number; descricao: string; requer?: string[]; componentes: Record<string, ProntidaoComponenteRegra> }>
}
export interface ProntidaoMeta {
  snapshot_date: string; natureza: string; limites: string; regras: ProntidaoRegras
  fontes: { spoofer: { fonte: string; citacao?: string | null; janela?: { inicio: string; fim: string; dias: number } | null }; irr: { fonte: string; citacao?: string | null; serial: Record<string, string | null> }; seguranca: { fonte: string; snapshot?: string | null } }
}
export interface ProntidaoComponente { valor: number; peso: number; detalhe: Record<string, unknown> | null }
export interface ProntidaoPilar { score: number; peso: number; componentes: Record<string, ProntidaoComponente> }
export interface ManrsCelula extends RecorteAgregado {
  asns: number; usuarios: number; /** só em snapshots anteriores à regra sem supressão */ suprimido?: boolean; motivo?: string
  asns_participantes?: number; pct_asns?: number | null; usuarios_participantes?: number; pct_usuarios?: number | null
  comparacao_prontidao?: { participantes: ManrsPronto; nao_participantes: ManrsPronto } | null
  organizacoes_com_asn_br?: number
}
export interface ManrsPronto extends RecorteAgregado { asns_com_indice: number; media_ponderada_usuarios: number | null; mediana: number | null; classes: Record<ClassePronto, number> }
export interface ManrsResumo {
  snapshot_date: string; natureza: string; atribuicao: string; limites: string
  fonte: { descricao: string; url: string; medido_em: string | null; coletado_em: string; termos: string }
  regras: { minimo_asns_por_recorte: number; peso_aviso?: number; recortes_suprimidos?: boolean; comparacao: string }
  brasil: ManrsCelula; por_faixa_porte: Record<string, ManrsCelula>; por_uf: Record<string, ManrsCelula>
}
export interface ProntidaoAgregado extends RecorteAgregado {
  /** Classes separadas por haver ROV medido no pilar Filtragem (a soma das duas é `classes`); ausentes em snapshots anteriores. */
  classes_com_rov?: Record<ClassePronto, number>; classes_sem_rov?: Record<ClassePronto, number>
  asns: number; asns_com_indice: number; classes: Record<ClassePronto, number>; media_ponderada_usuarios: number | null; mediana: number | null; usuarios: number
  cobertura_pilares: Record<PilarId, number>
  /** Por componente (rov, sem_bogon, spoofer, peeringdb, irr_aut_num, irr_as_set, roa, irr, aspa): ASNs com dado e a média (0–100) simples e ponderada pelos usuários. */
  medicoes?: Record<string, RecorteAgregado & { pilar: PilarId; asns: number; media: number | null; media_ponderada_usuarios: number | null }>
}
export interface ProntidaoAsn extends ProntidaoMeta {
  total: number | null; classe: ClassePronto; pilares: Partial<Record<PilarId, ProntidaoPilar>>; pilares_sem_dado: PilarId[]; usuarios: number
  faixa_porte?: string | null; faixa_acessos_sici?: string | null
  comparacao_uf: ProntidaoAgregado | null; brasil: ProntidaoAgregado
}
export interface ProntidaoUf extends ProntidaoMeta { uf: string; agregado: ProntidaoAgregado; brasil: ProntidaoAgregado }
export interface ProntidaoOperadora extends ProntidaoMeta { raiz: string; agregado: ProntidaoAgregado; brasil: ProntidaoAgregado }
export interface ProntidaoResumo extends ProntidaoMeta {
  /** A lista por ASN está publicada nesta instância (`lista_nominal_habilitada()` da API). */
  lista_nominal?: boolean
  escopo: { uf?: string; pais?: string }; agregado: ProntidaoAgregado; por_uf?: Record<string, ProntidaoAgregado>; por_faixa_porte?: Record<string, ProntidaoAgregado>; brasil?: ProntidaoAgregado
  /** Participação agregada no MANRS; nulo se não publicada. */
  manrs?: ManrsResumo | null
}

// ── Região: ASNs de um conjunto de municípios, PTTs, trânsito e carregadores ─────────────────
export type RegiaoVinculo = 'sici' | 'sede' | 'geo'
export interface RegiaoPtt { codigo: string; direto: number; indireto: number; total: number; pct_direto: number | null; pct_total: number | null }
export interface RegiaoTransito {
  asn: number; nome: string; asns: number; pct: number | null; niveis: { confirmado: number; provavel: number; possivel: number }; na_regiao: boolean; ptts_diretos: string[]
}
export interface RegiaoCarregador { asn: number; nome: string; asns: number; pct: number | null; na_regiao: boolean; ptts_diretos: string[] }
export interface RegiaoProvedor {
  asn: number; nome: string; vinculos: RegiaoVinculo[]; acessos_fixo: number; acessos_movel: number; prefixos_geo: number; ptts_diretos: string[]; ptts_indiretos: string[]
}
export interface Regiao {
  snapshot_date: string; natureza: string; limites: string; fontes: Record<string, string | null>
  ibges: string[]; municipios_com_dados: number; ptts_nomes: Record<string, string>
  asns: { total: number; por_vinculo: Record<RegiaoVinculo, number> }
  participacao_ptts: { com_ptt_direto: number; so_indireto: number; sem_ptt: number; pct_direto: number | null; pct_indireto: number | null; pct_sem_ptt: number | null; ptts: RegiaoPtt[] }
  transito: RegiaoTransito[]; transito_total: number
  carregadores: RegiaoCarregador[]; carregadores_total: number; indiretos_sem_carregador: number
  provedores: RegiaoProvedor[]; provedores_total: number
  /** Prontidão dos ASNs da região que têm índice; nulo se o produto não foi publicado. Vale com qualquer número de ASNs: `asns_no_indice` diz quantos sustentam o número. */
  prontidao?: (Pick<ProntidaoMeta, 'regras' | 'limites' | 'fontes'> & { agregado: ProntidaoAgregado | null; asns_no_indice: number; brasil: ProntidaoAgregado }) | null
}

/** Organização por ASN (CAIDA, via AS Rank) e abuso agregado (Feodo Tracker), 1.5.13. A organização é inferida pelo CAIDA a partir do WHOIS; o abuso é contagem de terceiros, sem IPs. */
export interface OrganizacaoAsn {
  snapshot_date: string; coletado_em: string | null; fonte: { nome: string; url?: string | null; citacao?: string | null }; limites: string
  org_id: string; org_nome: string | null; org_pais: string | null; membros_total: number | null; irmaos_br?: number[]
}
export interface AbusoAsn {
  snapshot_date: string; coletado_em: string | null; fonte: { nome: string; url?: string | null; licenca?: string | null }; limites: string
  urlhaus?: { estado: string; motivo?: string } | null
  registrado: boolean; feodo_total_mundo: number | null; feodo_c2: number; feodo_c2_online: number; feodo_malware: Record<string, number>
}

/** Bloqueios e interferência medidos pelo OONI por ASN. Veredito da PRÓPRIA sonda (não do backend do OONI; não é prova de censura); dados CC BY-NC-SA 4.0. */
export interface BloqueioTeste {
  teste: string; rotulo: string; n: number; anomalias: number; pct_anomalia: number | null; criterio: string
  partes?: Record<string, number>; alvos_acessiveis_pct?: Record<string, number | null>; amostra?: boolean; sem_veredito?: number; inacessivel?: number
}
export interface BloqueiosAsn {
  snapshot_date: string; coletado_em: string | null; licenca: string; aviso: string; limites: string; minimo_medicoes: number
  fonte: { nome: string; url?: string | null; atribuicao?: string | null; licenca?: string | null; licenca_url?: string | null }
  janela: { inicio: string | null; fim: string | null; dias_com_dado: number; dias_da_janela: number | null }
  testes: BloqueioTeste[]
}

// ── Cloudflare Radar ─────────────────────────────────────────
export interface RadarBgpPapeis { vazou?: number; no_caminho_de_vazamento?: number; sequestrou?: number; vitima_de_sequestro?: number }
export interface RadarCobertura {
  asns_do_brasil_no_snapshot: number; asns_na_lista_do_radar: number; asns_com_leitura_ipv6: number; asns_com_dado_ipv6: number
  leitura_mais_antiga: string | null; leitura_mais_recente: string | null; asns_no_topo_de_trafego: number; asns_com_velocidade: number
}
interface RadarComum {
  snapshot_date: string; coletado_em: string | null; licenca: string; aviso: string; limites: string; janela_ipv6: string | null; cobertura: RadarCobertura
  fonte: { nome: string; url?: string | null; api?: string | null; atribuicao?: string | null; licenca?: string | null; licenca_url?: string | null }
  bgp_janela: { janela_dias: number | null; em: string | null; vazamentos_com_asn_do_brasil: number | null; sequestros_com_asn_do_brasil: number | null; criterio: string }
  quedas: { janela?: string; anomalias?: number; anotacoes?: number; consultado?: boolean; em?: string }
}
export interface RadarAsn extends RadarComum {
  asn: number
  ipv6?: { pct: number; em: string }
  trafego_pct_do_brasil?: number
  velocidade?: { download_mbps?: number; upload_mbps?: number; latencia_ociosa_ms?: number; latencia_carregada_ms?: number; jitter_ocioso_ms?: number; testes?: number }
  bgp?: RadarBgpPapeis
}
export interface RadarUf extends RadarComum {
  uf: string; asns: number; asns_com_ipv6: number; ipv6_mediana_pct: number | null; ipv6_ponderado_pelo_trafego_pct: number | null; asns_no_ponderado: number; bgp: Required<RadarBgpPapeis>; derivado: true
}

// ── Exposição de serviços (Shodan) ───────────────────────────
export interface ExposicaoCobertura {
  asns_do_brasil_no_snapshot: number; asns_com_leitura: number; asns_com_servicos_observados: number; leitura_mais_antiga: string | null; leitura_mais_recente: string | null
}
interface ExposicaoComum {
  snapshot_date: string; coletado_em: string | null; licenca: string; aviso: string; limites: string; cobertura: ExposicaoCobertura
  fonte: { nome: string; url?: string | null; api?: string | null; atribuicao?: string | null; licenca?: string | null }
  plano?: { facetas: { port: string; vuln: string } } | null
  classes_de_risco?: Record<string, { rotulo: string; portas: Array<{ porta: number; servico: string }> }>
}
export interface ExposicaoServicoDeRisco { porta: number; servico: string; n: number }
export interface ExposicaoAsn extends ExposicaoComum {
  asn: number
  lido_em: string
  servicos_observados: number
  /** O Shodan não viu serviço (zero observado, não ausência de leitura). */
  sem_servico_observado?: boolean
  portas_mais_vistas?: Array<{ porta: number; n: number }>
  risco?: { servicos_de_risco: number; pct_dos_servicos_observados: number; classes: Record<string, { total: number; servicos: ExposicaoServicoDeRisco[] }> }
  vulnerabilidades?: { disponivel: true; cves_mais_vistas: Array<{ cve: string; n: number }> } | { disponivel: false; nota: string }
}
export interface ExposicaoUf extends ExposicaoComum {
  uf: string; asns_do_cadastro: number; asns_com_leitura: number; asns_com_servicos_observados: number; servicos_observados: number; servicos_de_risco: number
  pct_de_servicos_de_risco: number | null; classes: Record<string, number>; servicos_de_risco_por_servico: Record<string, number>; derivado: true
}

// ── Qualidade (RQUAL) e reclamações da Anatel ─────────────────────
export interface QualMeta { natureza: string; fonte: string; data_arquivo: string | null; url_fonte?: string | null; limites: string | null; snapshot_date: string }
export interface QualIndicador { servico: string; codigo: string; descricao: string; tipo: string; grupo: string; unidade: string; referencia_superior: string | null; referencia_inferior: string | null }
export interface QualPrestadora { servico: string; prestadora: string; municipios: number; raizes: string[]; cnpjs_matriz?: string[]; casamento: 'curada' | 'automatico' | null; base_casamento: string | null }
export interface QualEstat { municipios: number; resultados: number; medidas: number | null; media: number; media_ponderada: number | null; mediana?: number }
export interface QualNacional extends QualEstat { servico: string; prestadora: string; indicador: string; mes: string }
export interface QualUfLinha extends QualEstat { uf: string; servico: string; prestadora: string; indicador: string; ano: number }
export interface QualCasamentoRqual { prestadoras: number; com_cnpj: number; pct_resultados_com_cnpj: number | null; sem_cnpj: string[]; tabela_curada: { versao: number; curada_em: string; fonte: string } }
export interface QualidadeResumo extends QualMeta {
  leitura: { linhas: number; resultados_numericos: number; sem_valor: Record<string, number>; municipios: number; municipios_com_resultado: number; mes_inicial: string; mes_final: string; itens_municipais: number }
  indicadores: QualIndicador[]; prestadoras: QualPrestadora[]; casamento: QualCasamentoRqual
  /** CNPJ → nome da empresa (cadeia da página de operadora); CNPJ sem nome fica de fora */
  nomes?: Record<string, string>
}
export interface QualidadePrestadoras extends QualMeta {
  indicador: QualIndicador; uf: string | null; periodo: { mes?: string; ano?: number | null }; ordem: string; total: number
  items: Array<(QualNacional | QualUfLinha) & { raizes_cnpj: string[] }>
}
export interface QualidadeSerie extends QualMeta { indicador: QualIndicador; uf: string | null; granularidade: string; total: number; items: Array<QualNacional | QualUfLinha> }
export interface QualMunicipioItem { indicador: string; mes: string; resultado: number; medidas: number | null; coletores: number | null; erro_amostral: number | null; estatistica: boolean; limite_inferior: number | null; limite_superior: number | null }
export interface QualidadeMunicipio extends QualMeta { ibge: string; nome: string; uf: string; indicadores?: QualIndicador[] | null; prestadoras: Array<{ servico: string; prestadora: string; itens: QualMunicipioItem[] }> }
export interface QualidadeUf extends QualMeta { uf: string; itens: QualUfLinha[]; indicadores: QualIndicador[] }
export interface QualidadeOperadora extends QualMeta { raiz: string; prestadoras: QualPrestadora[]; itens: QualNacional[]; indicadores: QualIndicador[] }

export interface ReclTaxa { marca: string; grupo: 'SCM' | 'SMP'; raizes: string[]; casamento: string; reclamacoes: number; acessos: number | null; por_mil_acessos: number | null; motivo_sem_taxa: string | null }
export interface ReclTaxasMeta { janela: { de: string; ate: string } | null; sici_mes_referencia: { SCM: string | null; SMP: string | null }; regra: string }
export interface ReclCasamento { reclamacoes_total: number; por_metodo: Record<string, number>; pct_com_cnpj: number | null; marcas: number; marcas_com_cnpj: number; tabela_curada: { versao: number; curada_em: string; fonte: string; marcas: number } }
export interface ReclamacoesResumo extends QualMeta {
  leitura: { arquivos: Record<string, { linhas: number; linhas_usadas: number; solicitacoes: number; mes_inicial: string | null; mes_final: string | null; data_extracao?: string | null }>; corte_contexto: string | null; anos: number[]; marcas: number; municipios: number; reclamacoes: number; sem_marca: number }
  casamento: ReclCasamento; taxas: ReclTaxasMeta
  por_ano_servico: Array<{ ano: number; servico: string; reclamacoes: number }>
  assuntos_ano: { ano: number | null; itens: Array<{ servico: string; assunto: string; reclamacoes: number }> }
  uf: Array<{ uf: string; servico: string; ano: number; reclamacoes: number }>
}
export interface ReclamacoesMarca { marca: string; ano: number; reclamacoes: number; por_servico: Record<string, number>; raizes: string[]; cnpjs_matriz: string[]; casamento: 'curada' | 'automatico' | null; taxas: ReclTaxa[] }
export interface ReclamacoesMarcas extends QualMeta { ano: number; servico: string | null; ordem: string; total: number; limit: number; offset: number; items: ReclamacoesMarca[]; nomes?: Record<string, string> }
export interface ReclamacoesMunicipio extends QualMeta {
  ibge: string; nome: string; uf: string; populacao: number | null
  anos: Array<{ ano: number; reclamacoes: number; por_100mil_hab: number | null; por_servico: Record<string, number>; marcas: Array<{ marca: string; servico: string; reclamacoes: number; raizes: string[] }> }>
}
export interface ReclamacoesUf extends QualMeta { uf: string; anos: Array<{ ano: number; reclamacoes: number; por_servico: Record<string, number> }> }
export interface ReclamacoesOperadora extends QualMeta {
  raiz: string; marcas: Array<{ marca: string; casamento: string }>
  anos: Array<{ ano: number; reclamacoes: number; por_servico: Record<string, number> }>
  assuntos_ano: { ano: number; itens: Array<{ servico: string; assunto: string; reclamacoes: number }> }
  taxas: ReclTaxasMeta & { itens: ReclTaxa[] }; aviso: string
}

/** Instalações do PeeringDB: cadastro AUTODECLARADO; `cadastro` é inferência pelas datas de atualização e não diz nada da operação. Sem contatos. */
export interface FacilityMeta {
  snapshot_date: string; coletado_em: string | null; fonte: { nome: string; url?: string | null; citacao?: string | null; aup?: string | null; coletado_em?: string | null }; limites: string
  regra_cadastro?: { versao: number }
}
export interface CadastroInferido { classe: 'recente' | 'parado' | 'antigo' | null; ultima_atualizacao: string | null; dias: number | null; inferido: true; rotulo?: string; registro_atualizado?: string | null; vinculo_atualizado?: string | null }
export interface FacilityResumo {
  id: number; nome: string | null; org_nome?: string; cidade?: string; uf?: string; pais?: string; lat?: number; lon?: number; escopo?: 'brasil' | 'ptt_externo'
  n_redes?: number; redes_declaradas?: number; n_ptts: number; n_carriers: number; campus_id?: number; criado?: string; atualizado?: string; cadastro?: CadastroInferido
  /** PTTs da instalação (PT-24): IX.br primeiro, depois externos, por fim os do PeeringDB que o site não acompanha (sem `code`). */
  ptts_detalhe?: Array<{ ix_id: number; code?: string; tipo?: 'ixbr' | 'externo' | 'outro' }>
}
export interface FacilitiesLista extends FacilityMeta {
  escopo: { pais: string }; ordem: string; total: number; items: FacilityResumo[]
  cobertura?: { instalacoes_br: number; com_ptt: number; com_carrier: number; ptts_ixbr: number; ptts_ixbr_com_instalacao: number; ptts_ixbr_sem_instalacao?: string[]
    /** PT-24, calculados na leitura: nome (cidade) de cada PTT do IX.br do site, os do site que o mapeamento com o PeeringDB não alcança e os códigos do produto que não são PTT do site. */
    ptts_ixbr_nomes?: Record<string, string>; ptts_ixbr_site?: number; ptts_ixbr_sem_mapeamento?: string[]; ptts_ixbr_fora_do_site?: string[]
    ptts_externos: number; ptts_externos_com_instalacao: number; asns_br_no_peeringdb: number; asns_br_com_instalacao: number | null; cadastro_br: Record<string, number> } | null
}
export interface FacilityPtt { ix_id: number; code?: string; nome?: string; tipo: 'ixbr' | 'externo' | 'outro' }
export interface FacilityDetalhe extends FacilityMeta {
  id: number; nome: string | null; aka?: string; nome_longo?: string; org_id?: number; org_nome?: string; campus_id?: number; site?: string; propriedade?: string; cidade?: string; uf?: string; pais?: string; lat?: number; lon?: number
  escopo: 'brasil' | 'ptt_externo'; criado?: string; atualizado?: string; redes_declaradas?: number; ixps_declarados?: number; carriers_declarados?: number; n_redes?: number; n_redes_br?: number
  ixps: FacilityPtt[]; carriers: Array<{ id: number; nome?: string; aka?: string; org_nome?: string; site?: string }>; campus: { id: number; nome?: string; org_nome?: string; cidade?: string; uf?: string; pais?: string; site?: string } | null
  redes: Array<{ asn: number; nome?: string; is_br?: boolean; no_vinculo_desde?: string; vinculo_atualizado?: string
    /** Só com `?include=redes_perfil` e só para rede do Brasil: usuários estimados do APNIC (`null` = sem estimativa), IPv6 e a situação em cada PTT do IX.br do prédio. */
    usuarios_apnic?: number | null; ipv6?: boolean | null; situacao?: Record<string, SituacaoNoPtt> }>
  redes_total: number; redes_nota: string; cadastro?: CadastroInferido
  redes_perfil?: RedesPerfil
}
export type SituacaoNoPtt = 'sessao_rs' | 'membro_sem_sessao_rs' | 'so_origina' | 'sem_presenca' | 'sem_coleta'
/** Resumo por PTT do IX.br do prédio (PT-24 / INST-E5.1). `so_origina` é inferido; PTT externo não tem dado de sessão. */
export interface RedesPerfil {
  resumo: Array<{ ixp: string; nome: string; coleta: Record<string, string>; redes_do_brasil: number } & Record<SituacaoNoPtt, number>>
  ptts_sem_dado_de_sessao: Array<{ ix_id?: number; code?: string | null; nome?: string | null; tipo?: string }>
  situacoes: Record<SituacaoNoPtt, string>
  inferidas: SituacaoNoPtt[]
  nota: string
}
export interface FacilitiesPtt extends FacilityMeta { ptt: string; total: number; items: FacilityResumo[] }
export interface FacilitiesAsn extends FacilityMeta { asn: number; total: number; nota: string; items: Array<FacilityResumo & { no_vinculo_desde?: string; vinculo_atualizado?: string; ptts: string[] }> }
export interface PeeringAsn extends FacilityMeta {
  asn: number; escopo?: string; ipv6?: boolean; multicast?: boolean; unicast?: boolean; nunca_via_route_server?: boolean; looking_glass?: string; route_server?: string
  criado?: string; atualizado?: string; portas_atualizadas?: string; instalacoes_atualizadas?: string; ixps_declarados?: number; instalacoes_declaradas?: number; instalacoes_br_observadas: number; cadastro?: CadastroInferido
  portas_externas?: { limites?: string; ptts: Array<{ ixp: string; portas: number; velocidades_mbps: number[]; capacidade_mbps: number }> }
}
export interface PortasIxp extends FacilityMeta {
  ixp: string; nome?: string; cidade?: string; pais?: string; portas: number; portas_com_velocidade: number; membros: number; capacidade_mbps: number; mediana_mbps: number | null; maior_mbps: number | null; por_velocidade: Record<string, number>
}

/** Trânsito inferido: tudo é inferência do ARC v2 sobre rotas observadas; a UF é a da sede da organização. */
export interface TransitoCab {
  snapshot_date: string; limites: string
  fonte?: { nome: string; coletores_coletados_em?: Record<string, string | null> | null } | null
  cobertura?: { asns_br: number; asns_br_com_provedor: number; asns_com_cone: number; elos_p2c_firmes: number; algoritmo?: string | null; relacoes_de?: string | null } | null
}
export interface TransitoProvedorUf {
  asn: number; nome?: string | null; br: boolean; clientes_uf: number; usuarios_uf: number; share_clientes: number | null; share_usuarios: number | null
}
export interface TransitoUf extends TransitoCab {
  uf: string; asns_br: number; asns_com_provedor: number; pct_com_provedor: number; elos_provedor: number; provedores_distintos: number
  hhi_clientes: number | null; top1_share: number | null; top3_share: number | null; share_provedores_estrangeiros: number | null
  provedores: TransitoProvedorUf[]
}
export interface TransitoAsn extends TransitoCab {
  asn: number; com_cliente: boolean; clientes_diretos: number; cone_asns: number; cone_br: number; cone_usuarios: number
  cone_ufs: Record<string, number>; irmaos_excluidos: number; posicao_cone_br?: number; br?: boolean
}

// ── Consumidor.gov.br ───────────────────────────────────────────────
export interface ConsMeta { natureza: string; fonte: string; url_fonte: string | null; limites: string; minimos: { base_para_media: number; reclamacoes_por_celula: number }; snapshot_date: string }
export interface ConsJanela { de: string; ate: string; meses: number; meses_com_dado: number; meses_ausentes: string[]; aviso: string | null }
/** Contagens e indicadores de um conjunto de reclamações finalizadas; os indicadores são null com menos de 30 casos (base insuficiente, não zero). */
export interface ConsMetricas { n: number; respondidas: number; avaliadas: number; resolvidas: number; pct_respondidas: number | null; indice_solucao: number | null; tempo_medio_dias: number | null; nota_media: number | null }
export interface ConsMarca extends ConsMetricas { marca: string; raizes: string[]; cnpjs_matriz: string[]; casamento: 'curada' | 'automatico' | null }
export interface ConsumidorResumo extends ConsMeta {
  janela: ConsJanela; setor_por_mes: Array<ConsMetricas & { mes: string }>
  casamento: { reclamacoes_janela: number; por_metodo: Record<string, number>; pct_com_cnpj: number | null; automaticas_descartadas_por_uf: string[]; marcas: number; marcas_com_cnpj: number; tabela_curada: { versao: number; curada_em: string; fonte: string; marcas: number; apelidos_consumidor_gov: number } }
  cidades: { reclamacoes_janela: number; sem_codigo_ibge: number; casadas_com_interrogacao: number; pct_com_codigo_ibge: number | null; maiores_sem_codigo: Array<{ uf: string; cidade: string; n: number }> }
  leitura: { meses: number; mes_inicial: string; mes_final: string; baixados: number; reclamacoes_telecom: number; meses_indisponiveis?: string[] }
}
export interface ConsumidorMarcas extends ConsMeta { janela: ConsJanela; uf: string | null; ordem: string; total: number; limit: number; offset: number; items: ConsMarca[]; nomes?: Record<string, string> }
export interface ConsumidorMunicipio extends ConsMeta { ibge: string; nome: string; uf: string; populacao: number | null; janela: ConsJanela; total: ConsMetricas; itens: Array<ConsMetricas & { marca: string; raizes: string[] }> }
export interface ConsumidorUf extends ConsMeta { uf: string; janela: ConsJanela; itens: Array<ConsMetricas & { marca: string; raizes: string[] }> }
export interface ConsumidorOperadora extends ConsMeta {
  raiz: string; janela: ConsJanela
  marcas: Array<{ marca: string; casamento: 'curada' | 'automatico' | null; base_casamento: string | null; janela: ConsMetricas | null; por_mes: Array<ConsMetricas & { mes: string }> }>
  assuntos: Array<{ marca: string; assunto: string; n: number }>; grupos: Array<{ marca: string; grupo: string; n: number }>
  setor_por_mes: Array<ConsMetricas & { mes: string }>
}

// ── Cadastro das empresas de telecom: Receita Federal cruzada com o SICI ─────────────────────
export interface CadastroMeta {
  snapshot_date: string; natureza: string; fonte: string; dump_reference: string; mes_referencia_sici?: string | null; limites: string
}
export interface CadastroPresenca {
  ibge: string; municipio: string; uf: string; estabelecimentos: number; ativos: number; tem_matriz: boolean; acessos_fixo: number; acessos_movel: number
}
export interface CadastroOperadora extends CadastroMeta {
  raiz: string; razao_social: string | null; nome_fantasia: string | null; natureza_juridica: { codigo: string; descricao: string | null } | null
  porte: string | null; capital_social: number | null; simples: boolean; mei: boolean
  matriz: { cnpj: string; uf: string | null; ibge: string | null; municipio: string | null; situacao: string | null; inicio: string | null; cnae: string | null; cnae_descricao: string | null } | null
  estabelecimentos: { total: number; ativos: number; baixados: number; filiais_ativas: number }
  presenca: CadastroPresenca[]
  resumo_presenca: { municipios_com_estabelecimento_ativo: number; municipios_com_acessos: number; com_ambos: number; so_acessos: number; so_estabelecimento: number }
}
export interface CadastroMercadoUf extends CadastroMeta {
  uf: string; entradas_por_ano: Array<{ ano: number; total: number }>; baixas_por_ano: Array<{ ano: number; total: number }>; ativas: number
  resumo: { empresas_no_recorte: number; operadoras_com_cadastro: number; empresas_ativas: number; estabelecimentos_sem_ibge: number }
}

/** Crédito público (BNDES) e sanções (CEIS/CNEP) por operadora (`/financiamento/operadoras/{cnpj}`). */
export interface FinanciamentoOperacao {
  cnpj: string; contrato: string; data: string | null; contratado: number | null; desembolsado: number | null; produto: string; instrumento: string; forma: string
  uf: string; ibge: string; cnae: string; porte: string; situacao: string; projeto: string
}
export interface FinanciamentoBndes {
  operacoes_total: number; contratado_total: number; desembolsado_total: number; primeira: string | null; ultima: string | null
  por_ano: Array<{ ano: string; operacoes: number; contratado: number; desembolsado: number }>
  por_uf: Array<{ uf: string; operacoes: number; contratado: number; desembolsado: number }>
  operacoes: FinanciamentoOperacao[]; operacoes_omitidas: number
}
export interface SancaoRegistro {
  cnpj: string; cadastro: 'CEIS' | 'CNEP'; codigo: string; categoria: string; inicio: string | null; fim: string | null; publicacao: string | null; abrangencia: string; orgao: string
  uf_orgao: string; esfera: string; fundamento: string; processo: string; multa?: number; situacao: 'vigente' | 'futura' | 'encerrada'; sem_prazo: boolean; sem_fim_informado?: boolean
}
export interface FinanciamentoOperadora {
  snapshot_date: string; natureza: string; limites: string; raiz: string
  fontes: { bndes: { fonte: string; licenca: string; dump_reference?: string | null }; cgu: { fonte: string; arquivos?: Record<string, string> | null } }
  financiamento?: FinanciamentoBndes
  sancoes?: { vigentes: SancaoRegistro[]; futuras: SancaoRegistro[]; encerradas: SancaoRegistro[]; total: number }
}

// Contratos públicos: resultados de itens publicados no PNCP (Compras.gov.br), coletados em rodízio. Ausência não é zero.
export interface ContratosCobertura {
  raizes_no_universo: number; raizes_faixa_a: number; raizes_com_leitura: number; raizes_sem_leitura: number; raizes_com_resultado: number; raizes_incompletas: number
  leitura_mais_antiga: string | null; leitura_mais_recente: string | null; janela_inicio: string | null
  itens: number; contratacoes: number; contratacoes_com_detalhe: number; contratacoes_com_municipio: number; municipios_com_contratacao: number
}
export interface ContratosCabecalho {
  snapshot_date: string; coletado_em: string | null; natureza: string; licenca: string; aviso: string; limites: string; cobertura: ContratosCobertura
  fonte: { nome: string; url: string; api?: string | null; licenca: string; consultado_em: string }
}
export interface ContratosSerie { itens: number; contratacoes: number; valor: number }
export interface ContratosRecente {
  contratacao: string; data: string | null; orgao: string | null; orgao_detalhado: boolean; esfera: string | null; uf: string | null; municipio: string | null; ibge: string | null
  modalidade: string | null; objeto: string | null; itens: number; valor: number
}
export interface ContratosOperadora extends ContratosCabecalho {
  raiz: string; nome: string | null; cnpj_consultado: string | null; faixa: 'A' | 'B' | null; lida_em: string | null; idade_dias: number | null; desde: string | null; incompleto: boolean
  resultado: 'com_resultado' | 'sem_resultado_na_consulta'; itens: number; contratacoes: number
  itens_cancelados?: number; orgaos?: number; valor_homologado?: number; primeiro_resultado?: string | null; ultimo_resultado?: string | null; contratacoes_detalhadas?: number
  por_ano?: Array<{ ano: string } & ContratosSerie>; por_uf?: Array<{ uf: string } & ContratosSerie>; por_esfera?: Array<{ esfera: string } & ContratosSerie>
  orgaos_principais?: Array<{ org: string | null; orgao: string | null; esfera: string | null; uf: string | null; itens: number; contratacoes: number; valor: number }>
  recentes?: ContratosRecente[]
}
export interface ContratosMunicipio extends ContratosCabecalho {
  ibge: string; criterio_municipio: string; municipio: string | null; uf: string | null; itens: number; contratacoes: number; valor: number
  fornecedores: Array<{ raiz: string; cnpj: string | null; nome: string | null; itens: number; contratacoes: number; valor: number }>
}

/** `GET /territorio/municipio/{ibge}/semelhantes`: municípios do mesmo porte e a posição do município entre eles. */
export interface SemelhanteMunicipio { ibge: string; nome: string; uf: string; acessos: number | null; penetracao: number | null; fibra_pct: number | null; km_ptt: number | null; domicilios: number | null }
export interface MunicipiosSemelhantes extends TerritorioMeta {
  ibge: string
  criterio: string
  total_do_porte: number
  municipio: SemelhanteMunicipio
  posicao: { penetracao: { posicao: number; de: number } | null; fibra_pct: { posicao: number; de: number } | null }
  items: SemelhanteMunicipio[]
}

export interface SerieMercadoMunicipio {
  snapshot_date: string
  mes_referencia: string
  meses: string[]
  fonte: string
  parametros: { meses: number; lideres: number; linhas_max?: number }
  acessos: Array<number | null>
  hhi: Array<number | null>
  lideres: Array<{ cnpj: string; empresa: string; share: Array<number | null> }>
}

/** Cruzamentos de mercado: HHI por CNPJ e por grupo econômico (inferido). */
export type FaixaHhi = 'competitivo' | 'moderado' | 'concentrado'
interface MercadoGruposMeta { snapshot_date: string; mes_referencia: string; natureza: string; fonte: string; limites: string; faixas: Record<FaixaHhi, string> }
export interface MercadoGruposMunicipio extends MercadoGruposMeta {
  uf: string; acessos?: number; avisos_cnpj?: string[]; avisos_grupo?: string[]
  hhi_cnpj: number | null; hhi_grupo: number | null; n_cnpjs: number; n_grupos: number; faixa_cnpj: FaixaHhi | null; faixa_grupo: FaixaHhi | null
  lider_grupo: { id: string; empresa: string; share: number; e_grupo: boolean }
}
export interface MercadoGruposUf extends MercadoGruposMeta {
  acessos?: number; n_cnpjs?: number; n_grupos?: number; lider_grupo_share?: number | null; avisos_cnpj?: string[]; avisos_grupo?: string[]
  hhi_cnpj: number | null; hhi_grupo: number | null; faixa_cnpj: FaixaHhi | null; faixa_grupo: FaixaHhi | null; municipios: number; municipios_mudam_de_faixa: number
}
export interface SobreposicaoOperadora extends MercadoGruposMeta {
  concorrentes: Array<{ cnpj: string; empresa: string; municipios_em_comum: number; acessos_dele_nos_comuns: number; acessos_dela_nos_comuns: number; mesmo_grupo: boolean }>
}
/** Municípios em cada faixa de HHI local; `sem_dado` quando o município não tem HHI. A soma é o total de municípios (PT-23). */
export type MunicipiosPorFaixa = Record<FaixaHhi | 'sem_dado', number>
export interface ResumoMercadoGrupos extends MercadoGruposMeta {
  resumo: { municipios: number; mudam_de_faixa: number; transicoes: Record<string, number>; grupos_com_mais_de_um_cnpj_no_mercado: number
    por_faixa_cnpj?: MunicipiosPorFaixa; por_faixa_grupo?: MunicipiosPorFaixa }
  ufs: Record<string, { hhi_cnpj: number | null; hhi_grupo: number | null; faixa_cnpj: FaixaHhi | null; faixa_grupo: FaixaHhi | null
    acessos?: number; n_cnpjs?: number; n_grupos?: number; lider_grupo_share?: number | null; avisos_cnpj?: string[]; avisos_grupo?: string[]
    municipios?: number; municipios_por_faixa_cnpj?: MunicipiosPorFaixa; municipios_por_faixa_grupo?: MunicipiosPorFaixa }>
  /** HHI nacional por CNPJ, como contraste com o local (cálculo do projeto) */
  brasil?: { hhi_cnpj: number | null; acessos: number | null; n_cnpjs: number | null; nota: string }
}

/** Uma linha de `GET /grupos/{id}/municipios`: o conjunto de CNPJs do grupo num município (PT-23). */
export interface GrupoMunicipioLinha {
  ibge: string; nome: string; uf: string
  acessos: number; cnpjs_do_conjunto: number
  municipio_acessos: number | null; parcela: number | null; declarantes: number | null
  hhi_grupo: number | null; faixa_grupo: FaixaHhi | null; avisos_grupo: string[] | null
  hhi_cnpj: number | null; faixa_cnpj: FaixaHhi | null
}
export type OrdemGrupoMunicipios = 'acessos' | 'parcela' | 'hhi' | 'nome' | 'uf'
export interface GrupoMunicipios {
  snapshot_date: string; grupo_id: string; mes_referencia: string | null; tamanho: number
  grupo_inferivel?: boolean; grupo_inferivel_rotulo?: string; como_ler?: string
  natureza: string; limites: string
  resumo: { municipios: number; com_mais_da_metade: number; com_um_so_declarante: number; acessos: number; ufs: number }
  filtros: { uf: string | null; q: string | null }; ordem: string; page: number; limit: number
  total: number; items: GrupoMunicipioLinha[]
}

/** Rede no território: estimativas e inferências com cobertura. */
interface RedeMeta { snapshot_date: string; natureza: string; limites: string; fontes: Record<string, string | null> }
export interface RedeIpv6 { acessos: number; acessos_com_estimativa?: number; v6_estimado: number; pct_v6: number | null; cobertura: number | null }
export interface RedeRov extends RecorteAgregado { usuarios: number; usuarios_com_medida: number; usuarios_atras_rov: number; pct_atras_rov: number | null; cobertura: number | null }
export interface RedeTransito { acessos: number; acessos_com_relacao: number; acessos_provedor_unico?: number; pct_provedor_unico: number | null; cobertura: number | null; provedor_principal: { asn: number; nome: string; pct_dos_acessos: number } | null }
export interface RedeTerritorioMunicipio extends RedeMeta { ipv6: RedeIpv6 | null; transito: RedeTransito | null }
export interface RedeTerritorioUf extends RedeMeta { ipv6: RedeIpv6 | null; rov: RedeRov | null; transito: RedeTransito | null }
export interface ResumoRedeTerritorio extends RedeMeta {
  ipv6: { ufs: Record<string, RedeIpv6>; brasil: RedeIpv6 }
  rov: { ufs: Record<string, RedeRov>; brasil: RedeRov; parametros: { min_amostras: number } }
  transito: { ufs: Record<string, RedeTransito> }
}

/** Interconexão mensurável do AS e alcance de CDN. Só fatos observados; nunca "não troca tráfego com B". */
export interface InterconexaoAsn {
  snapshot_date: string; asn: number; limites: string; uf_sede: string | null; usuarios_estimados: number | null; carregadores_disponiveis: boolean
  origem_sem_direto: Array<{ ixp: string; nome: string; uf: string | null; familias: Array<'v4' | 'v6'>; mesma_uf: boolean; km_da_sede?: number | null; carregadores: Array<{ asn: number; caminhos: number; via?: number[]; vinculo?: 'mesmo_cnpj' | 'mesma_org' | null }> }>
  sessoes: Array<{ ixp: string; nome: string; situacao: string; rotulo: string }>
  rejeicoes: Array<{ ixp: string; nome: string; rotas_rejeitadas: number; motivos: Array<{ rotulo: string | null; codigo: string | null; rotas: number | null }>; perfil: string | null; perfil_inferido: boolean | null; acoes: string[] }>
  resumo: { origem_sem_direto: number; sem_sessao: number; sessao_parcial: number; ptts_com_rejeicao: number }
}
export interface AlcanceCdns {
  snapshot_date: string; limites: string; usuarios_br_com_uf: number
  cdns: Array<{ name: string; ptts: string[]; usuarios_alcancados: number; pct: number | null; por_uf: Record<string, { usuarios: number; alcancados: number; pct: number }> }>
}

/** `GET /mercado/maiores`: posição mês a mês das maiores operadoras e as maiores empresas-ou-grupos do mercado fixo. */
export interface MercadoMaiores {
  snapshot_date: string; mes_referencia: string | null; meses: string[]
  operadoras: { cnpj: string; empresa: string; posicao: (number | null)[]; acessos: (number | null)[] }[]
  unidades: { id: string; grupo: boolean; nome: string; acessos: number; cnpjs: number; share: number | null }[]
  demais: { acessos: number; share: number | null; unidades: number }
  total_acessos: number; natureza: string; aviso: string
}

/** `GET /grupos/{id}?include=mercado`: o grupo no mercado fixo (acessos declarados ao SICI; agrupamento inferido). */
export interface GrupoMercadoFixo {
  grupo_id: string; mes_referencia: string | null; meses: string[]
  serie: { mes: string; acessos: number | null; parcela: number | null }[]
  posicao: { atual: number | null; ha_12_meses: number | null; mes_ha_12_meses: string | null; unidades: number }
  cnpjs_total: number; cnpjs_com_acessos: number
  por_uf: { uf: string; acessos: number; parcela_do_grupo: number | null; parcela_na_uf: number | null; hhi_cnpj: number | null; hhi_grupo: number | null; faixa_grupo: string | null }[]
  por_tecnologia: Record<string, number>
  sobreposicao_interna: { municipios: number; com_mais_de_um_cnpj: number }
  concorrentes: { cnpj: string; empresa: string | null; municipios_em_comum: number; acessos_dele_nos_comuns: number | null }[]
  natureza: string; limites: string
}

/** `GET /grupos/{id}?include=regulatorio`: outorgas, multas, RQUAL e reclamações das empresas do grupo; tudo em ordem alfabética, sem ranking. */
export interface GrupoRegulatorio {
  grupo_id: string; empresas: number
  outorgas: Record<string, number>
  multas: { empresas_com_registro: number; multas: number; original: number; pago: number; saldo: number; por_empresa: { raiz: string; empresa: string | null; multas: number; original: number; pago: number; saldo: number }[]; fonte: string | null; limites: string | null }
  qualidade: { prestadoras: { servico: string; prestadora: string; municipios: number; casamento: string | null }[]; limites: string | null }
  reclamacoes_anatel: { marcas: string[]; anos: { ano: number; reclamacoes: number; por_servico: Record<string, number> }[]; limites: string | null }
  consumidor: { janela: { de: string; ate: string } | null; marcas: { marca: string; casamento: string | null; n: number | null; pct_respondidas: number | null; indice_solucao: number | null; nota_media: number | null }[]; reclamacoes_finalizadas: number; limites: string | null }
  natureza: string; limites: string
}

/** `GET /grupos/{id}?include=tecnico`: os ASes do grupo, IPv6, RPKI, trânsito e PTTs. */
export interface GrupoTecnico {
  grupo_id: string; asns_total: number; asns_com_dado: number; asns_detalhados: number; asns_omitidos: number; visibilidade_bgp: boolean
  prefixos: { v4: number; v6: number }
  ipv6: { asns_com_ipv6: number; usuarios: number; usuarios_v6: number; pct_v6: number | null }
  rpki: { validados: number; valido: number; invalido: number; sem_roa: number; valido_pct: number | null }
  transito: { asns_multihomed: number; provedores: { asn: number; asns_do_grupo: number }[] }
  ptts: { ixp: string; asns: number[] }[]
  por_asn: { asn: number; nome: string | null; usuarios: number | null; pct_v6: number | null; prefixos_v4: number; prefixos_v6: number; tem_ipv6: boolean; roa_valido_pct: number | null; ptts_diretos: number }[]
  natureza: string; limites: string
}

/** `GET /grupos/{id}?include=relacoes`: com que evidência as empresas do grupo estão ligadas. Só estrutura entre empresas (PJ); nunca nome nem CPF de sócio. */
export interface GrupoRelacoes {
  grupo_id: string; classificacao: string | null; empresas: number; referencia_receita: string | null
  tipos: Record<string, string>
  ligacoes: { tipo: string; tipo_rotulo: string; de: string; para: string; de_nome: string; para_nome: string; socios: number | null; forca?: 'forte' | 'fraca'; classes_qualificacao?: string[] }[]
  /** Rótulos das classes de qualificação e da força da evidência, a regra de ligação e o resumo (só em snapshots novos). */
  classes?: Record<string, string>; forcas?: Record<string, string>; regra_ligacao?: string
  resumo?: { ligacoes: number; fortes: number; fracas: number }
  fora_do_grupo: { total: number; itens: { cnpj: string; empresa: string; tipo: string; tipo_rotulo: string; socios_em_comum: number | null; liga_a: string[] }[] }
  controladoras_externas: { cnpj_basico: string; razao_social: string | null; situacao_cadastral: string | null; natureza_juridica: string | null; controla: string[] }[]
  natureza: string; limites: string
}

/** `GET /brasil/indicadores`: agregados do país. */
export interface MedicaoApnicPais { asns?: number; mediana_pct?: number; media_ponderada_pct?: number; faixas?: Record<string, number>; fonte?: { fonte?: string; as_of?: string } | null }
export interface BrasilIndicadores {
  snapshot_date: string
  ipv6: { usuarios: number; usuarios_ipv6: number; pct_usuarios_ipv6: number | null; asns_com_estimativa: number; asns_com_ipv6: number; fonte: string; nota: string }
  dnssec?: MedicaoApnicPais
  rov?: MedicaoApnicPais
  asns?: number
  /** ASNs da lista do Registro.br no IX.br, cada um contado uma vez no país: diretos (sessão com route server em algum PTT), indiretos (só originam prefixos vistos nos PTTs) e os que aparecem como origem. */
  ixbr?: { asns_br_total: number; asns_br_diretos: number; asns_br_indiretos: number; asns_br_originam: number; fonte: string; nota: string }
  /** HHI nacional do mercado fixo por CNPJ (acessos declarados ao SICI); ausente sem o produto de indicadores. */
  mercado?: { hhi_cnpj: number; acessos: number | null; n_cnpjs: number | null; mes_referencia: string | null; fonte: string; nota: string }
  /** Retrato por macro-região da sede do AS (PT-22 / PANORAMA TÉCNICO 5.2); as linhas e `sem_regiao` fecham o `total`. Ausente sem o cadastro de organizações. */
  por_regiao?: {
    regioes: Array<{ regiao: string; nome: string; asns: number; usuarios: number; usuarios_ipv6: number; usuarios_com_roa: number; usuarios_sessao_rs: number; asns_com_ipv6: number }>
    sem_regiao: { asns: number; usuarios: number; usuarios_ipv6: number; usuarios_com_roa: number; usuarios_sessao_rs: number; asns_com_ipv6: number }
    total: { asns: number; usuarios: number; usuarios_ipv6: number; usuarios_com_roa: number; usuarios_sessao_rs: number; asns_com_ipv6: number }
    fonte: string
    nota: string
  }
  prontidao?: {
    natureza?: string
    agregado: { asns: number; classes: Record<string, number>; asns_com_indice: number; media_ponderada_usuarios: number | null; mediana: number | null; usuarios?: number;
      cobertura_pilares: Record<string, number>; medicoes: Record<string, { pilar: string; asns: number; media: number | null; media_ponderada_usuarios: number | null }> }
    pilares: Record<string, { nome: string; peso: number; descricao: string; componentes: Record<string, { descricao: string }> }>
    limites?: string | string[]
  }
  /** Panorama técnico: publicação de ROA/ASPA (corpo de `/rpki/summary`) e o resumo da análise de roteamento (null em snapshot sem o arquivo). */
  rpki?: { publicacao: Omit<RpkiSummary, 'snapshot_date'>; rotas: ResumoRoteamento | null }
}

/** Rotas brasileiras (P_BR) por estado RPKI de origem (RFC 6811), com a união do espaço de cada estado. */
export interface EstadoRpkiFamilia {
  rotas: number; valid: number; invalid: number; not_found: number
  pct: { valid: number | null; invalid: number | null; not_found: number | null }
  espaco: { unidade: string; total: number; valid: number; invalid: number; not_found: number }
  asns_origem_com_invalida: number
}

/** `published/{date}/routing_analysis_resumo.json`: totais nacionais da análise de roteamento. */
export interface ResumoRoteamento {
  snapshot_date: string
  definicao: string
  vrps: number | null
  /** `asn_br_fora_de_bloco`: rotas de ASN da lista do Registro.br em espaço de outro RIR, fora do total (ausente antes da regra de D4). */
  rotas_br: Record<'v6' | 'v4', { pbr_routes: number | null; pbr_pct: number | null; br_origin_asns: number | null; total_routes_global: number | null; asn_br_fora_de_bloco?: number | null }>
  rpki: Record<'v6' | 'v4', EstadoRpkiFamilia>
  saude: Record<'v6' | 'v4', { mais_especificos: number | null; mais_especificos_pct: number | null; filtraveis: number | null }> & { /** Por família quando medido; nulo (com `moas_indisponivel`) quando a coleta do snapshot guardou uma origem por prefixo. */ moas: Record<'v6' | 'v4', { prefixos: number; prefixos_br: number; coletores: number } | null> | null; moas_indisponivel?: string }
  limites: string
}
