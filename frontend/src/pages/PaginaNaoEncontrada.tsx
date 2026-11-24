// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import { SearchBar } from '../components/layout/SearchBar'

/**
 * Rota que a SPA não conhece. Tem `h1` próprio (NBR 17225: título e cabeçalho por página); o título da aba vem de `tituloDaRota` e o
 * status 404, do nginx (`map $rota_spa` em docker/nginx-frontend.conf).
 */
export function PaginaNaoEncontrada() {
  return (
    <div className="mx-auto max-w-xl py-16 text-center">
      <p className="mb-2 text-4xl text-gray-500" aria-hidden="true">404</p>
      <h1 className="mb-3 text-xl font-semibold text-gray-900">Página não encontrada</h1>
      <p className="mb-6 text-sm text-gray-600">O endereço não corresponde a nenhuma página do site.</p>
      <div className="mb-6 text-left"><SearchBar /></div>
      <nav aria-label="Links úteis" className="flex justify-center gap-4 text-sm">
        <Link to="/" className="text-primario-700 underline">Início</Link>
        <Link to="/mapa-do-site" className="text-primario-700 underline">Mapa do site</Link>
      </nav>
    </div>
  )
}
