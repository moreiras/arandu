// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/**
 * Chaves de cache por entidade. São EXATAMENTE as que as páginas já usavam (`['asn', asn, date]` etc.), então um hook novo e uma
 * página antiga dividem o mesmo cache e não repetem a chamada. Página nova: use estas funções, não escreva a chave à mão.
 */
export const chaves = {
  asn: (asn: number | string | undefined, date: string | null) => ['asn', asn, date] as const,
  asnPerfil: (asn: number | string | undefined, date: string | null) => ['asn-perfil', asn, date] as const,
  ixpPerfil: (code: string | undefined, date: string | null) => ['ixp-perfil', code, date] as const,
  asnPaths: (asn: number | string | undefined, date: string | null) => ['asn-paths', asn, date] as const,
  ixp: (code: string | undefined, date: string | null) => ['ixp', code, date] as const,
  ixps: (date: string | null) => ['ixps', date] as const,
  operadora: (cnpj: string | undefined, date: string | null) => ['operadora', cnpj, date] as const,
  operadoraMovel: (cnpj: string | undefined, date: string | null) => ['operadora-movel', cnpj, date] as const,
  operadoraPerfil: (cnpj: string | undefined, date: string | null) => ['operadora-perfil', cnpj, date] as const,
  municipioPerfil: (ibge: string | undefined, date: string | null) => ['municipio-perfil', ibge, date] as const,
  municipio: (ibge: string | undefined, date: string | null) => ['municipio-acessos', ibge, date] as const,
  municipioMovel: (ibge: string | undefined, date: string | null) => ['municipio-acessos-movel', ibge, date] as const,
  uf: (uf: string | undefined, date: string | null) => ['uf-perfil', uf, date] as const,
  ufs: (date: string | null) => ['ufs-resumo', date] as const,
  gruposSocietarios: (date: string | null) => ['grupos-societarios', date] as const,
  /** Mesma chave do Dashboard, IXPs, Estatísticas e Comparar: o detalhe do snapshot (com `manifest.sources`) é buscado uma vez e compartilhado. */
  snapshot: (date: string | null) => ['snapshot-details', date] as const,
}

/** Snapshots são imutáveis: o documento de uma data nunca muda. */
export const IMUTAVEL = { staleTime: Infinity, gcTime: Infinity } as const
