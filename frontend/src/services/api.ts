import type { BrasilIndicadores,
  Limites,
  HealthResponse,
  SnapshotListResponse,
  SnapshotDetails,
  IXPListResponse,
  IXPIndexEntry,
  HistoricoBloco,
  HistoricoEvento,
  IXPDocument,
  IXPMembersResponse,
  IXPPeersResponse,
  ASNIXPPeersResponse,
  IXPHilbertData,
  IXPHilbertV6Data,
  IXPHilbertV4DetailData,
  HilbertV4DetailLayer,
  PaginatedASNs,
  ASNsLote,
  ASNDocument,
  ASNContactsResponse,
  ASNPathsResponse,
  HilbertV4Data,
  HilbertV6Data,
  ExternalIXPListResponse,
  ExternalIXPDocument,
  IXPCompareMembersResponse,
  CDNPresenceResponse,
  RpkiSummary,
  PaginatedOutorgas,
  SCMStats,
  AsnsPorOrganizacaoResponse,
  SiciStats,
  SiciAcessos,
  SiciAsnMunicipios,
  SiciMunicipioRow,
  PerfilMunicipio,
  Regiao,
  CadastroOperadora,
  FinanciamentoOperadora,
  ContratosOperadora,
  ContratosMunicipio,
  CadastroMercadoUf,
  RankingOperadoras,
  SegurancaAsn,
  RouteServersAsn,
  OrganizacaoAsn,
  BloqueiosAsn,
  AbusoAsn,
  TransitoAsn,
  FacilitiesAsn,
  PeeringAsn,
  FacilitiesLista,
  FacilityDetalhe,
  FacilitiesPtt,
  PortasIxp,
  RouteServersIxp,
  ParticipantesPtt,
  RankingRouteServers,
  PoliticaAsn,
  RejeicoesIxp,
  CommunitiesResp,
  CeticTabelas,
  CeticIndicadores,
  CeticEstimativas,
  DemandaOferta,
  ErbsMunicipios,
  FustMunicipios,
  ProntidaoAsn,
  ProntidaoResumo,
  FustResumo,
  MultasResumo,
  MultasEmpresas,
  QualidadeResumo,
  QualidadePrestadoras,
  QualidadeSerie,
  ReclamacoesResumo,
  ReclamacoesMarcas,
  ConsumidorResumo,
  ConsumidorMarcas,
  EspectroResumo,
  EspectroFaixas,
  SatelitesResumo,
  SatelitesDireitos,
  Ipv4Transferencias,
  Ipv4Mercado,
  Ipv4Recuperacao,
  Ipv4CicloDeVida,
  Ipv4Espaco,
  Ipv4Uso,
  Ipv4RecursosAsn,
  Ipv4Subasignacoes,
  SegurancaResumo,
  RankingTerritorio,
  RankingMunicipios,
  SemDeclaracaoSici,
  PerfilOperadora,
  PerfilUf,
  RadarAsn,
  RadarUf,
  ExposicaoAsn,
  ResumoUf,
  MunicipiosSemelhantes,
  SiciMunicipioDetalhe,
  SiciMunicipiosMapaResponse,
  SiciDivergenciasResponse,
  SiciDivergenciasSCMResponse,
  PaginatedOperadoras,
  OperadoraDetalhe,
  OperadoraContactsResponse,
  PaginatedSMPs,
  SMPStats,
  SMPDetailResponse,
  PaginatedSTFCs,
  STFCStats,
  STFCDetailResponse,
  PaginatedSEACs,
  SEACStats,
  SEACDetailResponse,
  SiciMovelStats,
  MovelMunicipioDetalhe,
  PaginatedOperadorasMovel,
  OperadoraMovelDetalhe,
  GrupoSocietarioListResponse,
  GrupoDetalhe,
  EmpresasRelacionadasResponse,
} from '../types/api'
import type { RoutingAnalysis } from '../types/routingAnalysis'
import { getFingerprint } from '../auth/fingerprint'

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? ''

// Header pelo qual o backend recebe o fingerprint de dispositivo (ver
// api/auth/anon_session.py::FINGERPRINT_HEADER) e header pelo qual ele
// sinaliza, em qualquer resposta, que o limite de navegação anônima foi
// atingido (ver api/main.py::anon_session_guard).
const FINGERPRINT_HEADER = 'X-Device-Fingerprint'
const ANON_LIMIT_HEADER = 'X-Anon-Limit-Reached'
const AREA_HEADER = 'X-Arandu-Area'

/** Área da página em uso: o orçamento de uso anônimo só corre em `metered`
 * (ver auth/accessPolicy.ts). Definida pelo AuthProvider a cada troca de rota. */
export type AccessArea = 'open' | 'metered'
let currentArea: AccessArea = 'open'
export function setCurrentArea(area: AccessArea): void {
  currentArea = area
}

type AnonLimitListener = () => void
const anonLimitListeners = new Set<AnonLimitListener>()

/** Registra um callback chamado sempre que uma resposta sinalizar limite de
 * navegação anônima atingido. Usado pelo AuthContext para atualizar o estado
 * sem que cada chamador de `get`/`post` precise checar isso manualmente. */
export function onAnonLimitReached(cb: AnonLimitListener): () => void {
  anonLimitListeners.add(cb)
  return () => anonLimitListeners.delete(cb)
}

type LoginRequiredListener = (reason: string | null) => void
const loginRequiredListeners = new Set<LoginRequiredListener>()

/** Callback chamado quando a API responde 401 `login_required` (expandir
 * lista, histórico, contatos): o AuthContext abre o modal de login. */
export function onLoginRequired(cb: LoginRequiredListener): () => void {
  loginRequiredListeners.add(cb)
  return () => loginRequiredListeners.delete(cb)
}

/** Erro de acesso (login exigido ou orçamento esgotado) — as telas distinguem
 * de falha de rede para mostrar um aviso em vez de "erro ao carregar" (`components/ui/EstadoDados`). */
export class AccessError extends Error {
  /** `taxa`: 429 do orçamento por cliente ou da cota de contatos (a mensagem da API diz qual limite e quanto esperar).
   *  `limit`: orçamento anônimo das páginas avançadas esgotado (403 `anon_limit_reached` ou o 429 equivalente). */
  kind: 'login' | 'limit' | 'taxa'
  /** Segundos até poder tentar de novo, quando a API manda `Retry-After`. */
  retryAfter: number | null
  /** Motivo do 401 (`lista-expandida`, `historico`, `contatos`…), quando a API informa. */
  reason: string | null
  constructor(kind: 'login' | 'limit' | 'taxa', message: string, opts: { retryAfter?: number | null; reason?: string | null } = {}) {
    super(message)
    this.name = 'AccessError'
    this.kind = kind
    this.retryAfter = opts.retryAfter ?? null
    this.reason = opts.reason ?? null
  }
}

/** `Retry-After` em segundos (número ou data HTTP); sem cabeçalho, o `retry_after` do corpo do limitador. */
function segundosParaTentar(res: Response, body: { retry_after?: unknown } | null): number | null {
  const h = res.headers.get('Retry-After')
  if (h) {
    const n = Number(h)
    if (Number.isFinite(n) && n >= 0) return Math.ceil(n)
    const quando = Date.parse(h)
    if (Number.isFinite(quando)) return Math.max(0, Math.ceil((quando - Date.now()) / 1000))
  }
  return typeof body?.retry_after === 'number' && body.retry_after >= 0 ? Math.ceil(body.retry_after) : null
}

function checkAnonLimitHeader(res: Response): void {
  if (res.headers.get(ANON_LIMIT_HEADER) === 'true') {
    anonLimitListeners.forEach((cb) => cb())
  }
}

function baseHeaders(): Record<string, string> {
  return { [FINGERPRINT_HEADER]: getFingerprint(), [AREA_HEADER]: currentArea }
}

/** Converte respostas 401/403 de política em AccessError e notifica ouvintes. */
async function failure(res: Response): Promise<never> {
  const text = await res.text().catch(() => '')
  let body: { login_required?: boolean; anon_limit_reached?: boolean; reason?: string; detail?: unknown; retry_after?: unknown } | null = null
  try {
    body = text ? JSON.parse(text) : null
  } catch {
    body = null
  }
  // 401 da política (login_required) ou de uma rota protegida (require_user):
  // em ambos os casos a ação exige login — abre o modal em vez de exibir o JSON.
  if (res.status === 401) {
    const reason = body?.reason ?? (res.url.endsWith('/contacts') ? 'contatos' : null)
    loginRequiredListeners.forEach((cb) => cb(reason))
    throw new AccessError('login', 'Esta ação exige login. Entre para continuar.', { reason })
  }
  // O orçamento anônimo esgotado pode vir como 403 ou como 429 com Retry-After: as duas formas são o mesmo estado para a tela.
  const orcamentoEsgotado = !!body?.anon_limit_reached || res.headers.get(ANON_LIMIT_HEADER) === 'true'
  if ((res.status === 403 || res.status === 429) && orcamentoEsgotado) {
    anonLimitListeners.forEach((cb) => cb())
    throw new AccessError('limit', 'O tempo de uso das páginas avançadas sem login acabou. Entre para continuar.',
      { retryAfter: segundosParaTentar(res, body) })
  }
  if (res.status === 429) {
    const msg = typeof body?.detail === 'string' ? body.detail : 'Muitas consultas em pouco tempo. Tente novamente em instantes.'
    throw new AccessError('taxa', msg, { retryAfter: segundosParaTentar(res, body) })
  }
  throw new Error(`HTTP ${res.status}${text ? ': ' + text : ''}`)
}

async function get<T>(
  path: string,
  params?: Record<string, string | number | boolean | undefined>,
  signal?: AbortSignal,
): Promise<T> {
  const url = new URL(BASE + path, window.location.href)
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) url.searchParams.set(k, String(v))
    }
  }
  const res = await fetchComEspera(url.toString(), { credentials: 'include', headers: baseHeaders(), signal })
  checkAnonLimitHeader(res)
  if (!res.ok) return failure(res)
  // `opcional`: a API responde 204 em vez de 404 (sem erro no console do navegador); para quem chama continua sendo "HTTP 404".
  if (res.status === 204) throw new Error('HTTP 404: não encontrado')
  return res.json() as Promise<T>
}

/** Tentativas extras quando a API está ocupada (503 com `busy`, ver api/concurrency.py) e a espera mínima entre elas. */
export const BUSY_RETRIES = 3
export const BUSY_MIN_WAIT_MS = 1000

/**
 * `fetch` que, diante de 503 "servidor ocupado", espera o `Retry-After` (com piso e teto) e tenta de novo.
 * Sem isso uma rajada (a página de uma CDN pede um documento por ASN) mostrava "sem dados" onde bastava esperar a fila andar.
 * Só GET: reenviar um POST pode repetir efeito.
 */
export async function fetchComEspera(input: string, init: RequestInit): Promise<Response> {
  for (let tentativa = 0; ; tentativa++) {
    const res = await fetch(input, init)
    if (res.status !== 503 || tentativa >= BUSY_RETRIES) return res
    const corpo = await res.clone().json().catch(() => null) as { busy?: boolean } | null
    if (!corpo?.busy) return res
    const pedido = Number(res.headers.get('Retry-After')) * 1000
    const espera = Math.min(Math.max(Number.isFinite(pedido) ? pedido : 0, BUSY_MIN_WAIT_MS) + Math.random() * 500, 15000)
    await new Promise((r) => setTimeout(r, espera))
  }
}

async function post<T>(
  path: string,
  body: unknown,
  params?: Record<string, string | undefined>,
  signal?: AbortSignal,
): Promise<T> {
  const url = new URL(BASE + path, window.location.href)
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) url.searchParams.set(k, v)
    }
  }
  const res = await fetch(url.toString(), {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...baseHeaders() },
    body: JSON.stringify(body),
    signal,
  })
  checkAnonLimitHeader(res)
  if (!res.ok) return failure(res)
  return res.json() as Promise<T>
}

export function fetchHealth(): Promise<HealthResponse> {
  return get('/health')
}

/** Datas dos snapshots. Sem login (`completo` falso) vêm só as atuais, de `/brasil/snapshots` (entrada, aberta); com login, a lista inteira de
 *  `/snapshots`, que é da classe `login` (D9). Outra URL por quem pede, nunca a mesma resposta para níveis diferentes (cache por URL). */
export function fetchSnapshots(completo = false): Promise<SnapshotListResponse> {
  return get(completo ? '/api/v1/snapshots' : '/api/v1/brasil/snapshots')
}

/** Limites de uso em vigor (aberta, igual para todos): o quadro de /dados e o Sobre se montam daqui. */
export function fetchLimites(): Promise<Limites> {
  return get('/api/v1/limites')
}

/** Resumo e manifesto de um snapshot: aberto para as datas atuais, `login` para as anteriores (como `?date=` nas demais rotas). */
export function fetchSnapshot(date: string): Promise<SnapshotDetails> {
  return get(`/api/v1/brasil/snapshots/${date}`, { esquema: ESQUEMA_SNAPSHOT })
}
/** `esquema` 2: `sources[]` do manifesto ganhou `verificado_em`, `limite_dias` e `ativa` (PT-16). */
const ESQUEMA_SNAPSHOT = 2

/** Totais dos destaques da home e "O que mudou" na janela dos snapshots atuais: rota fixa e aberta (não gasta o orçamento anônimo). */
export interface DestaquesHome {
  snapshot_date: string
  destaques: Record<string, { total: number }>
  o_que_mudou: { total: number; de: string; mais_recente: string | null }
}
export function fetchDestaquesHome(date?: string): Promise<DestaquesHome> {
  return get('/api/v1/brasil/destaques', { date })
}

// `coleta` por família (ok, vazia, missing) e `status: partial` com a tabela vazia: a resposta de snapshot publicado mudou e o `?date=` é
// imutável no cache, então a URL muda junto.
/** `esquema` 3: a cobertura dos route servers em `rejeicoes` ganhou os campos do rodízio (PT-16). `esquema` 4: `/ixps` ganhou `route_servers`, `cdns_curados` e `interligacao` (PT-24). */
const ESQUEMA_IXPS = 4

export function fetchIXPs(date?: string, status?: string, uf?: string): Promise<IXPListResponse> {
  return get('/api/v1/ixps', { date, status, uf, esquema: ESQUEMA_IXPS })
}

export function fetchIXP(code: string, date?: string): Promise<IXPDocument> {
  return get(`/api/v1/ixps/${code}`, { date, esquema: ESQUEMA_IXPS })
}

/** Perfil consolidado do PTT: o documento mais membros (com nomes), usuários estimados, potencial, assinantes, a linha do índice e os totais do snapshot. */
export type IxpPerfil = IXPDocument & {
  membros?: IXPMembersResponse & { nomes?: Record<string, { name: string; uf?: string | null }> }
  usuarios_estimados?: IXPEstimatedUsers
  potencial?: IXPPotential | null
  assinantes?: IXPAssinantes | null
  indice?: IXPIndexEntry | null
  totais?: { total_asns_br: number | null; total_asns_global: number | null; br_apnic_users_total: number | null }
  historico?: HistoricoBloco | null
  route_servers?: RouteServersIxp | null
  rejeicoes?: RejeicoesIxp | null
  facilities?: FacilitiesPtt | null
  portas?: PortasIxp | null
}
/**
 * O bloco de histórico dos perfis: `historico` traz os 2 snapshots atuais, igual para todos; `historico_completo` traz a série inteira e
 * exige login (a API responde 401 ao anônimo). A resposta depende só da URL, então os caches por URL (nginx, API) não misturam os dois.
 */
export const blocoHistorico = (completo: boolean) => (completo ? 'historico_completo' : 'historico')

export function fetchIXPPerfil(code: string, date?: string, historicoCompleto = false): Promise<IxpPerfil> {
  return get(`/api/v1/ixps/${code}`, { date, esquema: ESQUEMA_IXPS, include: `membros,usuarios_estimados,potencial,assinantes,indice,totais,${blocoHistorico(historicoCompleto)},route_servers,rejeicoes,facilities,portas`, opcional: true })
}

/** Um acerto da busca universal. `url` é o caminho da página no site. */
export interface ItemBusca { tipo: string; titulo: string; detalhe: string; url: string; selo: string | null; motivo: string }
export interface GrupoBusca { tipo: string; rotulo: string; total: number; itens: ItemBusca[] }
export interface RespostaBusca { q: string; reconhecido: string[]; grupos: GrupoBusca[]; snapshot_date: string }
/**
 * Muda a URL da busca quando o índice muda de forma visível. Até a 2.0.21 a busca com `date` saía `immutable`, e o navegador guardava
 * por um ano o resultado da versão em que foi feita (o "nada encontrado" de antes da razão social). A API já não manda `immutable` nela;
 * este número só descarta o que ficou guardado. A API ignora o parâmetro.
 */
const ESQUEMA_BUSCA = 2

export function fetchBusca(q: string, opts: { limite?: number; date?: string } = {}): Promise<RespostaBusca> {
  return get('/api/v1/busca', { q, ...opts, esquema: ESQUEMA_BUSCA })
}

export function fetchASNs(opts: {
  date?: string
  page?: number
  limit?: number
  br_only?: boolean
  ipv6_only?: boolean
  q?: string
  sort_by?: string
  sort_desc?: boolean
  /** `bgp_stability` junta epppd/epppd_v4/epppd_v6 em cada item; `prontidao` junta prontidao_indice/classe quando a lista nominal está liberada. */
  include?: string
}): Promise<PaginatedASNs> {
  return get('/api/v1/asns', opts)
}

/** Documentos completos de até 100 ASNs numa chamada; `paths` junta os caminhos de cada um. */
export function fetchASNsLote(asns: Array<number | string>, opts: { date?: string; include?: string; fields?: string } = {}): Promise<ASNsLote> {
  return get('/api/v1/asns', { ...opts, asns: asns.join(',') })
}

/** Presença da CDN no Brasil: por PTT e família de IP (`ixp_peers`) e a série de PTTs com peering direto (`historico`), por ASN. */
export interface AsnCdnBrasil {
  asn: number
  ixp_peers?: Record<string, { v4?: { total_prefixes: number; own_prefixes: number }; v6?: { total_prefixes: number; own_prefixes: number } }>
  historico?: HistoricoBloco | null
}
export function fetchAsnCdnBrasil(asn: number | string, date?: string, historicoCompleto = false): Promise<AsnCdnBrasil> {
  return get(`/api/v1/asns/${asn}`, { date, include: `ixp_peers,${blocoHistorico(historicoCompleto)}` })
}

export function fetchASN(asn: number | string, date?: string): Promise<ASNDocument> {
  return get(`/api/v1/asns/${asn}`, { date })
}

/** Perfil consolidado do AS: o documento mais caminhos, pares nos PTTs diretos e estabilidade BGP, numa chamada. */
export type AsnPerfil = ASNDocument & {
  referencias?: import('../types/api').ReferenciasAsn | null
  paths?: ASNPathsResponse
  ixp_peers?: ASNIXPPeersResponse['peers']
  estabilidade?: import('../types/bgpStability').BgpStabilityAsn | null
  historico?: HistoricoBloco | null
  seguranca?: SegurancaAsn | null
  prontidao?: ProntidaoAsn | null
  route_servers?: RouteServersAsn | null
  politica_rs?: PoliticaAsn | null
  organizacao?: OrganizacaoAsn | null
  abuso?: AbusoAsn | null
  transito?: TransitoAsn | null
  bloqueios?: BloqueiosAsn | null
  radar?: RadarAsn | null
  exposicao?: ExposicaoAsn | null
  facilities?: FacilitiesAsn | null
  peering?: PeeringAsn | null
}
export function fetchASNPerfil(asn: number | string, date?: string, historicoCompleto = false): Promise<AsnPerfil> {
  return get(`/api/v1/asns/${asn}`, { date, include: `paths,ixp_peers,estabilidade,${blocoHistorico(historicoCompleto)},seguranca,prontidao,route_servers,politica_rs,organizacao,abuso,bloqueios,radar,exposicao,facilities,peering,transito,referencias`, opcional: true, esquema: ESQUEMA_INSTALACOES })
}

export function fetchASNContacts(asn: number | string, date?: string): Promise<ASNContactsResponse> {
  return get(`/api/v1/asns/${asn}/contacts`, { date })
}

export function fetchASNPaths(asn: number | string, date?: string): Promise<ASNPathsResponse> {
  return get(`/api/v1/asns/${asn}/paths`, { date })
}

export function fetchHilbertV4(date?: string): Promise<HilbertV4Data> {
  return get('/api/v1/hilbert/v4', { date })
}

export function fetchHilbertV6(date?: string): Promise<HilbertV6Data> {
  return get('/api/v1/hilbert/v6', { date })
}

export function fetchIXPMembers(code: string, date?: string): Promise<IXPMembersResponse> {
  return get(`/api/v1/ixps/${code}/members`, { date })
}

export function fetchIXPPeers(code: string, afi: 'v4' | 'v6', date?: string): Promise<IXPPeersResponse> {
  // as portas e instalações do PeeringDB vêm junto (o mesmo pedido serve às duas tabelas de participantes)
  return get(`/api/v1/ixps/${code}/peers`, { afi, date, peeringdb: 1 })
}

export interface IXPEstimatedUsers {
  snapshot_date: string
  ixp: string
  afi: string
  estimated_users: number
  contributing_asns: number
}

export function fetchIXPEstimatedUsers(code: string, date?: string): Promise<IXPEstimatedUsers> {
  return get(`/api/v1/ixps/${code}/estimated-users`, { date })
}

export interface IXPPotential {
  snapshot_date: string
  ixp: string
  nearby_asn_count: number
  v4_prefixes_24: number
  v6_prefixes_48: number
  estimated_users_total: number
}

export function fetchIXPPotential(code: string, date?: string): Promise<IXPPotential> {
  return get(`/api/v1/ixps/${code}/potential`, { date })
}

export interface IXPAssinantesAsn {
  cnpj: string | null
  empresa: string | null
  has_scm: boolean
  has_smp: boolean
  has_stfc: boolean
  has_seac: boolean
  usuarios_apnic: number | null
  assinantes_diretos: number
}

export interface IXPAssinantesMunicipio {
  ibge: string
  nome: string
  uf: string
  acessos: number
}

export interface IXPAssinantes {
  mes_referencia: string
  /** ASN (string) → empresa, outorgas, APNIC e assinantes do próprio CNPJ */
  asns: Record<string, IXPAssinantesAsn>
  /** AFI → ASN (string) → assinantes totais (peer + clientes nos AS-paths) */
  peers: { v4: Record<string, number>; v6: Record<string, number> }
  assinantes_diretos: number
  assinantes_total: number
  municipios_diretos: IXPAssinantesMunicipio[]
  municipios_totais: IXPAssinantesMunicipio[]
}

export function fetchIXPAssinantes(code: string, date?: string): Promise<IXPAssinantes> {
  return get(`/api/v1/ixps/${code}/assinantes`, { date })
}

export interface AllIXPEstimatedUsers {
  snapshot_date: string
  afi: string
  ixps: Record<string, number>
}

export function fetchAllIXPEstimatedUsers(date?: string): Promise<AllIXPEstimatedUsers> {
  return get(`/api/v1/ixps/estimated-users`, { date })
}

/** Batch: stats de peering deste AS em todos os seus IXPs diretos (1 request). */
export function fetchASNIXPPeers(asn: number, date?: string): Promise<ASNIXPPeersResponse> {
  return get(`/api/v1/asns/${asn}/ixp-peers`, { date })
}

export function fetchIXPHilbert(code: string, peer?: number, date?: string): Promise<IXPHilbertData> {
  return get(`/api/v1/ixps/${code}/hilbert/v4`, { peer, date })
}

export function fetchIXPHilbertV6(code: string, peer?: number, date?: string): Promise<IXPHilbertV6Data> {
  return get(`/api/v1/ixps/${code}/hilbert/v6`, { peer, date })
}

export function fetchIXPHilbertV4Detail(
  code: string,
  slash8: number,
  peer?: number,
  date?: string,
): Promise<IXPHilbertV4DetailData> {
  return get(`/api/v1/ixps/${code}/hilbert/v4/detail`, { slash8, peer, date })
}

export function fetchHilbertV4Detail(
  slash8: number,
  layer: string,
  date?: string,
): Promise<HilbertV4DetailLayer> {
  return get('/api/v1/hilbert/v4/detail', { slash8, layer, date })
}

export function fetchExternalIXPs(date?: string, country?: string): Promise<ExternalIXPListResponse> {
  return get('/api/v1/external-ixps', { date, country })
}

export function fetchExternalIXP(code: string, date?: string, br_only?: boolean): Promise<ExternalIXPDocument> {
  return get(`/api/v1/external-ixps/${code}`, { date, br_only, opcional: true })
}

export function fetchIXPCompareMembers(ixps: string[], date?: string): Promise<IXPCompareMembersResponse> {
  return get('/api/v1/ixp-compare/members', { ixps: ixps.join(','), date })
}

/** `esquema` 2: cada CDN ganhou `ixbr_rs`, `ixbr_sem_rs`, `ixbr_origem` e `ixbr_sem_coleta` (PT-24). */
const ESQUEMA_CDNS = 2
export function fetchCDNPresence(date?: string): Promise<CDNPresenceResponse> {
  return get('/api/v1/cdns/presence', { date, esquema: ESQUEMA_CDNS })
}

/** Nomes só dos ASNs pedidos (até 500 por chamada; o hook `useAsnNomes` divide em lotes). */
export function fetchAsnNomes(asns: number[], date?: string): Promise<{ snapshot_date: string; names: Record<string, string> }> {
  return get('/api/v1/asns/names', { date, asns: asns.join(',') })
}

export function fetchAsnNames(date?: string): Promise<{ snapshot_date: string; names: Record<string, string> }> {
  return get('/api/v1/asns/names', { date })
}

export type IXPGeoLayer =
  | 'asns_members'
  | 'asns_direct'
  | 'asns_origin'
  | 'prefixes_v4'
  | 'prefixes_v6'

export interface IXPGeoFeature {
  type: 'Feature'
  geometry: { type: 'Point'; coordinates: [number, number] }
  properties: {
    // camadas de ASN
    asn?: number
    name?: string
    geo_confidence?: string
    // camadas de prefixo
    block_count?: number
    block_unit?: string
    // comuns
    city?: string
    uf?: string
    country?: string
  }
}

export interface IXPGeoResponse {
  type: 'FeatureCollection'
  features: IXPGeoFeature[]
  snapshot_date: string
  ixp_code: string
  layer: IXPGeoLayer
  layer_description: string
  ixp_pix?: Array<{ name: string; lat?: number; lon?: number }>
}

export function fetchIXPGeo(
  code: string,
  layer: IXPGeoLayer,
  date?: string,
): Promise<IXPGeoResponse> {
  return get(`/api/v1/ixps/${code}/geo`, { layer, date })
}

export type ASNGeoLayer = 'fulltable_v4' | 'fulltable_v6' | 'ixp_v4' | 'ixp_v6'

export interface ASNGeoFeature {
  type: 'Feature'
  geometry: { type: 'Point'; coordinates: [number, number] }
  properties: {
    role: 'own' | 'downstream'
    direct?: boolean
    ixp_code?: string
    city?: string
    uf?: string
    country?: string
    block_count?: number
    block_unit?: string
  }
}

export interface ASNGeoResponse {
  type: 'FeatureCollection'
  features: ASNGeoFeature[]
  snapshot_date: string
  asn: number
  layer: ASNGeoLayer
  layer_description: string
  ixp_pix?: Array<{ ixp_code: string; name: string; lat: number; lon: number }>
}

export interface HomeMapFeature {
  type: 'Feature'
  geometry: { type: 'Point'; coordinates: [number, number] }
  properties: {
    role: 'asn' | 'pix'
    // ASN fields
    asn?: number
    name?: string
    city?: string
    uf?: string
    visibility?: 'both' | 'v4_only' | 'v6_only' | 'none'
    // PIX fields
    ixp_code?: string
    ixp_name?: string
  }
}

export interface HomeMapResponse {
  type: 'FeatureCollection'
  features: HomeMapFeature[]
  snapshot_date: string
}

export function fetchHomeMap(date?: string): Promise<HomeMapResponse> {
  return get('/api/v1/map/asns-overview', { date })
}

// ---------------------------------------------------------------------------
// Mapa Explorer
// ---------------------------------------------------------------------------

export interface MapQueryNear {
  ixp?: string
  place?: string
  point?: [number, number]
  radius_km: number
}

export interface MapQueryNearIx {
  code: string
  afi?: 'v4' | 'v6'
  exclude_asns?: number[]
  include_asns?: number[]
}

export interface MapQueryBody {
  filter?: Record<string, unknown>
  near?: MapQueryNear
  near_prefixes?: MapQueryNear
  near_ix?: MapQueryNearIx
  layers?: string[]
  color_by?: string
  ix_code?: string
  ix_afi?: 'v4' | 'v6'
  ix_exclude_asns?: number[]
  ix_include_asns?: number[]
  ix_apply_filter?: boolean
  scm_mode?: 'todas' | 'com_asn' | 'sem_asn'
}

export interface MapQueryFeature {
  type: 'Feature'
  geometry: { type: 'Point'; coordinates: [number, number] }
  properties: {
    layer: string
    // asns_geo / asns_ix_*
    asn?: number
    name?: string
    uf?: string
    city?: string
    color_value?: string | number | null
    // export fields (asn layers)
    has_rpki?: boolean | null
    has_aspa?: boolean | null
    porte?: string
    pct_v6?: number | null
    ixps_direct?: string    // comma-separated list
    has_scm?: boolean       // AS com outorga SCM (color_by="outorga")
    // scms (outorga SCM sem ASN) / outorgas_scm (todas)
    asns?: number[]
    cnpj?: string
    razao_social?: string
    nome_fantasia?: string
    municipio?: string
    situacao?: string
    has_asn?: boolean
    // prefixes (BR)
    prefix?: string
    ip_version?: number
    origin_asn?: number
    origin_cnpj?: string | null
    origin_name?: string | null
    // prefixes (PTT / BR aggregated)
    block_count?: number
    block_unit?: string
    origin_asns?: number[]
    peer_asns?: number[]
    // pix
    ixp_code?: string
    ixp_name?: string
    // geo
    country?: string
    geo_confidence?: string
  }
}

export interface MapQueryResponse {
  type: 'FeatureCollection'
  features: MapQueryFeature[]
  snapshot_date: string
  // null quando nenhuma camada pedida depende do recorte de ASes
  matched_asns: number | null
}

/** GET de um caminho da API com parâmetros (cartões da página inicial). Mesmo tratamento de login e limite das demais chamadas. */
export function fetchCaminho<T = unknown>(caminho: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  return get(caminho, params)
}

/** Corpo maior que isto (codificado na URL) vai pelo POST: o nginx aceita linhas de requisição de ~8 KB, e a API aceita no GET até
 * 5.120 caracteres de corpo (`_MAX_CORPO_GET`, api/routes/query.py). Codificado ≤ 5.000 garante decodificado ≤ 5.000. */
export const MAX_CORPO_NA_URL = 5000

/** `esquema` 2: a agregação respeita `sort`, `limit` e `page` e traz `total_grupos`; `mes_referencia` em `municipios` e `acessos_municipio`
 * (PT-19). A URL com `date` sai `immutable` por um ano: sem o parâmetro novo, o navegador e o nginx serviriam a resposta antiga. */
const ESQUEMA_QUERY = 2

/**
 * Consulta genérica de uma collection (mesmo motor do MCP): filtro, agregação, ordenação e paginação — ver `GET /api/v1/schema`.
 * Vai por GET (`?corpo=<JSON>`), que o navegador, o nginx e a API guardam: as perguntas prontas da página inicial são as mesmas para todo
 * visitante e, por POST, eram recalculadas a cada visita (no teste de carga de 2026-11-21, os travamentos na chegada de visitantes novos).
 * Corpo grande demais para uma URL vai pelo POST.
 */
export function queryColecao<T = unknown>(collection: string, body: Record<string, unknown>, date?: string, signal?: AbortSignal): Promise<T> {
  const corpo = JSON.stringify(body)
  if (encodeURIComponent(corpo).length > MAX_CORPO_NA_URL) {
    return post(`/api/v1/query/${collection}`, body, date ? { date } : undefined, signal)
  }
  return get(`/api/v1/query/${collection}`, { corpo, date, esquema: ESQUEMA_QUERY }, signal)
}

export function fetchMapQuery(body: MapQueryBody, date?: string, signal?: AbortSignal): Promise<MapQueryResponse> {
  return post('/api/v1/map/query', body, date ? { date } : undefined, signal)
}

/** `esquema` 2: a resposta ganhou `chave` e o modo por raiz de CNPJ (PT-09, D5). */
const ESQUEMA_ORGANIZACOES = 2

export function fetchAsnsPorOrganizacao(date?: string, limit = 30, chave: 'cnpj' | 'raiz' = 'cnpj'): Promise<AsnsPorOrganizacaoResponse> {
  return get('/api/v1/asns/by-organization', { date, limit, chave, esquema: ESQUEMA_ORGANIZACOES })
}

export function fetchASNGeo(
  asn: number | string,
  layer: ASNGeoLayer,
  date?: string,
): Promise<ASNGeoResponse> {
  return get(`/api/v1/asns/${asn}/geo`, { layer, date })
}

export function fetchRpkiSummary(date?: string): Promise<RpkiSummary> {
  return get('/api/v1/rpki/summary', { date })
}

// ---------------------------------------------------------------------------
// SCM — Outorgas Anatel
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// SICI — Acessos de banda larga (Anatel)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Outorgas da Anatel — contrato unificado: SCM, SMP, STFC e SeAC
// ---------------------------------------------------------------------------

export type ServicoOutorga = 'SCM' | 'SMP' | 'STFC' | 'SeAC'

/** `GET /outorgas`: uma linha por CNPJ. `servico` aceita vários (qualquer um; `todos` exige todos). */
export function fetchOutorgas(opts: {
  date?: string
  page?: number
  limit?: number
  servico?: ServicoOutorga[]
  todos?: boolean
  uf?: string
  municipio?: string
  q?: string
  com_asn?: boolean
  ativo?: boolean
  porte?: string
  min_acessos?: number
  sort_by?: string
  sort_desc?: boolean
}): Promise<PaginatedOutorgas> {
  const { servico, todos, ...resto } = opts
  return get('/api/v1/outorgas', { ...resto, ...(servico?.length ? { servico: servico.join(',') } : {}), ...(todos ? { todos: true } : {}), esquema: ESQUEMA_VINCULO_ASN })
}

/** Totais e quebras de um serviço (`GET /outorgas/stats?servico=`); o corpo de cada serviço tem o seu tipo. */
export interface EstatisticasDe { SCM: SCMStats; SMP: SMPStats; STFC: STFCStats; SeAC: SEACStats }
export function fetchOutorgasStats<S extends ServicoOutorga>(servico: S, date?: string): Promise<EstatisticasDe[S]> {
  return get('/api/v1/outorgas/stats', { date, servico })
}

/** GeoJSON das outorgas de um serviço (`GET /outorgas/map`). */
export function fetchOutorgasMapa(servico: ServicoOutorga, opts: { date?: string; uf?: string; com_asn?: boolean } = {}): Promise<{ type: string; features: unknown[]; snapshot_date: string }> {
  return get('/api/v1/outorgas/map', { ...opts, servico })
}

export function fetchAcessosStats(date?: string, top = 20): Promise<SiciStats> {
  return get('/api/v1/acessos/stats', { date, top })
}

/** `esquema` 2: respostas com o vínculo ASN ↔ CNPJ da decisão D5 (`asn_vinculo`, `asns_vinculados`, rede e grupos pela raiz do CNPJ, `com_asn`
 *  pela raiz e pela marca). O mesmo `?date=` servia a versão antiga do cache imutável. */
const ESQUEMA_VINCULO_ASN = 2

/** `esquema` 3 nas rotas de grupo: o grupo só se forma por sócio com participação, tem `nome` por regra visível, `grupo_id` estável (menor CNPJ básico; id antigo
 *  redireciona) e `grupo_societario` na resposta de `/grupos/empresa`. `esquema` 4 (P8): S.A. com `grupo_inferivel: false`, `grupo_inferivel_rotulo` e `como_ler`
 *  (o quadro da Receita de S.A. não traz acionistas). O mesmo `?date=` servia a versão antiga do cache imutável. */
const ESQUEMA_GRUPOS = 4

/** Perfil consolidado da operadora (SCM, SMP, STFC e SeAC, ASNs e rede) numa chamada; 204 = CNPJ sem informação. */
export function fetchOperadoraPerfil(cnpj: string, date?: string, historicoCompleto = false): Promise<PerfilOperadora | null> {
  return get(`/api/v1/operadoras/${cnpj}`, { date, include: `${blocoHistorico(historicoCompleto)},indicadores,erbs,multas,prontidao,qualidade,reclamacoes,consumidor,mercado_grupos`, opcional: true, esquema: ESQUEMA_GRUPOS })
}

export function fetchOperadoraContacts(cnpj: string, date?: string): Promise<OperadoraContactsResponse> {
  return get(`/api/v1/acessos/operadora/${cnpj}/contacts`, { date })
}

export function fetchGruposSocietarios(date?: string): Promise<GrupoSocietarioListResponse> {
  return get('/api/v1/grupos', { date, esquema: ESQUEMA_GRUPOS })
}

export function fetchEmpresasRelacionadas(cnpj: string, date?: string): Promise<EmpresasRelacionadasResponse> {
  return get(`/api/v1/grupos/empresa/${cnpj}`, { date, esquema: ESQUEMA_GRUPOS })
}

export interface GrupoPrefixoGeoFeature {
  type: 'Feature'
  geometry: { type: 'Point'; coordinates: [number, number] }
  properties: { afi: 'v4' | 'v6'; city?: string; uf?: string; block_count?: number }
}

export interface GrupoPrefixosGeoResponse {
  type: 'FeatureCollection'
  features: GrupoPrefixoGeoFeature[]
  snapshot_date: string
  grupo_id: string
}

export function fetchGrupo(grupoId: string, date?: string): Promise<GrupoDetalhe> {
  return get(`/api/v1/grupos/${encodeURIComponent(grupoId)}`, { date, opcional: true, esquema: ESQUEMA_GRUPOS })
}

/** Um bloco extra do grupo: `mercado` → `mercado_fixo`, `regulatorio`, `tecnico`. Cada aba busca o seu quando abre. */
export async function fetchGrupoBloco<T>(grupoId: string, include: 'mercado' | 'regulatorio' | 'tecnico' | 'relacoes', date?: string): Promise<T | null> {
  const r = await get<Record<string, unknown>>(`/api/v1/grupos/${encodeURIComponent(grupoId)}`, { date, include, esquema: ESQUEMA_GRUPOS })
  return (r[include === 'mercado' ? 'mercado_fixo' : include] as T | null | undefined) ?? null
}

/** O grupo com mercado, regulatório e técnico numa chamada só, para o comparador. */
export async function fetchGrupoComparavel(grupoId: string, date?: string): Promise<import('../features/comparar/entidades').GrupoComparavel> {
  const r = await get<GrupoDetalhe & { mercado_fixo?: import('../types/api').GrupoMercadoFixo | null; regulatorio?: import('../types/api').GrupoRegulatorio | null; tecnico?: import('../types/api').GrupoTecnico | null }>(
    `/api/v1/grupos/${encodeURIComponent(grupoId)}`, { date, include: 'mercado,regulatorio,tecnico', esquema: ESQUEMA_GRUPOS })
  const { mercado_fixo, regulatorio, tecnico, ...grupo } = r
  return { grupo: grupo as GrupoDetalhe, mercado: mercado_fixo ?? null, regulatorio: regulatorio ?? null, tecnico: tecnico ?? null }
}

export const fetchGrupoMercado = (grupoId: string, date?: string) => fetchGrupoBloco<import('../types/api').GrupoMercadoFixo>(grupoId, 'mercado', date)

export function fetchGrupoPrefixosGeo(grupoId: string, date?: string): Promise<GrupoPrefixosGeoResponse> {
  return get(`/api/v1/grupos/${grupoId}/prefixos-geo`, { date, esquema: ESQUEMA_GRUPOS })
}

export function fetchMunicipioAcessos(
  ibge: string, date?: string,
): Promise<SiciMunicipioDetalhe> {
  return get(`/api/v1/acessos/municipio/${ibge}`, { date, opcional: true })
}

/** Perfil consolidado do município (fixo, móvel, centróide e PTTs mais próximos) numa chamada. */
export function fetchMunicipioPerfil(ibge: string, date?: string): Promise<PerfilMunicipio> {
  return get(`/api/v1/municipios/${ibge}`, { date, include: 'indicadores,territorio,erbs,fust,qualidade,reclamacoes,consumidor,serie_mercado,mercado_grupos,rede_territorio', opcional: true, esquema: ESQUEMA_GRUPOS })
}

/** ASNs de um conjunto de municípios: provedores, participação nos PTTs, trânsito e carregadores. Até 50 códigos IBGE. */
export function fetchRegiao(ibges: string[], date?: string): Promise<Regiao> {
  return get('/api/v1/regiao', { date, ibges: ibges.join(',') })
}

/** Cadastro da operadora: matriz, estabelecimentos e presença física por município. `opcional`: 204 (sem erro no console) se a raiz não tem cadastro de telecom. */
export function fetchCadastroOperadora(cnpj: string, date?: string): Promise<CadastroOperadora> {
  return get(`/api/v1/empresas/operadoras/${cnpj}`, { date, opcional: true })
}

/** Crédito público e sanções da operadora. `opcional`: 204 (sem erro no console) se a raiz não tem registro nas duas fontes. */
export function fetchFinanciamentoOperadora(cnpj: string, date?: string): Promise<FinanciamentoOperadora> {
  return get(`/api/v1/financiamento/operadoras/${cnpj}`, { date, opcional: true })
}

/** Contratos públicos da operadora (PNCP). `opcional`: 204 (sem erro no console) se a raiz ainda não foi lida pelo rodízio. */
export function fetchContratosOperadora(cnpj: string, date?: string): Promise<ContratosOperadora> {
  return get(`/api/v1/contratos/operadoras/${cnpj}`, { date, opcional: true })
}

/** Operadoras com contratação de órgão sediado no município. `opcional`: 204 se não há contratação nas leituras. */
export function fetchContratosMunicipio(ibge: string, date?: string): Promise<ContratosMunicipio> {
  return get(`/api/v1/contratos/municipios/${ibge}`, { date, opcional: true })
}

/** Empresas de telecom da UF: entradas e baixas por ano e as ativas. */
export function fetchCadastroMercadoUf(uf: string, date?: string): Promise<CadastroMercadoUf> {
  return get('/api/v1/empresas/mercado', { date, uf, opcional: true })
}

/** Resumo das 27 UFs (acessos, fibra, usuários estimados, PTTs) para a página /estados. */
/** `GET /territorio/mapa`: um indicador normalizado de todos os municípios, `{ibge: valor}`; município sem dado fica de fora. */
export interface TerritorioMapa {
  snapshot_date: string; mes_referencia_sici: string; censo_ano: string; pnad_ano: string; indicador: string; rotulo: string; normalizacao: string; total: number
  limites: string; fonte: string; valores: Record<string, number>
}
export function fetchTerritorioMapa(indicador: string, date?: string): Promise<TerritorioMapa> {
  return get('/api/v1/territorio/mapa', { indicador, date })
}

// `ptts` passou a contar os PTTs do snapshot com ou sem coleta (+ `ptts_com_coleta`) e acessos/municípios sem SICI saem `null`; o `?date=`
// é imutável no cache: subir quando a resposta de `/ufs` ou `/ufs/{uf}` mudar para um snapshot já publicado.
const ESQUEMA_UFS = 2

export function fetchUfs(date?: string): Promise<{ snapshot_date: string; mes_referencia?: string | null; total: number; items: ResumoUf[] }> {
  return get('/api/v1/ufs', { date, esquema: ESQUEMA_UFS })
}

/** Perfil consolidado da UF numa chamada. */
/** Sobe quando o corpo de `/ufs/{uf}` muda (2: `operadoras_presentes`, UF-E2): a URL com `date` é imutável no cache. */
const ESQUEMA_UF = 2
export function fetchUfPerfil(uf: string, date?: string, historicoCompleto = false): Promise<PerfilUf> {
  return get(`/api/v1/ufs/${uf}`, { date, esquema: ESQUEMA_UF, include: `${blocoHistorico(historicoCompleto)},territorio,cetic,erbs,fust,prontidao,qualidade,reclamacoes,consumidor,transito,radar,exposicao,mercado_grupos,rede_territorio` })
}

export function fetchAcessosMunicipios(opts: {
  date?: string; uf?: string; q?: string
  sort_by?: string; sort_desc?: boolean; limit?: number
}): Promise<{ snapshot_date: string; mes_referencia: string; total: number
              items: (SiciMunicipioRow & { operadores: number; hhi: number
                                           share_maior: number })[] }> {
  return get('/api/v1/acessos/municipios', opts)
}

export function fetchAcessosMunicipiosMapa(date?: string): Promise<SiciMunicipiosMapaResponse> {
  return get('/api/v1/acessos/municipios/mapa', { date })
}

export function fetchDivergenciasSCM(opts: {
  date?: string; limit?: number; ordem?: string; asc?: boolean
}): Promise<SiciDivergenciasSCMResponse> {
  return get('/api/v1/acessos/divergencias/scm', opts)
}

export function fetchASNAcessos(asn: number, date?: string): Promise<SiciAcessos> {
  return get(`/api/v1/asns/${asn}/acessos`, { date, opcional: true })
}

export function fetchASNAcessosMunicipios(
  asn: number, date?: string,
): Promise<SiciAsnMunicipios> {
  return get(`/api/v1/asns/${asn}/acessos/municipios`, { date })
}

// ---------------------------------------------------------------------------
// SMP — Outorgas Anatel (Serviço Móvel Pessoal)
// ---------------------------------------------------------------------------


// ---------------------------------------------------------------------------
// STFC — Outorgas Anatel
// ---------------------------------------------------------------------------


// ---------------------------------------------------------------------------
// SEAC — Outorgas Anatel
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// SICI móvel — Acessos de telefonia móvel (SMP, Anatel)
// ---------------------------------------------------------------------------

export function fetchAcessosMovelStats(date?: string, top = 20): Promise<SiciMovelStats> {
  return get('/api/v1/acessos/stats', { date, top, servico: 'movel' })
}

export function fetchOperadorasMovel(opts: {
  date?: string
  page?: number
  limit?: number
  uf?: string
  q?: string
  com_asn?: boolean
  ativo?: boolean
  min_acessos?: number
  sort_by?: string
  sort_desc?: boolean
}): Promise<PaginatedOperadorasMovel> {
  return get('/api/v1/acessos/operadoras', { ...opts, servico: 'movel' })
}

export function fetchOperadoraMovelContacts(cnpj: string, date?: string): Promise<OperadoraContactsResponse> {
  return get(`/api/v1/acessos/operadora/${cnpj}/contacts`, { date, servico: 'movel' })
}

export function fetchMunicipioAcessosMovel(
  ibge: string, date?: string,
): Promise<MovelMunicipioDetalhe> {
  return get(`/api/v1/acessos/municipio/${ibge}`, { date, servico: 'movel', opcional: true })
}

export function fetchAcessosMovelMunicipios(opts: {
  date?: string; uf?: string; q?: string
  sort_by?: string; sort_desc?: boolean; limit?: number
}): Promise<{ snapshot_date: string; mes_referencia: string; total: number
              items: Array<{ ibge: string; nome: string; uf: string; acessos: number
                             pf: number; pj: number; operadores: number; hhi: number
                             share_maior: number }> }> {
  return get('/api/v1/acessos/municipios', { ...opts, servico: 'movel' })
}

// ---------------------------------------------------------------------------
// Camadas GeoJSON de mapa (datadas — incluir date no queryKey)
// ---------------------------------------------------------------------------

export interface GeoJSONFeatureCollection {
  type: 'FeatureCollection'
  features: Array<{
    type: 'Feature'
    geometry: { type: string; coordinates: unknown }
    properties: Record<string, unknown>
  }>
  snapshot_date?: string
}

export function fetchMapAsns(date?: string): Promise<GeoJSONFeatureCollection> {
  return get('/api/v1/map/asns', { date })
}

export function fetchMapPrefixes(date?: string): Promise<GeoJSONFeatureCollection> {
  return get('/api/v1/map/prefixes', { date })
}

/** Um ROA (VRP) que cobre o prefixo, de qualquer AS; `autoriza_origem` nulo quando não há origem observada. */
export interface RoaQueCobre { prefix: string; asn: number; maxLength: number; ta: string; autoriza_origem: boolean | null }

/** Validação de origem (RFC 6811) do par prefixo × origem observada; `nao_avaliado` quando o prefixo não é anunciado. */
export interface RpkiObservado {
  estado: 'valid' | 'invalid' | 'not_found' | 'nao_avaliado'
  motivo: 'origem_diferente' | 'maxlength_excedido' | 'sem_roa' | 'sem_anuncio' | null
  asn: number | null
  roas_que_cobrem: RoaQueCobre[]
}

export interface PrefixoInfo {
  prefix: string
  /** A grafia pedida, quando difere da canônica. */
  prefixo_informado?: string
  ip_version: 4 | 6
  /** Depreciado: é o AS do Registro.br (= `registro_asn`), não a origem observada. */
  origin_asn: number | null
  escopo?: 'alocacao_registro_br' | 'rota_dentro_de_alocacao' | 'fora_do_registro_br' | 'registro_br_indisponivel'
  /** Alocação do Registro.br igual ao prefixo ou que o contém. */
  alocacao_registro_br?: string | null
  /** Detentor: AS a que o Registro.br associa a alocação. */
  registro_asn?: number | null
  registro_asn_nome?: string | null
  /** Último AS do caminho na tabela global coletada (ou nos route servers do IX.br); nulo sem anúncio. */
  observed_origin_asn?: number | null
  observed_origin_nome?: string | null
  observed_origin_fonte?: 'tabela_global' | 'route_servers_ixbr' | null
  rpki_observado?: RpkiObservado | null
  uf?: string | null
  country?: string | null
  geo_confidence?: string | null
  geo_source?: string | null
  snapshot_date: string
  geo_org: { name?: string; cnpj?: string; city?: string; uf?: string; municipio?: string; geo_confidence?: string; geo_source?: string } | null
}

/** Um prefixo (`GET /prefixes/{prefix}`): alocação do Registro.br ou rota observada; 404 se não é nenhum dos dois neste snapshot, 422 se a grafia não é CIDR. A barra do CIDR fica no caminho. */
export function fetchPrefix(prefix: string, date?: string): Promise<PrefixoInfo> {
  return get(`/api/v1/prefixes/${prefix}`, { date })
}

/** Resultado de `GET /prefixes/lookup`: consulta de roteamento, sem posição nenhuma. */
export interface PrefixoDoIp { prefix: string; ip_version: 4 | 6; origin_asn: number | null; registro_asn?: number | null; observed_origin_asn?: number | null; snapshot_date: string; consulta: string }

/** Prefixo mais específico que contém o IP (`GET /prefixes/lookup`); 404 se nenhum prefixo conhecido o contém. */
export function fetchPrefixDoIp(ip: string, date?: string): Promise<PrefixoDoIp> {
  return get('/api/v1/prefixes/lookup', { ip, date })
}

export function fetchMapPix(date?: string): Promise<GeoJSONFeatureCollection> {
  return get('/api/v1/map/pix', { date })
}

export interface IXPresenceResponse {
  snapshot_date: string
  asns: Record<string, { m: string[]; o: string[] }>
}

export function fetchIXPresence(date?: string): Promise<IXPresenceResponse> {
  return get<IXPresenceResponse>('/api/v1/asns/ix-presence', { date })
}

export interface ResolvePlaceResult {
  snapshot_date: string
  place: string
  /** Nulos quando o nome existe em mais de uma UF e nenhuma foi dada (`ambiguo`). */
  lat: number | null
  lon: number | null
  n: number
  uf?: string
  /** Homônimos sem UF (LOC-E4): `ufs` = organizações por UF; informe "Nome/UF". */
  ambiguo?: boolean
  ufs?: Record<string, number>
}

export function fetchResolvePlace(q: string, date?: string): Promise<ResolvePlaceResult> {
  return get<ResolvePlaceResult>('/api/v1/resolve/place', { q, date })
}

// ---------------------------------------------------------------------------
// Auth — usa credentials: 'include' para enviar cookies em cross-origin
// ---------------------------------------------------------------------------

export interface AnonInfo {
  activeSeconds: number
  limitSeconds: number
  limitReached: boolean
  heartbeatIntervalSeconds: number
  inactivityTimeoutSeconds: number
}

function anonInfoFromApi(raw: {
  active_seconds: number
  limit_seconds: number
  limit_reached: boolean
  heartbeat_interval_seconds: number
  inactivity_timeout_seconds: number
} | null | undefined): AnonInfo | null {
  if (!raw) return null
  return {
    activeSeconds: raw.active_seconds,
    limitSeconds: raw.limit_seconds,
    limitReached: raw.limit_reached,
    heartbeatIntervalSeconds: raw.heartbeat_interval_seconds,
    inactivityTimeoutSeconds: raw.inactivity_timeout_seconds,
  }
}

export interface AuthMeResponse {
  authenticated: boolean
  email?: string | null
  name?: string
  provider?: string
  anon: AnonInfo | null
}

export async function fetchAuthMe(): Promise<AuthMeResponse | null> {
  try {
    const url = new URL(BASE + '/auth/me', window.location.href)
    const res = await fetch(url.toString(), {
      credentials: 'include',
      headers: baseHeaders(),
    })
    checkAnonLimitHeader(res)
    if (!res.ok) return null
    const data = await res.json()
    return {
      authenticated: !!data.authenticated,
      email: data.email,
      name: data.name,
      provider: data.provider,
      anon: anonInfoFromApi(data.anon),
    }
  } catch {
    return null
  }
}

/** Heartbeat de sessão anônima — chamado periodicamente pelo frontend só
 * enquanto a aba está visível e houve interação recente (ver useAnonHeartbeat
 * em AuthContext.tsx). Usuários autenticados/isentos recebem anon=null. */
export async function postHeartbeat(): Promise<AnonInfo | null> {
  try {
    const url = new URL(BASE + '/auth/heartbeat', window.location.href)
    const res = await fetch(url.toString(), {
      method: 'POST',
      credentials: 'include',
      headers: baseHeaders(),
    })
    checkAnonLimitHeader(res)
    if (!res.ok) return null
    const data = await res.json()
    return anonInfoFromApi(data.anon)
  } catch {
    return null
  }
}

/**
 * Muda a URL quando a resposta muda sem a data mudar. 2: as listas de AS_PATH (prepending e upstreams) passaram a trazer o topo de cada
 * coluna ordenável (2.0.28), inclusive no snapshot de 2026-11-15, corrigido no lugar; a URL antiga fica `immutable` no navegador e na borda.
 * 3: `moas` passou a vir nulo, com `moas_indisponivel`, em todas as datas (a coleta guarda uma origem por prefixo).
 * 4: rota brasileira só por prefixo em bloco do Registro.br; `pbr_composition` com `total` e `asn_br_fora_de_bloco` (D4).
 * 5: `moas` volta como lista (prefixos brasileiros com origens e coletores) e `moas_resumo`, nos snapshots com `origins-multi`.
 */
const ESQUEMA_ROUTING_ANALYSIS = 5

export function fetchRoutingAnalysis(date?: string): Promise<RoutingAnalysis> {
  return get('/api/v1/routing-analysis', { date, esquema: ESQUEMA_ROUTING_ANALYSIS })
}

export function fetchBgpStability(date?: string): Promise<import('../types/bgpStability').BgpStability> {
  return get('/api/v1/bgp-stability', { date })
}

/** Resumo leve (eventos/prefixo/dia por AS) — usado na lista de ASes no lugar do
 * documento completo de ~40 MB. */
export interface BgpStabilitySummary {
  snapshot_date: string
  items: { asn: number; epppd: number | null; epppd_v4: number | null; epppd_v6: number | null }[]
}

/** Estabilidade BGP de um AS (snapshot ativo, diagnóstico e séries horárias das últimas semanas) numa chamada — 1.4.2.1. */
export function fetchBgpStabilityAsn(asn: number, date?: string, weeks = 6): Promise<import('../types/bgpStability').BgpStabilityAsn> {
  return get(`/api/v1/bgp-stability/asn/${asn}`, { date, weeks })
}

/** Visão geral da estabilidade (dezenas de KB) para a página `/bgp`; o documento completo (~46 MB) só para a lista "Ver todos". */
export function fetchBgpStabilityVisaoGeral(date?: string): Promise<import('../types/bgpStability').BgpStabilityVisaoGeral> {
  return get('/api/v1/bgp-stability/overview', { date })
}

export function fetchBgpStabilityDeep(date?: string): Promise<import('../types/bgpStability').BgpStabilityDeep> {
  return get('/api/v1/bgp-stability-deep', { date })
}

/** `resumo` (1.4.2.4): cada semana vem só com `data.hourly_global` — o que o gráfico de atividade usa — em vez dos ~13 MB de todos os ASes. */
export function fetchBgpStabilityHistory(date?: string, weeks = 6, resumo = false): Promise<import('../types/bgpStability').BgpStabilityHistory> {
  return get('/api/v1/bgp-stability/history', { date, weeks, ...(resumo ? { resumo: true } : {}) })
}

/** Os `top` ASes com mais updates BGP somados nas últimas `weeks` semanas, por família (as mesmas semanas do gráfico de atividade). */
export function fetchBgpStabilityCarga(date?: string, weeks = 6, top = 10): Promise<import('../types/bgpStability').BgpStabilityCarga> {
  return get('/api/v1/bgp-stability/carga', { date, weeks, top })
}

export function postAuthLog(path: string): void {
  const url = new URL(BASE + '/auth/log', window.location.href)
  fetch(url.toString(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ path }),
  }).catch(() => {})
}


// ── Histórico ─────────────────────────────────────────────────────────────────────────────────────────────────
export interface MudancasResposta {
  total: number
  limit: number
  offset: number
  items: Array<HistoricoEvento & { asn?: number; uf?: string; natureza: 'observado' | 'inferido'; confirmado_em?: string }>
}
/** `GET /changes`: eventos entre snapshots (padrão: confirmados). `from` é obrigatório para quem não tem login (o servidor limita a série). */
export function fetchMudancas(opts: { from?: string; to?: string; tipo?: string; uf?: string; ixp?: string; estado?: string; limit?: number; offset?: number }): Promise<MudancasResposta> {
  return get('/api/v1/changes', opts)
}
export interface MudancasResumo {
  total: number
  por_tipo: Record<string, { confirmado: number; pendente: number; revertido: number }>
  por_data: Record<string, number>
  snapshots_com_historico: number
}
export function fetchMudancasResumo(from?: string): Promise<MudancasResumo> {
  return get('/api/v1/changes/summary', { from })
}
export interface DiffSnapshots {
  a: string
  b: string
  totais: Record<string, { a: number; b: number; variacao: number }>
  eventos: { entre: [string, string]; total: number; por_tipo: Record<string, { confirmado: number; pendente: number; revertido: number }> }
  nota: string
}
export function fetchDiffSnapshots(a: string, b: string): Promise<DiffSnapshots> {
  return get('/api/v1/snapshots/diff', { a, b })
}

/** `esquema` 2 (PT-17, D6): `ranking/operadoras` ganhou `base_aa` e `base_pequena` e as listas deixam de esconder quem não tem percentual (vão para o fim); `multas/empresas` tem a ordem padrão alfabética. */
const ESQUEMA_RANKINGS = 2
/** Rankings do SICI e outorgas sem declaração. A prévia (limit ≤ 100, página 1) é aberta na área avançada; ampliar exige login. */
export function fetchRankingOperadoras(opts: { uf?: string; ordem?: string; asc?: boolean; limit?: number; page?: number }): Promise<RankingOperadoras> {
  return get('/api/v1/ranking/operadoras', { ...opts, esquema: ESQUEMA_RANKINGS })
}
export function fetchRankingMunicipios(opts: { date?: string; uf?: string; ordem?: string; asc?: boolean; limit?: number; page?: number }): Promise<RankingMunicipios> {
  return get('/api/v1/ranking/municipios', { ...opts, esquema: ESQUEMA_RANKINGS })
}
export function fetchSemDeclaracaoSici(opts: { tipo?: string; uf?: string; classe?: string; grupo_declara?: boolean; limit?: number; page?: number }): Promise<SemDeclaracaoSici> {
  return get('/api/v1/sem-declaracao-sici', opts)
}
export function fetchTerritorioRanking(opts: { date?: string; campo?: string; uf?: string; asc?: boolean; sem_ptt_proximo?: boolean; min_domicilios?: number; limit?: number; page?: number }): Promise<RankingTerritorio> {
  return get('/api/v1/territorio/ranking', opts)
}
export function fetchMunicipiosSemelhantes(ibge: string, date?: string): Promise<MunicipiosSemelhantes | null> {
  return get(`/api/v1/territorio/municipio/${ibge}/semelhantes`, { date, opcional: true })
}
export function fetchRankingRouteServers(opts: { date?: string; criterio?: string; ixp?: string; apenas_down?: boolean; limit?: number; page?: number }): Promise<RankingRouteServers> {
  return get('/api/v1/ranking/route-servers', opts)
}

/** Tabela única de participantes do PTT, paginada no servidor (a 1ª página, até 100 linhas, é medida; ampliar exige login). */
export function fetchIxpParticipantes(code: string, opts: { date?: string; q?: string; uf?: string; filtro?: string; ordem?: string; desc?: boolean; limit?: number; page?: number }): Promise<ParticipantesPtt> {
  return get(`/api/v1/ixps/${code}/participantes`, opts)
}

/** `esquema` 2: a resposta ganhou a cobertura do rodízio (`cobertura_total_nivel3`, `rs_pulados`; PT-16). */
const ESQUEMA_COMMUNITIES = 2

/** Explorador de communities dos route servers do IX.br: o que cada uma significa e quem a usa, só das rotas recebidas coletadas. */
export function fetchCommunities(opts: { date?: string; q?: string; ixp?: string; classe?: string; limit?: number; page?: number }): Promise<CommunitiesResp> {
  return get('/api/v1/communities', { ...opts, esquema: ESQUEMA_COMMUNITIES })
}

export function fetchCeticTabelas(opts: { date?: string; pesquisa: string }): Promise<CeticTabelas> {
  return get('/api/v1/cetic/tabelas', opts)
}
export function fetchCeticEstimativas(opts: { date?: string; tipo?: string } = {}): Promise<CeticEstimativas> {
  return get('/api/v1/cetic/estimativas', opts)
}
export function fetchCeticIndicadores(opts: { date?: string; pesquisa: string; tabela: string; limit?: number }): Promise<CeticIndicadores> {
  return get('/api/v1/cetic/indicadores', { limit: 1000, ...opts })
}

/**
 * Versão do formato de `/brasil/indicadores` que esta interface espera. A resposta com `?date=` de snapshot publicado sai `immutable`
 * por um ano (api/main.py), no navegador e no cache do nginx: quando a rota ganha campo (ex.: bloco `rpki`), a URL tem de mudar,
 * senão quem já abriu a página continua com a resposta antiga. A API ignora o parâmetro. 3: `rpki.rotas.saude.moas` nulo em todas as datas.
 * 4: `rpki.rotas.rotas_br.{afi}.asn_br_fora_de_bloco` e rota brasileira só por prefixo (D4).
 * 5: `rpki.rotas.saude.moas` por família ({prefixos, prefixos_br, coletores}) nos snapshots com MOAS medido.
 */
const ESQUEMA_BRASIL_INDICADORES = 5

/** Agregados do país para a home e o Panorama técnico: IPv6 do APNIC, DNSSEC, ROV, prontidão e RPKI. Rota aberta. */
export function fetchBrasilIndicadores(date?: string): Promise<BrasilIndicadores> {
  return get('/api/v1/brasil/indicadores', { date, esquema: ESQUEMA_BRASIL_INDICADORES })
}

export function fetchProntidaoResumo(opts: { date?: string; uf?: string } = {}): Promise<ProntidaoResumo> {
  return get('/api/v1/prontidao/resumo', opts)
}

export function fetchSegurancaResumo(opts: { date?: string; uf?: string }): Promise<SegurancaResumo> {
  return get('/api/v1/seguranca/resumo', opts)
}

export function fetchDemandaOferta(date?: string): Promise<DemandaOferta> {
  return get('/api/v1/mercado/demanda-oferta', { date })
}

export function fetchFustResumo(date?: string): Promise<FustResumo> {
  return get('/api/v1/fust/resumo', { date })
}

export function fetchMultasResumo(date?: string): Promise<MultasResumo> {
  return get('/api/v1/multas/resumo', { date })
}

export function fetchMultasEmpresas(opts: { date?: string; grupo?: string; q?: string; ordem?: string; limit?: number; page?: number } = {}): Promise<MultasEmpresas> {
  return get('/api/v1/multas/empresas', { ...opts, esquema: ESQUEMA_RANKINGS })
}

export function fetchQualidadeResumo(date?: string): Promise<QualidadeResumo> {
  return get('/api/v1/qualidade/resumo', { date })
}

export function fetchQualidadePrestadoras(opts: { date?: string; servico: string; indicador: string; uf?: string }): Promise<QualidadePrestadoras> {
  return get('/api/v1/qualidade/prestadoras', opts)
}

export interface QualidadeMapa {
  snapshot_date: string; limites: string; servico: string; unidade: string | null; total: number
  valores: Record<string, number>; prestadoras: Record<string, number>
  faixas: Record<string, 0 | 1 | 2> | null; faixas_rotulos: Record<string, string> | null
  referencias: { superior: string | null; inferior: string | null }; normalizacao: string
}
export function fetchQualidadeMapa(opts: { servico: string; indicador: string; date?: string }): Promise<QualidadeMapa> {
  return get('/api/v1/qualidade/mapa', opts)
}
export function fetchQualidadeSerie(opts: { date?: string; servico: string; indicador: string; prestadora?: string; uf?: string }): Promise<QualidadeSerie> {
  return get('/api/v1/qualidade/serie', opts)
}

export function fetchReclamacoesResumo(date?: string): Promise<ReclamacoesResumo> {
  return get('/api/v1/reclamacoes/resumo', { date })
}

export function fetchReclamacoesMarcas(opts: { date?: string; servico?: string; ano?: number; q?: string; com_cnpj?: boolean; limit?: number; page?: number } = {}): Promise<ReclamacoesMarcas> {
  return get('/api/v1/reclamacoes/marcas', opts)
}

export function fetchConsumidorResumo(date?: string): Promise<ConsumidorResumo> {
  return get('/api/v1/consumidor/resumo', { date })
}

export function fetchConsumidorMarcas(opts: { date?: string; uf?: string; q?: string; com_cnpj?: boolean; limit?: number; page?: number } = {}): Promise<ConsumidorMarcas> {
  return get('/api/v1/consumidor/marcas', opts)
}

export function fetchEspectroResumo(date?: string): Promise<EspectroResumo> {
  return get('/api/v1/espectro/resumo', { date })
}

export function fetchEspectroFaixas(opts: { date?: string; de?: number; ate?: number; servico?: string; carater?: string; limit?: number; page?: number } = {}): Promise<EspectroFaixas> {
  return get('/api/v1/espectro/faixas', opts)
}

/** Sobe quando o corpo de `/satelites/resumo` muda (2: `ngeo_sistemas`, REGULATORIO-E1): troca a URL guardada em cache. */
const ESQUEMA_SATELITES = 2
export function fetchSatelitesResumo(date?: string): Promise<SatelitesResumo> {
  return get('/api/v1/satelites/resumo', { date, esquema: ESQUEMA_SATELITES })
}

export function fetchSatelitesDireitos(opts: { date?: string; operadora?: string; tipo?: string; status?: string; limit?: number; page?: number } = {}): Promise<SatelitesDireitos> {
  return get('/api/v1/satelites/direitos', opts)
}

export function fetchFustMunicipios(opts: { date?: string; uf?: string; programa?: string; ordem?: string; limit?: number } = {}): Promise<FustMunicipios> {
  return get('/api/v1/fust/municipios', opts)
}

export function fetchErbsMunicipios(opts: { uf?: string; geracao?: string; ordem?: string; limit?: number } = {}): Promise<ErbsMunicipios> {
  return get('/api/v1/erbs/municipios', opts)
}

export function fetchIpv4Transferencias(opts: { date?: string; ano?: string; direcao?: string; q?: string; asn?: number; limit?: number; page?: number } = {}): Promise<Ipv4Transferencias> {
  return get('/api/v1/ipv4/transferencias', opts)
}
export function fetchIpv4Mercado(date?: string): Promise<Ipv4Mercado> {
  return get('/api/v1/ipv4/transferencias/resumo', { date })
}
export function fetchIpv4Recuperacao(date?: string): Promise<Ipv4Recuperacao> {
  return get('/api/v1/ipv4/recuperacao', { date })
}
/** Ciclo de vida de um bloco IPv4; 204 = nenhum registro do Brasil para o bloco. */
export function fetchIpv4CicloDeVida(bloco: string, date?: string): Promise<Ipv4CicloDeVida | null> {
  return get(`/api/v1/ipv4/blocos/${bloco}/ciclo-de-vida`, { date, opcional: true })
}

export function fetchIpv4Espaco(opts: { date?: string; classe?: string; asn?: number; cnpj?: string; uf?: string; limit?: number; page?: number } = {}): Promise<Ipv4Espaco> {
  return get('/api/v1/ipv4/espaco', opts)
}
export function fetchIpv4UsoPorTerceiros(opts: { date?: string; sinal?: string; confianca?: string; asn?: number; cnpj?: string; limit?: number; page?: number } = {}): Promise<Ipv4Uso> {
  return get('/api/v1/ipv4/uso-por-terceiros', opts)
}
/** Recursos IPv4 de um ASN; 204 = nenhum bloco, bloco fora da plena divulgação ou sinal para o ASN. */
export function fetchIpv4Asn(asn: number | string, date?: string): Promise<Ipv4RecursosAsn | null> {
  return get(`/api/v1/ipv4/asns/${asn}`, { date, opcional: true })
}

export function fetchIpv4Subasignacoes(opts: { date?: string; asn?: number; conforme?: boolean; limit?: number; page?: number } = {}): Promise<Ipv4Subasignacoes> {
  return get('/api/v1/ipv4/subasignacoes', opts)
}

/** `esquema` 2: o selo de cadastro das instalações traz as datas de registro e de vínculo e ignora a data de lote (PT-16); vale também onde as instalações vêm embutidas (perfil do ASN). `esquema` 3: a lista traz `ptts` por instalação e a cobertura nomeada (PT-24). */
const ESQUEMA_INSTALACOES = 3

/** Instalações do PeeringDB: lista filtrada (a 1ª página, até 100, é aberta; ampliar exige login), uma instalação, as de um PTT e as portas de um PTT externo. */
export function fetchFacilities(opts: { date?: string; pais?: string; uf?: string; q?: string; ptt?: string; cadastro?: string; com_ptt?: boolean; com_carrier?: boolean; ordem?: string; limit?: number; page?: number }): Promise<FacilitiesLista> {
  return get('/api/v1/facilities', { ...opts, esquema: ESQUEMA_INSTALACOES })
}
export function fetchFacility(id: number | string, date?: string, include?: string): Promise<FacilityDetalhe> {
  return get(`/api/v1/facilities/${id}`, { date, include, opcional: true, esquema: ESQUEMA_INSTALACOES })
}
export function fetchIxpFacilities(code: string, date?: string): Promise<FacilitiesPtt> {
  return get(`/api/v1/ixps/${code}/facilities`, { date, opcional: true, esquema: ESQUEMA_INSTALACOES })
}
export function fetchIxpPortas(code: string, date?: string): Promise<PortasIxp> {
  return get(`/api/v1/ixps/${code}/portas`, { date, opcional: true })
}

/** Resumo do cruzamento de mercado por grupo: faixas, municípios que mudam de faixa e HHI por UF. */
export function fetchMercadoGrupos(date?: string): Promise<import('../types/api').ResumoMercadoGrupos> {
  return get('/api/v1/mercado/grupos', { date })
}

/** Maiores do mercado fixo: posição mês a mês das maiores operadoras e treemap por empresa ou grupo. */
export function fetchMercadoMaiores(opts: { date?: string; n?: number; meses?: number } = {}): Promise<import('../types/api').MercadoMaiores> {
  return get('/api/v1/mercado/maiores', opts)
}

/** Resumo da rede no território: IPv6 estimado, usuários atrás de ROV e trânsito único, por UF e país. */
export function fetchRedeTerritorio(date?: string): Promise<import('../types/api').ResumoRedeTerritorio> {
  return get('/api/v1/territorio/rede', { date })
}

/** Interconexão mensurável do AS: originação sem sessão direta, sessões nos route servers e rejeições. */
export function fetchInterconexaoAsn(asn: number | string, date?: string): Promise<import('../types/api').InterconexaoAsn> {
  return get(`/api/v1/asns/${asn}/interconexao`, { date })
}
/** Alcance de cada CDN por peering, por UF. */
export function fetchAlcanceCdns(date?: string): Promise<import('../types/api').AlcanceCdns> {
  return get('/api/v1/cdns/alcance', { date })
}
