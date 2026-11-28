// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { LOGIN_REASONS } from '../../auth/accessPolicy'
import { formatarData } from '../../lib/datas'
import { AccessError } from '../../services/api'

/**
 * Estados de um bloco ou página que depende da API. Só `vazio` e `sem-dado` afirmam algo sobre o dado; os demais dizem por que
 * ele não chegou e o que fazer. `login`, `orcamento`, `taxa` e `falha` nunca podem virar "não encontrado", "sem dado" ou zero.
 */
export type EstadoDadosTipo = 'carregando' | 'vazio' | 'sem-dado' | 'login' | 'orcamento' | 'taxa' | 'falha'

/** A API respondeu 404 (ou 204 com `opcional`): a entidade ou o produto não está no snapshot. */
export function ehNaoEncontrado(erro: unknown): boolean {
  return erro instanceof Error && !(erro instanceof AccessError) && /^HTTP 404\b/.test(erro.message)
}

/** Estado de uma consulta que falhou, a partir do erro de `services/api.ts`. */
export function estadoDoErro(erro: unknown): 'sem-dado' | 'login' | 'orcamento' | 'taxa' | 'falha' {
  if (erro instanceof AccessError) return erro.kind === 'login' ? 'login' : erro.kind === 'limit' ? 'orcamento' : 'taxa'
  return ehNaoEncontrado(erro) ? 'sem-dado' : 'falha'
}

/** Erro que impede de dizer qualquer coisa sobre o dado (tudo menos o 404). */
export function ehErroDeAcessoOuFalha(erro: unknown): boolean {
  return !!erro && estadoDoErro(erro) !== 'sem-dado'
}

/** Espera legível: segundos, minutos ou horas, arredondados para cima. */
export function formatarEspera(s: number): string {
  if (s < 90) return `${Math.max(1, Math.ceil(s))} s`
  if (s < 3600) return `${Math.ceil(s / 60)} min`
  return `${Math.ceil(s / 3600)} h`
}

function linkLogin(): string {
  return `/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`
}

const ESTILO: Record<EstadoDadosTipo, string> = {
  carregando: 'text-gray-500',
  vazio: 'text-gray-600',
  'sem-dado': 'text-gray-600',
  login: 'text-primario-900 bg-primario-50 border border-primario-100',
  orcamento: 'text-aviso-700 bg-aviso-50 border border-aviso-200',
  taxa: 'text-aviso-700 bg-aviso-50 border border-aviso-200',
  falha: 'text-perigo-700 bg-perigo-50 border border-perigo-200',
}

/**
 * Mensagem de estado de dados com causa e ação, para página inteira (`variante="pagina"`, título em h1) ou bloco. Passe `erro`
 * (o `error` da consulta) ou `estado` explícito. O 401 também abre o modal de login (`services/api.ts`); aqui fica o aviso no
 * lugar do bloco, para quem fecha o modal não ver um bloco vazio. Anúncio: `role="alert"` só na falha; os outros, `role="status"`.
 */
export function EstadoDados({ estado, erro, oQue = 'estes dados', snapshot, mensagem, aoTentarDeNovo, variante = 'bloco', className = '' }: {
  estado?: EstadoDadosTipo
  erro?: unknown
  /** O que não carregou, para a frase ("o perfil deste AS", "a lista de transferências"). */
  oQue?: string
  /** Data do snapshot (AAAA-MM-DD), citada em `sem-dado`. */
  snapshot?: string | null
  /** Texto próprio para `vazio` e `sem-dado` (e para `carregando`). */
  mensagem?: string
  aoTentarDeNovo?: () => void
  variante?: 'pagina' | 'bloco'
  className?: string
}) {
  const tipo: EstadoDadosTipo = estado ?? (erro ? estadoDoErro(erro) : 'carregando')
  const acesso = erro instanceof AccessError ? erro : null
  const espera = acesso?.retryAfter ?? null
  let titulo: string | null = null
  let texto: string
  let acao: 'entrar' | 'tentar' | null = null
  switch (tipo) {
    case 'carregando':
      texto = mensagem ?? 'Carregando…'
      break
    case 'vazio':
      texto = mensagem ?? 'Nenhum item para mostrar com estes filtros.'
      break
    case 'sem-dado':
      texto = mensagem ?? `Sem dado publicado ${snapshot ? `no snapshot de ${formatarData(snapshot)}` : 'neste snapshot'}.`
      break
    case 'login':
      titulo = 'Entre para ver este dado'
      texto = `${(acesso?.reason && LOGIN_REASONS[acesso.reason]) || 'Este dado exige login (por exemplo, snapshots anteriores aos dois mais recentes ou listas além da prévia).'} O dado não foi carregado; isso não indica que ele não exista.`
      acao = 'entrar'
      break
    case 'orcamento':
      titulo = 'Limite de uso sem login atingido'
      texto = `O tempo de uso das páginas avançadas sem login acabou. Entre gratuitamente para continuar${espera != null ? ` ou volte em ${formatarEspera(espera)}` : ''}. O dado não foi carregado; isso não indica que ele não exista.`
      acao = 'entrar'
      break
    case 'taxa': {
      titulo = 'Muitas consultas em pouco tempo'
      // O título já diz "muitas consultas": do texto da API fica o resto (qual limite, quanto esperar).
      const detalhe = (acesso?.message ?? '').replace(/^Muitas consultas em pouco tempo\.\s*/, '')
      texto = espera != null && !detalhe.includes(String(espera))
        ? `${detalhe.replace(/\s*Tente novamente em instantes\.?$/, '')} Tente de novo em ${formatarEspera(espera)}.`.trim()
        : detalhe || 'Tente de novo em instantes.'
      acao = aoTentarDeNovo ? 'tentar' : null
      break
    }
    case 'falha':
      titulo = 'Falha ao carregar'
      texto = `Não foi possível carregar ${oQue} agora (falha na API ou na rede). Isso não indica que o dado não exista.`
      acao = aoTentarDeNovo ? 'tentar' : null
      break
  }
  const pagina = variante === 'pagina'
  const caixa = tipo === 'carregando' || tipo === 'vazio' || tipo === 'sem-dado' ? '' : `rounded-lg ${pagina ? 'p-6' : 'px-3 py-2'}`
  const Titulo = pagina ? 'h1' : 'p'
  return (
    <div role={tipo === 'falha' ? 'alert' : 'status'} data-estado={tipo}
      className={`text-sm ${ESTILO[tipo]} ${caixa} ${className}`.trim()}>
      {titulo && <Titulo className={pagina ? 'text-lg font-semibold mb-1' : 'font-medium'}>{titulo}</Titulo>}
      <p>{texto}</p>
      {acao === 'entrar' && (
        <a href={linkLogin()} className="mt-2 inline-block rounded px-3 py-1 text-white bg-[#0c1e45] hover:bg-primario-900">Entrar</a>
      )}
      {acao === 'tentar' && (
        <button type="button" onClick={aoTentarDeNovo} className="mt-2 inline-block rounded border border-current px-3 py-1 hover:underline">Tentar de novo</button>
      )}
    </div>
  )
}
