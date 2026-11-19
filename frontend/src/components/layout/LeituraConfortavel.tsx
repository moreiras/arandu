// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useEffect, useState } from 'react'

const CHAVE = 'arandurape.leitura.confortavel'
const CLASSE = 'leitura-confortavel'

function lerPreferencia(): boolean {
  try { return localStorage.getItem(CHAVE) === '1' } catch { return false }
}

/** Aplica a preferência salva assim que o app carrega (antes do primeiro desenho do cabeçalho). */
export function aplicarLeituraSalva(): void {
  if (typeof document !== 'undefined' && lerPreferencia()) document.documentElement.classList.add(CLASSE)
}

/**
 * "Leitura confortável" (NBR 17225 5.12.1–5.12.4 e 5.12.6): o mecanismo que a norma aceita para
 * entrelinha de 1,5, espaço entre parágrafos de 2 vezes a fonte, entre letras de 0,12 e entre palavras de 0,16, e linhas de até 80
 * caracteres. Liga a classe `leitura-confortavel` no `<html>` (regras em `index.css`) e lembra a escolha neste navegador.
 */
export function LeituraConfortavel() {
  const [ligada, setLigada] = useState(lerPreferencia)
  useEffect(() => {
    document.documentElement.classList.toggle(CLASSE, ligada)
    try { localStorage.setItem(CHAVE, ligada ? '1' : '0') } catch { /* sem armazenamento: vale só nesta página */ }
  }, [ligada])
  return (
    <button
      type="button"
      aria-pressed={ligada}
      onClick={() => setLigada((v) => !v)}
      title="Mais espaço entre linhas, letras, palavras e parágrafos"
      className={`whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs transition-colors ${ligada ? 'border-primario-300 bg-primario-50 text-primario-800' : 'border-gray-200 bg-white text-gray-600 hover:text-gray-900'}`}
    >
      Leitura confortável
    </button>
  )
}
