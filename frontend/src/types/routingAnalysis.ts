export interface SummaryStats {
  total_routes_global: number
  total_prefixes_global: number
  total_asns_global: number
  pbr_routes: number
  pbr_pct: number
  br_origin_asns: number
  pbr_asns: number
}

export interface PbrCompositionEntry {
  routes: number
  asns: number
  /** `asn_br_fora_de_bloco` (alias `origin_only_br`): apoio, fora do total de rotas brasileiras. */
  fora_do_total?: boolean
}

/** Rota brasileira = prefixo em bloco do Registro.br (a origem não define): a composição traz `total` e a contagem de apoio
 * `asn_br_fora_de_bloco`. Documentos gerados antes da regra não trazem `total` e somavam "apenas origem BR" ao total. */
export function composicaoPorPrefixo(data: { pbr_composition: { v6: Record<string, PbrCompositionEntry> } }): boolean {
  return 'total' in (data.pbr_composition?.v6 ?? {})
}

export interface PrefixLengthEntry {
  length: number
  count: number
  span: number
  pct_routes: number
  pct_span: number
}

export interface MoreSpecificsStats {
  global_root: number
  global_more_specific: number
  pbr_root: number
  pbr_more_specific: number
  same_origin: number
  diff_origin: number
  max_depth: number
  avg_depth: number
}

export interface TopAsnMoreSpecifics {
  asn: number
  name: string
  v4_routes: number
  v4_root: number
  v4_more_spec: number
  v6_routes: number
  v6_root: number
  v6_more_spec: number
}

export interface AggregationEntry {
  asn: number
  name: string
  afi: string
  current: number
  by_origin: number
  savings_origin: number
  by_path: number
  savings_path: number
  savings_path_pct: number
}

export interface OriginRoute {
  prefix: string
  rpki: 'valid' | 'invalid' | 'not_found'
}

export interface OriginDetail {
  asn: number
  name: string
  cnpj: string
  routes: OriginRoute[]
}

export interface RegistroBrCoverage {
  block: string
  afi: string
  asn: number
  name: string
  cnpj: string
  routes_inside: number
  coverage_pct: number
  has_exact_aggregate: boolean
  origin_count: number
  origins: number[]
  origins_detail: OriginDetail[]
  category: 'not_announced' | 'partial' | 'full_with_agg' | 'full_without_agg' | 'multi_origin'
}

export interface MoasEntry {
  prefix: string
  afi: string
  origins: number[]
  br_origins: number[]
  is_prefix_br: boolean
}

export interface TooSpecificEntry {
  prefix: string
  origin_as: number
  name: string
  has_covering: boolean
  is_prefix_br: boolean
}

export interface GlobalComparison {
  pct_24_global?: number
  pct_24_pbr?: number
  pct_gt24_global?: number
  pct_gt24_pbr?: number
  pct_48_global?: number
  pct_48_pbr?: number
  pct_gt48_global?: number
  pct_gt48_pbr?: number
  pct_more_spec_global: number
  pct_more_spec_pbr: number
}

export interface AsPathStatsAfi {
  unique_paths_raw: number
  unique_paths_norm: number
  avg_len_raw: number
  avg_len_norm: number
  median_norm: number
  p95_norm: number
  addr_weighted_len: number
  routes_with_prepend: number
  prepend_pct: number
  private_as_in_path: number
  private_as_as_origin: number
  as_loops: number
  as_trans_present: number
}

export interface TopPrepender {
  asn: number
  name: string
  afi: string
  routes: number
  routes_with_prepend: number
  prepend_pct: number
  avg_excess: number
  max_excess: number
}

export interface UpstreamDiversity {
  asn: number
  name: string
  afi: string
  routes: number
  upstream_count: number
  main_upstream: number
  main_upstream_pct: number
}

export interface HygieneIssue {
  prefix: string
  afi: string
  origin_as: number
  issue: 'private_as_origin' | 'private_as_path' | 'as_loop' | 'as_trans'
  as_path: number[]
}

export interface TopCommunity {
  community: string
  count: number
  asns: number[]
  description?: string
  operator?: string
}

export interface CommunityStatsAfi {
  routes_with_communities: number
  community_pct: number
  routes_with_large_communities: number
  no_export_count: number
  no_advertise_count: number
  blackhole_candidates: number
  private_community_leak_count: number
  top_communities: TopCommunity[]
}

export interface AsPathStats {
  v4: AsPathStatsAfi
  v6: AsPathStatsAfi
  top_prependers: TopPrepender[]
  upstream_diversity: UpstreamDiversity[]
  hygiene_issues: HygieneIssue[]
  community_stats: { v4: CommunityStatsAfi; v6: CommunityStatsAfi }
}

export interface RoutingAnalysis {
  snapshot_date: string
  generated_at: string
  has_path_data: boolean
  br_asns_visible: number
  br_asns_registered: number
  summary: { v4: SummaryStats; v6: SummaryStats }
  pbr_composition: {
    v4: Record<string, PbrCompositionEntry>
    v6: Record<string, PbrCompositionEntry>
  }
  prefix_length_dist: { v4: PrefixLengthEntry[]; v6: PrefixLengthEntry[] }
  more_specifics: { v4: MoreSpecificsStats; v6: MoreSpecificsStats }
  top_asns_more_specifics: TopAsnMoreSpecifics[]
  aggregation_by_asn: AggregationEntry[]
  registro_br_coverage: RegistroBrCoverage[]
  /** Sempre nulo: a coleta guarda uma origem por prefixo e não detecta MOAS (motivo em `moas_indisponivel`). */
  moas: MoasEntry[] | null
  moas_indisponivel?: string
  too_specific: { v4: TooSpecificEntry[]; v6: TooSpecificEntry[] }
  global_comparison: { v4: GlobalComparison; v6: GlobalComparison }
  as_path_stats: AsPathStats | null
}
