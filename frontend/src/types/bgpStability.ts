export type Classification =
  | 'chronic_flapper'
  | 'burst_event'
  | 'attribute_oscillator'
  | 'more_specific_injection'
  | 'noisy'

export type Severity = 'critical' | 'high' | 'medium' | 'low'

export type NoiseCategory = 'estavel' | 'inquieto' | 'barulhento' | 'critico'

export interface StabilityBucket {
  min: number
  max: number | null
  label: string
  asn_count: number
}

export interface StabilityDistribution {
  buckets:         StabilityBucket[]
  p50:             number
  p90:             number
  p95:             number
  p99:             number
  max:             number
  asn_count_total: number
}

export interface DailyStability {
  date:             string
  total_events:     number
  announcements_v4: number
  withdrawals_v4:   number
  attr_updates_v4:  number
  announcements_v6: number
  withdrawals_v6:   number
  attr_updates_v6:  number
  active_prefixes:  number
}

export interface PrefixStability {
  prefix:                   string
  afi:                      'v4' | 'v6'
  total_events:             number
  announcements:            number
  withdrawals:              number
  attribute_updates:        number
  flap_cycles:              number
  mean_hold_time_sec:       number
  burst_concentration_1h:   number
  burst_peak_utc:           string
  daily_events:             number[]
}

export interface AsPeriodStats {
  total_events:                  number
  announcements:                 number
  withdrawals:                   number
  attribute_updates:             number
  announcements_v4:              number
  withdrawals_v4:                number
  attribute_updates_v4:          number
  announcements_v6:              number
  withdrawals_v6:                number
  attribute_updates_v6:          number
  events_per_prefix_per_day:     number
  events_per_prefix_per_day_v4:  number
  events_per_prefix_per_day_v6:  number
  flapping_prefixes:             number
  max_flap_cycles:               number
  mean_hold_time_sec:            number
  burst_concentration_1h:        number
}

/** Série horária por tipo (168 valores = 7 dias × 24h) */
export interface HourlySeries {
  ann:      number[]
  wd:       number[]
  attr_upd: number[]
}

export interface AsStability {
  asn:             number
  name:            string
  rank:            number
  classification:  Classification
  severity:        Severity
  noise_category?: NoiseCategory
  prefix_count_v4: number
  prefix_count_v6: number
  period:          AsPeriodStats
  daily:           DailyStability[]
  /** Presente apenas para severity critical/high/medium */
  hourly?:         HourlySeries
  top_prefixes:    PrefixStability[]
}

export interface EppdStats {
  median: number
  mean:   number
  max:    number
}

export type DeepVerdict =
  | 'upstream_instability'
  | 'prefix_specific'
  | 'origin_instability'

export interface HotPrefix {
  prefix:                  string
  flap_events:             number
  dominant_upstream_asn:   number | null
  dominant_upstream_name:  string
  dominant_upstream_pct:   number
}

export interface AsDiagnosis {
  asn:                       number
  verdict:                   DeepVerdict
  prefix_sync_score:         number
  suspected_upstream_asn:    number | null
  suspected_upstream_name:   string
  upstream_concentration_pct: number
  hot_prefixes:              HotPrefix[]
}

export interface SuspectedUpstream {
  asn:                  number
  name:                 string
  affected_origin_ases: number[]
  events_attributed:    number
  peak_hour_utc:        string
}

export interface BgpStabilityDeep {
  generated_at:        string
  date:                string
  top_n:               number
  suspected_upstreams: SuspectedUpstream[]
  as_diagnosis:        AsDiagnosis[]
  published_at?:       string
}

export interface BgpStabilityHistoryEntry {
  date: string
  data: BgpStability
}

export interface BgpStabilityHistory {
  weeks: BgpStabilityHistoryEntry[]
}

export interface BgpStability {
  epppd_stats?: EppdStats
  period: {
    start:             string
    end:               string
    days:              number
    collector:         string
    generated_at:      string
    files_processed:   number
    files_missing:     number
    raw_events_seen:   number
    events_counted:    number
    dedup_rate_pct:    number
    br_events_v4:      number
    br_events_v6:      number
  }
  distribution: {
    v4: StabilityDistribution
    v6: StabilityDistribution
  }
  /** Série horária agregada de todos os ASes BR */
  hourly_global: {
    timestamps: string[]
  } & HourlySeries
  as_stability:  AsStability[]
  published_at?: string
  /** Só na visão geral: os 10 primeiros ASNs de cada ordem da lista "Ver todos" (coluna → sentido → ASNs) e os ASes que não estão em
   *  `as_stability`. Com eles a tabela recolhida mostra o topo da lista inteira, não as 10 linhas da visão geral reordenadas. */
  ordens?: Partial<Record<'rank' | 'epppd' | 'epppd_v6' | 'epppd_v4' | 'flap', { asc: number[]; desc: number[] }>>
  as_stability_ordens?: AsStability[]
}

/** `GET /bgp-stability/asn/{asn}` (1.4.2.1): o que a página de um AS usa da estabilidade, sem o documento inteiro. */
export interface BgpStabilityAsn {
  snapshot_date: string
  asn: number
  stability: AsStability | null
  epppd_stats: EppdStats | null
  timestamps: string[]
  diagnosis: AsDiagnosis | null
  weeks: Array<{ date: string; timestamps: string[]; series: HourlySeries }>
}

/** `GET /bgp-stability/overview` (1.4.2.5): a seção de estabilidade da página `/bgp`, sem o documento inteiro. */
export interface BgpStabilityVisaoGeral extends Omit<BgpStability, 'as_stability'> {
  snapshot_date: string
  /** Só o top 10 por rank, sem `hourly` nem `top_prefixes`. */
  as_stability: AsStability[]
  categorias: Record<NoiseCategory, number> & { total: number }
  severidades: Record<string, number>
  /** ASes com severidade crítica, alta ou média: o que a lista "Ver todos" mostra (carregada sob demanda). */
  medio_ou_maior: number
}
