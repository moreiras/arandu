// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { HistoricoEvento } from '../../types/api'
import { formatarData } from '../../lib/datas'

/**
 * Rótulos do histórico. Linguagem de evidência: o evento é uma DIFERENÇA OBSERVADA entre snapshots, sem causa, intenção nem
 * nome de empresa. Eventos de provedor (inferência do ARC v1) não aparecem na interface.
 */
export const ROTULO_METRICA: Record<string, string> = {
  users: 'Usuários estimados (APNIC)', users_ma4: 'Usuários, média de 28 dias', v6users: 'Usuários IPv6 estimados',
  p6: 'Prefixos IPv6 na tabela', p4: 'Prefixos IPv4 na tabela', n_ixd: 'PTTs com par direto', n_ixm: 'PTTs como membro',
  n_roa: 'ROAs', n_aspa: 'Objetos ASPA', rpki_valid: 'Prefixos RPKI válidos', rpki_invalid: 'Prefixos RPKI inválidos',
  rpki_not_found: 'Prefixos sem ROA', n_alertas: 'Pontos de atenção', n_asns: 'ASNs', n_cnpjs: 'CNPJs',
  n_direct: 'ASNs em par direto', n_br_direct: 'ASNs BR em par direto', n_origin: 'ASNs originadores', n_br_origin: 'ASNs BR originadores',
  n_membros: 'Membros cadastrados', v6_rotas: 'Rotas IPv6', v6_prefixos: 'Prefixos IPv6', v4_rotas: 'Rotas IPv4', v4_prefixos: 'Prefixos IPv4',
}

/** Métricas desenhadas por escopo, na ordem. As demais colunas seguem na API. */
export const METRICAS_ESCOPO: Record<'asn' | 'ixp' | 'operadora' | 'uf', string[]> = {
  asn: ['users', 'p6', 'p4', 'n_ixd', 'n_roa', 'rpki_invalid'],
  ixp: ['n_direct', 'n_br_direct', 'n_membros', 'v4_prefixos'],
  operadora: ['users_ma4', 'p4', 'n_asns', 'n_roa'],
  uf: ['users_ma4', 'n_asns', 'p4', 'n_roa'],
}

const FRASE: Record<string, (e: HistoricoEvento) => string> = {
  asn_novo: () => 'Passou a aparecer na tabela de roteamento',
  asn_sumido: () => 'Deixou de aparecer na tabela de roteamento',
  ixp_entrada: (e) => `Passou a constar como membro do PTT ${e.chave}`,
  ixp_saida: (e) => `Deixou de constar como membro do PTT ${e.chave}`,
  ixp_entrada_observada: (e) => `Passou a ser visto em par direto no PTT ${e.chave}`,
  ixp_saida_observada: (e) => `Deixou de ser visto em par direto no PTT ${e.chave}`,
  mudanca_origem: (e) => `Prefixo ${e.entidade.replace('prefixo:', '')}: origem mudou de AS${e.de} para AS${e.para}`,
  roa_ganho: () => 'Passou a ter ROA',
  roa_perdido: () => 'Deixou de ter ROA',
  aspa_ganho: () => 'Passou a publicar ASPA',
  aspa_perdido: () => 'Deixou de publicar ASPA',
  rpki_invalido_novo: () => 'Passou a ter prefixo com RPKI inválido',
  rpki_invalido_resolvido: () => 'Deixou de ter prefixo com RPKI inválido',
  outorga_nova: (e) => `Nova outorga ${e.chave.toUpperCase()} no cadastro da Anatel`,
  outorga_baixa: (e) => `Outorga ${e.chave.toUpperCase()} deixou de constar no cadastro da Anatel`,
  alerta_novo: (e) => `Novo ponto de atenção: ${e.chave.replace(/_/g, ' ')}`,
  alerta_resolvido: (e) => `Ponto de atenção deixou de aparecer: ${e.chave.replace(/_/g, ' ')}`,
}

export const TIPOS_DA_PAGINA = Object.keys(FRASE)

export function fraseEvento(e: HistoricoEvento): string {
  return (FRASE[e.tipo] ?? (() => e.tipo.replace(/_/g, ' ')))(e)
}

export const ROTULO_ESTADO: Record<HistoricoEvento['estado'], string> = {
  confirmado: 'confirmado', pendente: 'em confirmação', revertido: 'revertido',
}

/** Data do primeiro snapshot publicado (DD/MM/AAAA), lida da lista de `/snapshots`; vazio enquanto a lista não chega. */
export function inicioDosSnapshots(datas: readonly string[] | undefined): string {
  const primeira = [...(datas ?? [])].sort()[0]
  return primeira ? formatarData(primeira) : ''
}

