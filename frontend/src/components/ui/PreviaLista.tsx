// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

/** Texto da prévia anônima de uma lista (D9): quantas linhas aparecem e quantas existem. */
export function textoPrevia(mostradas: number, total: number): string {
  return `Prévia: ${mostradas.toLocaleString('pt-BR')} de ${total.toLocaleString('pt-BR')}.`
}

/**
 * Aviso de prévia de lista para quem não tem login: a primeira página (até `PREVIEW_LIMIT` linhas, pela ordem escolhida) já está na tela;
 * as demais exigem login. Substitui o erro e a lista vazia: o botão abre o modal de login (`requireLogin('lista-expandida')`).
 * Não aparece quando a lista inteira já está na tela.
 */
export function PreviaLista({ mostradas, total, aoEntrar, className = 'mt-3 text-xs text-gray-500' }: {
  mostradas: number; total: number; aoEntrar: () => void; className?: string
}) {
  if (total <= mostradas) return null
  return (
    <p className={className} data-testid="previa-lista" role="status">
      {textoPrevia(mostradas, total)}{' '}
      <button type="button" className="text-primario-600 hover:underline" onClick={aoEntrar}>Entre para ver as demais.</button>
    </p>
  )
}
