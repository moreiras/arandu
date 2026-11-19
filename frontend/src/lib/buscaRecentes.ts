// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

/** Últimas buscas da barra: só no navegador (localStorage), sem login e sem ir ao servidor. Guarda título e caminho do que foi aberto. */
export interface Recente { titulo: string; detalhe: string; url: string }

export const CHAVE_RECENTES = 'arandurape.busca.recentes'
const MAX = 6

export function lerRecentes(): Recente[] {
  try {
    const bruto = JSON.parse(localStorage.getItem(CHAVE_RECENTES) ?? '[]')
    return Array.isArray(bruto) ? bruto.filter((r) => r && typeof r.url === 'string' && typeof r.titulo === 'string').slice(0, MAX) : []
  } catch {
    return []
  }
}

/** Põe no topo, sem repetir pelo caminho. Devolve a nova lista. */
export function lembrarBusca(item: Recente): Recente[] {
  const nova = [{ titulo: item.titulo, detalhe: item.detalhe ?? '', url: item.url }, ...lerRecentes().filter((r) => r.url !== item.url)].slice(0, MAX)
  try { localStorage.setItem(CHAVE_RECENTES, JSON.stringify(nova)) } catch { /* armazenamento bloqueado: segue sem lembrar */ }
  return nova
}

export function limparRecentes(): void {
  try { localStorage.removeItem(CHAVE_RECENTES) } catch { /* idem */ }
}
