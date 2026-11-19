// Política de acesso no frontend — ESPELHO de api/auth/access_policy.py.
// O servidor é a fonte de verdade (a API/gate decide); aqui só dizemos qual é a
// área de cada rota para (a) o relógio do orçamento só andar em páginas
// avançadas e (b) mostrar o painel de login no lugar certo.
// A classificação das rotas de API é travada por
// tests/test_access_policy.py; esta tabela (rotas do SPA) é revisada junto com ela.

/** open = entrada, sempre aberta · metered = avançada, medida · login = exige login. */
export type RouteAccess = 'open' | 'metered' | 'login'

const OPEN_EXACT = new Set([
  '/', '/visao-geral', '/login', '/sobre', '/privacidade', '/uso-aceitavel', '/acessibilidade', '/mapa-do-site', '/dados', '/fontes', '/estados',
  '/ixps', '/ases', '/operadoras', '/scms', '/smps', '/stfcs', '/seacs', '/grupos',
])

const LOGIN_EXACT = new Set(['/snapshots', '/perfil'])

/** Classe de acesso da rota do SPA (pathname sem query). */
export function routeAccess(pathname: string): RouteAccess {
  const p = pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname
  if (OPEN_EXACT.has(p)) return 'open'
  if (LOGIN_EXACT.has(p)) return 'login'
  return 'metered'
}

/** Motivos de login (mensagens do modal/painel). */
export const LOGIN_REASONS: Record<string, string> = {
  'lista-expandida': 'Para ver a lista completa e navegar entre as páginas, entre com sua conta.',
  historico: 'Para consultar snapshots anteriores e a evolução no tempo, entre com sua conta.',
  contatos: 'Os contatos só são exibidos para usuários logados.',
  exportar: 'Para exportar os dados em CSV, entre com sua conta.',
  esgotado: 'O tempo de uso das páginas avançadas sem login acabou. Entre para continuar.',
  geral: 'Entre com sua conta para continuar.',
}

/** Snapshots "atuais" (os 2 mais recentes) — o resto é histórico (login). */
export function isHistoricalDate(date: string | null | undefined, snapshots: string[] | undefined): boolean {
  if (!date || !snapshots || snapshots.length === 0) return false
  const recent = [...snapshots].sort().slice(-2)
  return !recent.includes(date)
}

/** Prévia de lista para anônimo (espelha PREVIEW_LIMIT da API). */
export const PREVIEW_LIMIT = 100
